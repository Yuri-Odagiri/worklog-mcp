"""MCPサーバーの実装"""

import logging
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from .database import Database
from .project_context import ProjectContext

if TYPE_CHECKING:
    from .event_bus import EventBus
from .logging_config import setup_logging

# ログ設定を確実に初期化
setup_logging()

logger = logging.getLogger(__name__)


async def create_server(
    db: Database, project_context: ProjectContext, event_bus: "EventBus"
) -> FastMCP:
    """MCPサーバーのインスタンスを作成"""
    # MCPサーバーのインスタンス作成
    server_name = f"worklog-mcp-{project_context.get_project_name()}"
    mcp = FastMCP(server_name)

    # ツールの登録（イベントバスを渡す）
    from .tools import register_tools

    register_tools(mcp, db, project_context, event_bus)

    logger.info(
        f"MCPサーバーの初期化が完了しました (プロジェクト: {project_context.get_project_name()})"
    )
    return mcp
