"""
Worklog analytics tools for the worklog MCP server.
"""

from typing import Any, Dict, Optional

from mcp import Context
from mcp.server.fastmcp import FastMCP

from ..database import Database

# Import the logging decorator from the main tools module
from ..tools import log_mcp_tool


def register_worklog_analytics_tools(
    mcp: FastMCP,
    db: Database,
) -> None:
    """Register worklog analytics tools with the MCP server."""

    @mcp.tool(
        name="get_team_status",
        description="チーム全体の現在の状況（各メンバーの最新投稿状況）を取得します。チーム全体の活動状況を一覧で確認できます。",
    )
    @log_mcp_tool
    async def get_team_status(user_id: str, ctx: Context) -> Dict[str, Any]:
        """チーム全体の現在の状況（各メンバーの最新エントリー）"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            await ctx.info("チーム状況を取得中...")

            # 全ユーザー取得
            users = await db.get_all_users()

            team_status = {"total_users": len(users), "members": []}

            for user in users:
                # 各ユーザーの最新エントリーを取得
                recent_entries = await db.get_timeline(user.user_id, count=1)
                latest_entry = recent_entries[0] if recent_entries else None

                member_info = {
                    "user_id": user.user_id,
                    "name": user.name,
                    "last_active": user.last_active.isoformat(),
                    "latest_entry": None,
                }

                if latest_entry:
                    member_info["latest_entry"] = {
                        "content_preview": latest_entry.markdown_content[:100] + "..."
                        if len(latest_entry.markdown_content) > 100
                        else latest_entry.markdown_content,
                        "created_at": latest_entry.created_at.isoformat(),
                    }

                team_status["members"].append(member_info)

            await ctx.info(f"チーム状況取得完了: {len(users)}人")
            return team_status

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @mcp.tool(
        name="get_user_stats",
        description="特定ユーザーの分報投稿統計情報を取得します。投稿数、活動期間、最近の投稿状況などの詳細データを確認できます。",
    )
    @log_mcp_tool
    async def get_stats(
        user_id: str, target_user_id: str, ctx: Context
    ) -> Dict[str, Any]:
        """ユーザー別統計情報"""
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

            await ctx.info(f"ユーザー '{target_user.name}' の統計情報を取得中...")

            # 統計情報取得
            stats = await db.get_user_stats(target_user_id)

            # ユーザー情報を追加
            result = {
                "user_id": target_user_id,
                "user_name": target_user.name,
                "total_posts": stats["total_posts"],
                "today_posts": stats["today_posts"],
                "first_post": stats["first_post"],
                "latest_post": stats["latest_post"],
                "member_since": target_user.created_at.isoformat(),
                "last_active": target_user.last_active.isoformat(),
            }

            await ctx.info("統計情報取得完了")
            return result

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @mcp.tool(
        name="generate_worklog_summary",
        description="指定した期間の分報をサマリーとして要約します。チーム全体または特定ユーザーの活動をまとめて確認したい場合に使用します。",
    )
    @log_mcp_tool
    async def generate_summary(
        user_id: str, ctx: Context, target_user_id: Optional[str] = None, hours: int = 8
    ) -> Dict[str, Any]:
        """分報サマリー生成（対象ユーザー指定可能）"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            # 対象ユーザーが指定されている場合は存在確認
            if target_user_id:
                target_user = await db.get_user(target_user_id)
                if not target_user:
                    raise ValueError(f"ユーザーID '{target_user_id}' が見つかりません")

            await ctx.info(f"過去{hours}時間のサマリーを生成中...")

            # エントリー取得
            entries = await db.get_timeline(target_user_id, hours)

            if not entries:
                return {
                    "period_hours": hours,
                    "target_user": target_user_id,
                    "summary": "指定された期間内に投稿がありませんでした。",
                    "entry_count": 0,
                    "users_count": 0,
                }

            # 基本統計
            entry_count = len(entries)
            user_ids = set(entry.user_id for entry in entries)
            users_count = len(user_ids)

            # 内容の結合（長すぎる場合は制限）
            content_parts = []
            total_length = 0
            max_length = 5000  # サマリー生成のための最大文字数

            for entry in entries:
                content = f"[{entry.user_id}] {entry.markdown_content}"
                if total_length + len(content) > max_length:
                    break
                content_parts.append(content)
                total_length += len(content)

            combined_content = "\n\n".join(content_parts)

            # 簡単なサマリー生成（実装は基本的なもの）
            summary_lines = []
            if target_user_id:
                summary_lines.append(
                    f"ユーザー {target_user_id} の過去{hours}時間の活動:"
                )
            else:
                summary_lines.append(f"チーム全体の過去{hours}時間の活動:")

            summary_lines.append(f"- 投稿数: {entry_count}件")
            summary_lines.append(f"- 参加ユーザー: {users_count}人")

            # キーワード抽出（簡単な実装）
            words = combined_content.split()
            word_freq = {}
            for word in words:
                if len(word) > 3:  # 3文字以上の単語のみ
                    word_freq[word] = word_freq.get(word, 0) + 1

            # 頻出単語トップ5
            if word_freq:
                top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]
                summary_lines.append(
                    "- よく使われた単語: "
                    + ", ".join([f"{w}({c}回)" for w, c in top_words])
                )

            summary = "\n".join(summary_lines)

            result = {
                "period_hours": hours,
                "target_user": target_user_id,
                "summary": summary,
                "entry_count": entry_count,
                "users_count": users_count,
                "entries": [
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "content_preview": entry.markdown_content[:100],
                        "created_at": entry.created_at.isoformat(),
                    }
                    for entry in entries[:10]  # 最新10件のプレビュー
                ],
            }

            await ctx.info(f"サマリー生成完了 ({entry_count}件の投稿を分析)")
            return result

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise
