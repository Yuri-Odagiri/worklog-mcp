"""
Worklog reading tools for the worklog MCP server.
"""

from typing import Any, Dict, List, Optional

from mcp import Context
from mcp.server.fastmcp import FastMCP

from ..database import Database

# Import the logging decorator from the main tools module
from ..tools import log_mcp_tool


def register_worklog_reading_tools(
    mcp: FastMCP,
    db: Database,
) -> None:
    """Register worklog reading tools with the MCP server."""

    @mcp.tool(
        name="read_timeline",
        description="分報のタイムライン（時系列一覧）を取得します。全体または特定ユーザーの分報を時間・件数で絞り込んで表示できます。",
    )
    @log_mcp_tool
    async def get_timeline(
        user_id: str,
        ctx: Context,
        target_user_id: Optional[str] = None,
        hours: Optional[int] = None,
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """タイムライン取得（時間または件数ベース）"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            # パラメータ検証
            if hours and count:
                raise ValueError("hoursとcountは同時に指定できません")

            # デフォルト値設定
            if not hours and not count:
                hours = 24  # デフォルトは過去24時間

            await ctx.info("タイムラインを取得中...")

            # タイムライン取得
            entries = await db.get_timeline(target_user_id, hours, count)

            # 結果をJSONシリアライザブルな形式に変換
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

            await ctx.info(f"タイムライン取得完了: {len(result)}件")
            return result

        except ValueError as e:
            await ctx.error(f"パラメータエラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @mcp.tool(
        name="read_user_worklogs",
        description="特定ユーザーの最近の分報を取得します。指定した時間範囲内でそのユーザーが投稿した全ての分報を確認できます。",
    )
    @log_mcp_tool
    async def get_recent_entries(
        user_id: str, ctx: Context, target_user_id: str, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """特定ユーザーの最近の分報を取得"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            if not target_user_id:
                raise ValueError("target_user_idは必須です")

            # 対象ユーザー存在確認
            target_user = await db.get_user(target_user_id)
            if not target_user:
                raise ValueError(f"ユーザーID '{target_user_id}' が見つかりません")

            await ctx.info(
                f"ユーザー '{target_user.name}' の過去{hours}時間の分報を取得中..."
            )

            # エントリー取得
            entries = await db.get_timeline(target_user_id, hours)

            # 結果を変換
            result = []
            for entry in entries:
                result.append(
                    {
                        "user_id": entry.user_id,
                        "user_name": target_user.name,
                        "markdown_content": entry.markdown_content,
                        "created_at": entry.created_at.isoformat(),
                    }
                )

            await ctx.info(f"取得完了: {len(result)}件")
            return result

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise
