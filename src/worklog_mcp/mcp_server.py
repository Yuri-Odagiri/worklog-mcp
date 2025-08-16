#!/usr/bin/env python3
"""
MCPサーバー専用エントリーポイント
分報MCPサーバーをスタンドアロンで起動
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path


# モジュールパスの設定（uvx環境対応）
def setup_module_path():
    """モジュールパスを適切に設定"""
    current_dir = Path(__file__).parent

    # uvx環境の場合、既にモジュールパスは設定済み
    if "archive-v0" in str(current_dir):
        return

    # 開発環境の場合、プロジェクトルートを追加
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


setup_module_path()

from worklog_mcp.database import Database
from worklog_mcp.event_bus import EventBus
from worklog_mcp.logging_config import setup_logging
from worklog_mcp.project_context import ProjectContext
from worklog_mcp.server import create_server

# ロガー設定
log_file_path = setup_logging()
logger = logging.getLogger(__name__)


def parse_args():
    """コマンドラインク引数をパース"""
    parser = argparse.ArgumentParser(description="分報MCPサーバー（スタンドアロン版）")
    parser.add_argument(
        "--project",
        type=str,
        help="プロジェクトディレクトリのパス（指定されない場合は現在のディレクトリを使用）",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser.parse_args()


async def run_mcp_server(project_path: str, transport: str = "http") -> None:
    """MCPサーバーの起動と実行"""
    try:
        # プロジェクトコンテキストの初期化
        project_context = ProjectContext(project_path)
        project_context.initialize_project_directories()

        # データベースパスの設定
        db_path = project_context.get_database_path()

        # データベースの初期化
        db = Database(db_path)
        await db.initialize()

        # 初回起動チェック
        if await db.is_first_run():
            project_info = project_context.get_project_info()
            logger.info(
                f"プロジェクト '{project_info['project_name']}' の初回起動を検出しました。ユーザー登録が必要です。"
            )

        # イベントバスの初期化
        event_bus_path = project_context.get_eventbus_database_path()
        event_bus = EventBus(event_bus_path)
        await event_bus.initialize()

        # MCPサーバーの作成と実行
        mcp = await create_server(db, project_context, event_bus)

        logger.info(
            f"MCPサーバー起動 (プロジェクト: {project_context.get_project_name()}, transport: {transport})"
        )

        # トランスポートに応じてサーバー実行
        if transport == "stdio":
            await mcp.run_stdio_async()
        elif transport == "http":
            from .sse_server import run_http_server

            await run_http_server(mcp, host="127.0.0.1", port=8000)
        else:
            raise ValueError(f"Unknown transport: {transport}")

    except KeyboardInterrupt:
        logger.info("MCPサーバーが停止されました (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"MCPサーバーエラー: {e}")
        raise
    finally:
        # クリーンアップ
        if "event_bus" in locals():
            await event_bus.close()
        if "db" in locals():
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

        # MCPサーバー実行
        asyncio.run(run_mcp_server(project_path))

    except KeyboardInterrupt:
        logger.info("MCPサーバーが停止されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCPサーバーエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
