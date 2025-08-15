"""
Worklog management tools for the worklog MCP server.
"""

from typing import Optional

from mcp import Context
from mcp.server.fastmcp import FastMCP

from ..database import Database

# Import the logging decorator from utils
from ..utils import log_mcp_tool


def register_worklog_management_tools(
    mcp: FastMCP,
    db: Database,
    notify_web,
) -> None:
    """Register worklog management tools with the MCP server."""

    @log_mcp_tool
    async def delete_entry(user_id: str, entry_id: str, ctx: Context) -> str:
        """分報を削除する"""
        try:
            # ユーザー存在確認
            user = await db.get_user(user_id)
            if not user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            if not entry_id:
                raise ValueError("entry_idは必須です")

            # 削除対象エントリーの存在確認
            entry = await db.get_entry(entry_id)
            if not entry:
                raise ValueError(f"エントリーID '{entry_id}' が見つかりません")

            # 削除権限チェック（投稿者本人のみ削除可能）
            if entry.user_id != user_id:
                raise ValueError("自分の投稿のみ削除できます")

            await ctx.info(f"エントリー '{entry_id}' を削除中...")

            # エントリー削除
            deleted = await db.delete_entry(entry_id)

            if not deleted:
                raise ValueError("削除に失敗しました")

            # イベントバス経由でWeb側に通知
            await notify_web(
                "entry_deleted",
                {"id": entry_id, "user_id": user_id},
            )

            await ctx.info(f"エントリー '{entry_id}' が削除されました")
            return f"分報 (ID: {entry_id}) を削除しました"

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @log_mcp_tool
    async def truncate_entries(
        user_id: str, ctx: Context, target_user_id: Optional[str] = None
    ) -> str:
        """分報の全削除（オプションで特定ユーザーのみ）"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            if target_user_id:
                # 特定ユーザーの分報削除（自分の投稿のみ）
                if target_user_id != user_id:
                    raise ValueError("自分の投稿のみ削除できます")

                target_user = await db.get_user(target_user_id)
                if not target_user:
                    raise ValueError(f"ユーザーID '{target_user_id}' が見つかりません")

                await ctx.info(f"ユーザー '{target_user.name}' の全分報を削除中...")
                deleted_count = await db.truncate_entries(target_user_id)

                message = f"ユーザー '{target_user.name}' の分報 {deleted_count} 件を削除しました"
            else:
                # 全分報削除（管理機能として実装、現在は自分の投稿のみに制限）
                await ctx.info("自分の全分報を削除中...")
                deleted_count = await db.truncate_entries(user_id)

                message = f"あなたの分報 {deleted_count} 件を削除しました"

            # イベントバス経由でWeb側に通知
            await notify_web(
                "entries_truncated",
                {
                    "user_id": target_user_id or user_id,
                    "deleted_count": deleted_count,
                },
            )

            await ctx.info(message)
            return message

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise
