"""
Main registration function that coordinates all MCP tools.
"""

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from ..database import Database
from ..project_context import ProjectContext
from ..logging_config import logger

from .user_management import register_user_management_tools
from .worklog_posting import register_worklog_posting_tools
from .worklog_reading import register_worklog_reading_tools
from .worklog_search import register_worklog_search_tools
from .worklog_management import register_worklog_management_tools
from .worklog_analytics import register_worklog_analytics_tools

if TYPE_CHECKING:
    from ..event_bus import EventBus


def register_tools(
    mcp: FastMCP,
    db: Database,
    project_context: ProjectContext,
    event_bus: "EventBus",
) -> None:
    """全ツールをMCPサーバーに登録"""

    async def notify_web(event_type: str, data: dict) -> None:
        """イベントバス経由でWebへ通知"""
        try:
            await event_bus.publish(event_type, data)
        except Exception as e:
            logger.debug(
                f"イベント通知エラー（Webサーバーが起動していない可能性）: {e}"
            )

    async def get_project_info(ctx) -> dict:
        """現在のプロジェクト情報を取得"""
        try:
            await ctx.info("プロジェクト情報を取得中...")

            project_info = project_context.get_project_info()

            await ctx.info(
                f"プロジェクト '{project_info['project_name']}' の情報を取得しました"
            )
            return project_info

        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    # Register all tool modules
    register_user_management_tools(mcp, db, notify_web)
    register_worklog_posting_tools(mcp, db, notify_web)
    register_worklog_reading_tools(mcp, db)
    register_worklog_search_tools(mcp, db)
    register_worklog_management_tools(mcp, db, notify_web)
    register_worklog_analytics_tools(mcp, db)
