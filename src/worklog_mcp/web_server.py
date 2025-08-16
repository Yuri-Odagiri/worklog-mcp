#!/usr/bin/env python3
"""
Webビューアー専用エントリーポイント
分報Webビューアーをスタンドアロンで起動
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import uvicorn

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worklog_mcp.database import Database
from worklog_mcp.event_bus import EventBus, EventBusPoller
from worklog_mcp.job_queue import JobQueue
from worklog_mcp.logging_config import setup_logging
from worklog_mcp.project_context import ProjectContext
from worklog_mcp.web_ui import WebUIServer

# ロガー設定
log_file_path = setup_logging()
logger = logging.getLogger(__name__)


def parse_args():
    """コマンドラインク引数をパース"""
    parser = argparse.ArgumentParser(
        description="分報Webビューアー（スタンドアロン版）"
    )
    parser.add_argument(
        "--project",
        type=str,
        help="プロジェクトディレクトリのパス（指定されない場合は現在のディレクトリを使用）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Webサーバーポート（デフォルト: 8080）",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="バインドするホスト（デフォルト: 0.0.0.0）",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser.parse_args()


async def run_web_server(project_path: str, host: str, port: int) -> None:
    """Webサーバーの起動と実行"""

    # プロジェクトコンテキストの初期化
    project_context = ProjectContext(project_path)
    project_context.initialize_project_directories()

    # データベースパスの設定
    db_path = project_context.get_database_path()

    # データベースの初期化
    db = Database(db_path)
    await db.initialize()

    # イベントバスの初期化
    event_bus_path = project_context.get_eventbus_database_path()
    event_bus = EventBus(event_bus_path)
    await event_bus.initialize()

    # ジョブキューの初期化（ジョブ追加のみ）
    job_queue_path = project_context._get_project_dir() / "jobs.db"
    job_queue = JobQueue(job_queue_path)
    await job_queue.initialize()

    # Webサーバー作成（ジョブキューとイベントバスを渡す）
    web_server = WebUIServer(db, project_context, job_queue, event_bus)

    # イベントポーラーの設定と開始
    poller = EventBusPoller(event_bus, poll_interval=0.5)

    # イベント受信時のコールバック
    async def handle_event(event_type: str, data: dict):
        """イベントバスからのイベントを処理"""
        try:
            # user_registeredイベントの場合、アバター生成ジョブをキューに追加
            if event_type == "user_registered":
                await job_queue.enqueue(
                    "avatar_generation",
                    {
                        "user_id": data["user_id"],
                        "name": data["name"],
                        "role": data["role"],
                        "personality": data["personality"],
                        "appearance": data["appearance"],
                        "theme_color": data["theme_color"],
                    },
                )
                logger.info(f"アバター生成ジョブをキューに追加: {data['user_id']}")

            # 通常のWebSocket通知（即座に実行）
            await web_server.notify_clients(event_type, data)
        except Exception as e:
            logger.error(f"イベント処理エラー: {e}")

    # ポーリング開始
    await poller.start(handle_event)

    # uvicornサーバー設定
    config = uvicorn.Config(app=web_server.app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    logger.info(
        f"Webビューアー起動 (http://{host}:{port}, プロジェクト: {project_context.get_project_name()})"
    )

    try:
        # Webサーバー実行
        await server.serve()
    finally:
        # クリーンアップ
        await poller.stop()
        await job_queue.close()
        await event_bus.close()
        await db.close()


def main():
    """メインエントリーポイント"""
    try:
        args = parse_args()

        # プロジェクトパスの設定
        project_path = args.project if args.project else os.getcwd()

        if args.project:
            logger.info(f"プロジェクトモードで開始: {args.project}")
        else:
            logger.info(
                f"プロジェクトモードで開始（現在のディレクトリ）: {project_path}"
            )

        logger.info(f"Webビューアーを起動します (http://{args.host}:{args.port})")

        # Webサーバー実行
        asyncio.run(run_web_server(project_path, args.host, args.port))

    except KeyboardInterrupt:
        logger.info("Webビューアーが停止されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Webビューアーエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
