#!/usr/bin/env python3
"""
独立ジョブワーカープロセス
重い処理（AI画像生成など）を専用で処理するデーモン
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worklog_mcp.database import Database
from worklog_mcp.event_bus import EventBus
from worklog_mcp.job_queue import JobQueue, JobWorker
from worklog_mcp.logging_config import setup_logging
from worklog_mcp.project_context import ProjectContext

# ロガー設定
log_file_path = setup_logging()
logger = logging.getLogger(__name__)


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="分報ジョブワーカーデーモン（重い処理専用）"
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="プロジェクトディレクトリのパス",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="ジョブポーリング間隔（秒、デフォルト: 1.0）",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser.parse_args()


class JobWorkerDaemon:
    """ジョブワーカーデーモンクラス"""

    def __init__(self, project_path: str, poll_interval: float = 1.0):
        self.project_path = project_path
        self.poll_interval = poll_interval
        self._running = False
        self._task = None

        # インスタンス変数の初期化
        self.project_context = None
        self.db = None
        self.event_bus = None
        self.job_queue = None
        self.job_worker = None

    async def initialize(self):
        """各種コンポーネントの初期化"""
        # プロジェクトコンテキストの初期化
        self.project_context = ProjectContext(self.project_path)
        self.project_context.initialize_project_directories()

        # データベースの初期化
        db_path = self.project_context.get_database_path()
        self.db = Database(db_path)
        await self.db.initialize()

        # イベントバスの初期化
        event_bus_path = self.project_context.get_eventbus_database_path()
        self.event_bus = EventBus(event_bus_path)
        await self.event_bus.initialize()

        # ジョブキューの初期化
        job_queue_path = self.project_context._get_project_dir() / "jobs.db"
        self.job_queue = JobQueue(job_queue_path)
        await self.job_queue.initialize()

        # ジョブワーカーの設定
        self.job_worker = JobWorker(self.job_queue, poll_interval=self.poll_interval)

        # アバター生成ジョブハンドラーを登録
        self.job_worker.register_handler(
            "avatar_generation", self._handle_avatar_generation
        )

        logger.info(
            f"ジョブワーカーデーモン初期化完了: {self.project_context.get_project_name()}"
        )

    async def _handle_avatar_generation(self, payload: dict) -> dict:
        """アバター生成ジョブハンドラー"""
        try:
            user_id = payload["user_id"]
            name = payload["name"]
            role = payload["role"]
            personality = payload["personality"]
            appearance = payload["appearance"]

            logger.info(f"アバター生成ジョブ開始: {user_id}")

            from worklog_mcp.avatar_generator import generate_openai_avatar

            # OpenAI APIでアバター生成
            avatar_path = await generate_openai_avatar(
                name, role, personality, appearance, user_id, self.project_context
            )

            if avatar_path:
                # データベース更新
                await self.db.update_user_avatar_path(user_id, avatar_path)

                # EventBusでアバター更新を通知
                await self.event_bus.publish(
                    "avatar_updated",
                    {"user_id": user_id, "avatar_path": avatar_path},
                )

                logger.info(f"アバター生成ジョブ完了: {user_id} -> {avatar_path}")
                return {"success": True, "avatar_path": avatar_path}
            else:
                logger.warning(f"アバター生成失敗: {user_id}")
                return {"success": False, "error": "AI生成に失敗しました"}

        except Exception as e:
            logger.error(f"アバター生成ジョブエラー: {e}")
            raise

    async def start(self):
        """ジョブワーカーデーモン開始"""
        if self._running:
            return

        self._running = True
        logger.info("ジョブワーカーデーモン開始")

        # ジョブワーカー開始
        await self.job_worker.start()

        # メインループ
        self._task = asyncio.create_task(self._main_loop())

    async def stop(self):
        """ジョブワーカーデーモン停止"""
        self._running = False

        if self.job_worker:
            await self.job_worker.stop()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("ジョブワーカーデーモン停止")

    async def cleanup(self):
        """リソースのクリーンアップ"""
        if self.job_queue:
            await self.job_queue.close()
        if self.event_bus:
            await self.event_bus.close()
        if self.db:
            await self.db.close()

    async def _main_loop(self):
        """メインループ"""
        try:
            while self._running:
                # ジョブワーカーが動作中かチェック
                if not self.job_worker._running:
                    logger.warning("ジョブワーカーが停止しています。再起動中...")
                    await self.job_worker.start()

                # 短い間隔で生存確認
                await asyncio.sleep(5.0)

        except asyncio.CancelledError:
            logger.info("メインループがキャンセルされました")
            raise
        except Exception as e:
            logger.error(f"メインループエラー: {e}")
            raise


async def run_daemon(project_path: str, poll_interval: float) -> None:
    """ジョブワーカーデーモンの実行"""
    daemon = JobWorkerDaemon(project_path, poll_interval)

    # シグナルハンドラー設定
    def signal_handler(signum, frame):
        logger.info(f"シグナル受信: {signum}")
        asyncio.create_task(daemon.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await daemon.initialize()
        await daemon.start()

        # デーモンが停止するまで待機
        while daemon._running:
            await asyncio.sleep(1.0)

    except KeyboardInterrupt:
        logger.info("キーボード割り込みを受信")
    except Exception as e:
        logger.error(f"ジョブワーカーデーモンエラー: {e}")
        raise
    finally:
        await daemon.stop()
        await daemon.cleanup()


def main():
    """メインエントリーポイント"""
    try:
        args = parse_args()

        logger.info(
            f"ジョブワーカーデーモンを起動します (プロジェクト: {args.project})"
        )
        logger.info(f"ポーリング間隔: {args.poll_interval}秒")

        # デーモン実行
        asyncio.run(run_daemon(args.project, args.poll_interval))

    except KeyboardInterrupt:
        logger.info("ジョブワーカーデーモンが停止されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"ジョブワーカーデーモンエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
