"""
Worklog search tools for the worklog MCP server.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp import Context
from mcp.server.fastmcp import FastMCP

from ..database import Database

# Import the logging decorator from the main tools module
from ..tools import log_mcp_tool


def register_worklog_search_tools(
    mcp: FastMCP,
    db: Database,
) -> None:
    """Register worklog search tools with the MCP server."""

    @mcp.tool(
        name="search_worklogs",
        description="分報をキーワード検索します。特定の単語やフレーズを含む分報を検索し、ユーザーや日付範囲で絞り込むことができます。",
    )
    @log_mcp_tool
    async def search_entries(
        user_id: str,
        ctx: Context,
        keyword: str,
        target_user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """分報を検索する"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            if not keyword.strip():
                raise ValueError("検索キーワードは必須です")

            # 日付パラメータの変換
            date_from_dt = None
            date_to_dt = None

            if date_from:
                try:
                    date_from_dt = datetime.fromisoformat(date_from)
                except ValueError:
                    raise ValueError(
                        "date_fromの形式が正しくありません (YYYY-MM-DD形式)"
                    )

            if date_to:
                try:
                    date_to_dt = datetime.fromisoformat(date_to)
                except ValueError:
                    raise ValueError("date_toの形式が正しくありません (YYYY-MM-DD形式)")

            await ctx.info(f"キーワード '{keyword}' で検索中...")

            # 検索実行
            entries = await db.search_entries(
                keyword, target_user_id, date_from_dt, date_to_dt
            )

            # 結果を変換
            result = []
            for entry in entries:
                # ユーザー情報を取得
                user = await db.get_user(entry.user_id)
                user_name = user.name if user else "Unknown"

                result.append(
                    {
                        "user_id": entry.user_id,
                        "user_name": user_name,
                        "markdown_content": entry.markdown_content,
                        "created_at": entry.created_at.isoformat(),
                    }
                )

            await ctx.info(f"検索完了: {len(result)}件")
            return result

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise
