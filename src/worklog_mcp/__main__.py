"""メインエントリーポイント"""

import sys
import logging
import argparse
import os
import asyncio
from .server import run_server, create_server


# ログ設定
from .logging_config import setup_logging

# ログ設定を実行
log_file_path = setup_logging()

logger = logging.getLogger(__name__)


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description="分報MCPサーバー")
    parser.add_argument(
        "--project",
        type=str,
        help="プロジェクトディレクトリのパス（指定されない場合は現在のディレクトリを使用）",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8080,
        help="Webサーバーポート（デフォルト: 8080）",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Webサーバーを無効化（MCPサーバーのみ起動）",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser.parse_args()


async def run_integrated_server(project_path: str, web_port: int = 8080):
    """MCPとWebサーバーの統合起動"""
    import uvicorn
    from .database import Database
    from .project_context import ProjectContext
    from .web_ui import WebUIServer

    # データベースとコンテキストの初期化
    project_context = ProjectContext(project_path)
    db_path = project_context.get_database_path()
    db = Database(db_path)
    await db.initialize()

    # Web UIサーバー作成
    web_server = WebUIServer(db, project_context)

    # MCPサーバー作成（Web連携機能付き）
    mcp_server = await create_server(project_path, web_server)

    # uvicornサーバー設定
    config = uvicorn.Config(
        app=web_server.app, host="0.0.0.0", port=web_port, log_level="info"
    )
    server = uvicorn.Server(config)

    logger.info(f"統合サーバーを開始します (Web: http://localhost:{web_port})")

    # MCPサーバーの実行タスクを作成（run_stdio_asyncを直接呼び出す）
    mcp_task = asyncio.create_task(mcp_server.run_stdio_async())

    # Webサーバーの実行タスクを作成
    web_task = asyncio.create_task(server.serve())

    try:
        # 両方のタスクを並行実行
        await asyncio.gather(mcp_task, web_task)
    except KeyboardInterrupt:
        logger.info("サーバーを停止しています...")
        mcp_task.cancel()
        web_task.cancel()
        try:
            await asyncio.gather(mcp_task, web_task, return_exceptions=True)
        except Exception as e:
            logger.debug(
                f"タスク停止処理でエラー（予期される動作）: {type(e).__name__}: {e}"
            )


def main():
    """uvxから呼び出されるメインエントリーポイント"""
    try:
        args = parse_args()

        # --project引数が指定されていない場合は現在のディレクトリを使用
        project_path = args.project if args.project else os.getcwd()

        if args.project:
            logger.info(f"プロジェクトモードで開始: {args.project}")
        else:
            logger.info(
                f"プロジェクトモードで開始（現在のディレクトリ）: {project_path}"
            )

        if args.no_web:
            # 既存のMCPサーバーのみ起動
            logger.info("MCPサーバーのみ起動（Web機能無効）")
            run_server(project_path=project_path)
        else:
            # 統合サーバー起動
            logger.info(f"統合サーバー起動（Web: http://localhost:{args.web_port}）")
            asyncio.run(run_integrated_server(project_path, args.web_port))

    except KeyboardInterrupt:
        logger.info("サーバーが停止されました (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"サーバーエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
