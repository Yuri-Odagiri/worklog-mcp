"""
Worklog posting tools for the worklog MCP server.
"""

from mcp.server.fastmcp import Context
from mcp.server.fastmcp import FastMCP

from ..database import Database
from ..models import WorklogEntry

# Import the logging decorator from utils
from ..utils import log_mcp_tool


def register_worklog_posting_tools(
    mcp: FastMCP,
    db: Database,
    notify_web,
) -> None:
    """Register worklog posting tools with the MCP server."""

    @mcp.tool(
        name="post_worklog",
        description="分報（作業ログ）を投稿します。Markdown形式で作業内容、進捗、メモなどを記録できます。",
    )
    @log_mcp_tool
    async def post_entry(user_id: str, markdown_content: str, ctx: Context) -> str:
        """分報を投稿する"""
        try:
            # ユーザー存在確認
            user = await db.get_user(user_id)
            if not user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            # バリデーション
            if not markdown_content or not markdown_content.strip():
                raise ValueError("分報の内容は必須です")

            if len(markdown_content) > 10000:
                raise ValueError("分報は10000文字以内で入力してください")

            await ctx.info("分報を投稿中...")

            # エントリー作成
            entry = WorklogEntry(
                user_id=user_id, markdown_content=markdown_content.strip()
            )

            await db.create_entry(entry)

            # イベントバス経由でWeb側に通知
            await notify_web(
                "entry_created",
                {
                    "user_id": entry.user_id,
                    "user_name": user.name,
                    "markdown_content": entry.markdown_content,
                    "created_at": entry.created_at.isoformat(),
                    "is_reply": False,
                },
            )

            await ctx.info("分報が投稿されました")
            return "分報を投稿しました"

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise
