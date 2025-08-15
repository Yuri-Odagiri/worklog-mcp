"""MCPツールの実装"""

import logging
import functools
import json
from typing import Callable, TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from .database import Database
from .project_context import ProjectContext

if TYPE_CHECKING:
    from .event_bus import EventBus

logger = logging.getLogger(__name__)


def log_mcp_tool(func: Callable) -> Callable:
    """MCPツールのリクエストとレスポンスをロギングするデコレータ"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import time

        tool_name = func.__name__
        start_time = time.perf_counter()

        # リクエストのログ出力（機密情報を除外）
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if key in ["password", "token", "secret"]:
                sanitized_kwargs[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized_kwargs[key] = f"{value[:200]}... (truncated)"
            else:
                sanitized_kwargs[key] = value

        logger.info(
            f"MCP Tool Request - {tool_name}: args={args[:2]}, kwargs={sanitized_kwargs}"
        )

        try:
            # ツール実行
            result = await func(*args, **kwargs)

            # 実行時間を計算
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            # レスポンスのログ出力（大きなレスポンスは省略）
            if isinstance(result, (dict, list)):
                result_preview = json.dumps(result, ensure_ascii=False, default=str)[
                    :1000
                ]
                if len(str(result)) > 1000:
                    result_preview += "... (truncated)"
                logger.info(
                    f"MCP Tool Response - {tool_name} ({duration_ms:.1f}ms): {result_preview}"
                )
            elif isinstance(result, str) and len(result) > 1000:
                logger.info(
                    f"MCP Tool Response - {tool_name} ({duration_ms:.1f}ms): {result[:1000]}... (truncated)"
                )
            else:
                logger.info(
                    f"MCP Tool Response - {tool_name} ({duration_ms:.1f}ms): {result}"
                )

            return result

        except Exception as e:
            # エラー時も実行時間を計算
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            logger.error(
                f"MCP Tool Error - {tool_name} ({duration_ms:.1f}ms): {type(e).__name__}: {str(e)}"
            )
            raise

    return wrapper


def register_tools(
    mcp: FastMCP,
    db: Database,
    project_context: ProjectContext,
    event_bus: "EventBus",
) -> None:
    """全ツールをMCPサーバーに登録"""
    # Import and delegate to the new modular tools structure
    from .tools import register_tools as new_register_tools

    return new_register_tools(mcp, db, project_context, event_bus)
