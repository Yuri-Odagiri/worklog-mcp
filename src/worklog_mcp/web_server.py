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

    # Webサーバー作成
    web_server = WebUIServer(db, project_context)

    # イベントバスの初期化
    event_bus_path = project_context.get_eventbus_database_path()
    event_bus = EventBus(event_bus_path)
    await event_bus.initialize()

    # イベントポーラーの設定と開始
    poller = EventBusPoller(event_bus, poll_interval=0.5)

    # イベント受信時のコールバック
    async def handle_event(event_type: str, data: dict):
        """イベントバスからのイベントを処理"""
        try:
            # user_registeredイベントの場合、アバター生成を実行
            if event_type == "user_registered":
                await handle_user_registered(data, db, project_context, web_server)

            # 通常のWebSocket通知も継続
            await web_server.notify_clients(event_type, data)
        except Exception as e:
            logger.error(f"イベント処理エラー: {e}")

    async def handle_user_registered(
        user_data: dict,
        db: Database,
        project_context: ProjectContext,
        web_server: WebUIServer,
    ):
        """user_registeredイベントを処理してアバター生成を実行"""
        try:
            user_id = user_data["user_id"]
            name = user_data["name"]
            role = user_data["role"]
            personality = user_data["personality"]
            appearance = user_data["appearance"]
            theme_color = user_data["theme_color"]

            logger.info(
                f"ユーザー '{user_id}' のアバター生成を開始します（ビューアーサーバー側）"
            )

            # 非同期でAIアバター生成を開始（バックグラウンド処理）
            import asyncio

            asyncio.create_task(
                generate_ai_avatar_for_user(
                    name,
                    role,
                    personality,
                    appearance,
                    theme_color,
                    user_id,
                    project_context,
                    db,
                    web_server,
                )
            )

        except Exception as e:
            logger.error(f"アバター生成処理エラー: {e}")

    async def generate_ai_avatar_for_user(
        name: str,
        role: str,
        personality: str,
        appearance: str,
        theme_color: str,
        user_id: str,
        project_context: ProjectContext,
        db: Database,
        web_server: WebUIServer,
    ):
        """ユーザーのAIアバターを生成してデータベースとUIを更新"""
        try:
            from worklog_mcp.avatar_generator import generate_openai_avatar

            # OpenAI APIでアバター生成を試行
            avatar_path = await generate_openai_avatar(
                name, role, personality, appearance, user_id, project_context
            )

            if avatar_path:
                # AI生成が成功した場合のみデータベース更新と通知を実行
                await db.update_user_avatar_path(user_id, avatar_path)

                # WebSocket経由でクライアントに通知
                await web_server.notify_clients(
                    "avatar_updated",
                    {"user_id": user_id, "avatar_path": avatar_path},
                )

                logger.info(
                    f"ユーザー '{user_id}' のAI生成アバターが完了し、更新されました: {avatar_path}"
                )
            else:
                logger.info(
                    f"ユーザー '{user_id}' のAI生成に失敗しました。動的アバターが継続使用されます。"
                )

        except Exception as e:
            logger.error(f"AI アバター生成エラー (user_id: {user_id}): {e}")
            logger.debug("AI アバター生成エラー詳細", exc_info=True)

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
