"""MCPサーバーの実装"""

import logging
from typing import Optional, TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from .database import Database
from .project_context import ProjectContext
from .tools import register_tools

if TYPE_CHECKING:
    from .event_bus import EventBus
from .logging_config import setup_logging

# ログ設定を確実に初期化
setup_logging()

logger = logging.getLogger(__name__)


async def create_server(project_path: Optional[str] = None, web_server=None) -> FastMCP:
    """MCPサーバーのインスタンスを作成（統合起動用・下位互換性維持）"""
    # プロジェクトコンテキストの初期化
    project_context = ProjectContext(project_path)

    # プロジェクトディレクトリの初期化（初回起動時）
    project_context.initialize_project_directories()

    # データベースパスの設定（プロジェクト分離）
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

    # MCPサーバーのインスタンス作成
    server_name = f"worklog-mcp-{project_context.get_project_name()}"
    mcp = FastMCP(server_name)

    # ツールの登録（Webサーバーを渡す）
    register_tools(mcp, db, project_context, web_server)

    logger.info(
        f"MCPサーバーの初期化が完了しました (プロジェクト: {project_context.get_project_name()})"
    )
    return mcp


async def create_server_standalone(
    db: Database, project_context: ProjectContext, event_bus: "EventBus"
) -> FastMCP:
    """スタンドアロンMCPサーバーのインスタンスを作成"""
    # MCPサーバーのインスタンス作成
    server_name = f"worklog-mcp-{project_context.get_project_name()}"
    mcp = FastMCP(server_name)

    # ツールの登録（イベントバスを渡す）
    from .tools import register_tools_standalone

    register_tools_standalone(mcp, db, project_context, event_bus)

    logger.info(
        f"スタンドアロンMCPサーバーの初期化が完了しました (プロジェクト: {project_context.get_project_name()})"
    )
    return mcp


def run_server(project_path: Optional[str] = None) -> None:
    """MCPサーバーの起動と実行（下位互換性維持）"""
    try:
        import asyncio

        async def _run():
            # サーバー作成
            mcp = await create_server(project_path)

            # サーバー実行
            await mcp.run_stdio_async()

        # asyncio実行
        asyncio.run(_run())

    except Exception as e:
        logger.error(f"サーバー実行エラー: {e}")
        raise
