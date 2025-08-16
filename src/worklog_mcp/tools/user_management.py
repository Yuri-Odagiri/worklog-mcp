"""
User management tools for the worklog MCP server.
"""

import re
from typing import Any, Dict, List

from mcp.server.fastmcp import Context
from mcp.server.fastmcp import FastMCP

from ..database import Database
from ..models import User

# Import the logging decorator from utils
from ..utils import log_mcp_tool


def register_user_management_tools(
    mcp: FastMCP,
    db: Database,
    notify_web,
) -> None:
    """Register user management tools with the MCP server."""

    @mcp.tool(
        name="register_user",
        description="新規ユーザーを分報システムに登録します。初回起動時にのみ必要で、ユーザーID、表示名、テーマカラー、役割(日本語)、性格(200字程度)、外見(性別、年齢、髪の色、肌の色等詳細に500文字程度)を設定できます。",
    )
    @log_mcp_tool
    async def register_user(
        user_id: str,
        name: str,
        role: str,
        ctx: Context,
        theme_color: str = "Blue",
        personality: str = "明るく協力的で、チームワークを重視する性格です。",
        appearance: str = "親しみやすい外見で、いつも笑顔を絶やしません。",
    ) -> str:
        """新規ユーザーを登録する（初回起動時必須）

        Args:
            user_id: あなたのユーザーID（英数字、ハイフン、アンダースコアのみ）
            name: あなたのユーザー名(表示名)
            role: あなたの役割（必須）
            theme_color: あなたのテーマカラー（Red/Blue/Green/Yellow/Purple/Orange/Pink/Cyanのみ）
            personality: あなたの性格（想像で設定可能）。300文字程度。
            appearance: あなたの詳細な見た目（想像で設定可能）。性別、年齢、髪の色、肌の色等詳細に500文字程度。
        """
        try:
            # バリデーション
            if not user_id or not name or not role:
                raise ValueError("user_id、name、roleは必須です")

            # user_idの形式チェック
            if not re.match(r"^[a-zA-Z0-9-_]+$", user_id):
                raise ValueError(
                    "user_idは英数字、ハイフン、アンダースコアのみ使用可能です"
                )

            # 既存ユーザーチェック
            existing_user = await db.get_user(user_id)
            if existing_user:
                raise ValueError(f"ユーザーID '{user_id}' は既に登録されています")

            await ctx.info(f"ユーザー '{user_id}' を登録中...")

            # ユーザー作成（新フィールドはデフォルト値で初期化）
            user = User(
                user_id=user_id,
                name=name,
                theme_color=theme_color,
                role=role,
                personality=personality,
                appearance=appearance,
                description="",  # デフォルト空文字
                model="",  # デフォルト空文字
                mcp="",  # デフォルト空文字
                tools="",  # デフォルト空文字
                avatar_path=None,
            )
            await db.create_user(user)

            # イベントバスにユーザー登録イベントを送信（ビューアーサーバー側でアバター生成）
            user_data = {
                "user_id": user_id,
                "name": name,
                "role": role,
                "personality": personality,
                "appearance": appearance,
                "theme_color": theme_color,
            }
            await notify_web("user_registered", user_data)

            await ctx.info(f"ユーザー '{name}' ({user_id}) の登録が完了しました")
            return f"ユーザー '{name}' ({user_id}) を登録しました"

        except ValueError as e:
            await ctx.error(f"ユーザー登録エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @log_mcp_tool
    async def check_avatar_status(user_id: str, ctx: Context) -> str:
        """アバター生成状況を確認する

        Args:
            user_id: 確認したいユーザーID
        """
        try:
            # ユーザーが存在するかチェック
            user = await db.get_user(user_id)
            if not user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            # アバターファイルの存在確認
            from pathlib import Path

            avatar_path = user.avatar_path
            if not avatar_path or not Path(avatar_path).exists():
                return f"ユーザー '{user_id}' のアバターファイルが見つかりません"

            # ファイルサイズと作成時間で判定（AI生成は通常より大きく、時間もかかる）

            avatar_file = Path(avatar_path)
            file_size = avatar_file.stat().st_size

            # 10KB以下の場合はおそらくグラデーション画像
            if file_size < 10 * 1024:
                return f"ユーザー '{user_id}' のアバター: グラデーション画像（{file_size // 1024}KB）\nAI生成版は背景で処理中です..."
            else:
                return f"ユーザー '{user_id}' のアバター: AI生成版に更新済み（{file_size // 1024}KB）\nパス: {avatar_path}"

        except ValueError as e:
            await ctx.error(str(e))
            raise
        except Exception as e:
            await ctx.error(f"アバター状況確認エラー: {str(e)}")
            raise

    @mcp.tool(
        name="list_users",
        description="分報システムに登録されている全ユーザーの一覧を取得します。各ユーザーの基本情報とアクティビティ状況を確認できます。",
    )
    @log_mcp_tool
    async def list_users(user_id: str, ctx: Context) -> List[Dict[str, Any]]:
        """登録ユーザー一覧を取得"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            await ctx.info("ユーザー一覧を取得中...")

            users = await db.get_all_users()

            result = []
            for user in users:
                result.append(
                    {
                        "user_id": user.user_id,
                        "name": user.name,
                        "theme_color": user.theme_color,
                        "role": user.role,
                        "personality": user.personality,
                        "appearance": user.appearance,
                        "created_at": user.created_at.isoformat(),
                        "last_active": user.last_active.isoformat(),
                    }
                )

            await ctx.info(f"ユーザー一覧取得完了: {len(result)}人")
            return result

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @mcp.tool(
        name="delete_user",
        description="分報システムからユーザーを削除します。関連する分報エントリーも全て削除されます。削除は取り消せませんので注意してください。",
    )
    @log_mcp_tool
    async def delete_user(user_id: str, target_user_id: str, ctx: Context) -> str:
        """ユーザーを削除する

        Args:
            user_id: 削除操作を実行するユーザーID
            target_user_id: 削除対象のユーザーID
        """
        try:
            # 実行者の存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            # 削除対象ユーザーの存在確認
            target_user = await db.get_user(target_user_id)
            if not target_user:
                raise ValueError(
                    f"削除対象のユーザーID '{target_user_id}' が見つかりません"
                )

            # 自分自身の削除は禁止
            if user_id == target_user_id:
                raise ValueError("自分自身を削除することはできません")

            await ctx.info(
                f"ユーザー '{target_user_id}' ({target_user.name}) を削除中..."
            )

            # ユーザー削除実行（関連する分報エントリーも削除される）
            deleted = await db.delete_user(target_user_id)

            if deleted:
                await ctx.info(
                    f"ユーザー '{target_user_id}' とその関連データを削除しました"
                )

                # イベントバスにユーザー削除イベントを送信
                await notify_web(
                    "user_deleted",
                    {
                        "user_id": target_user_id,
                        "name": target_user.name,
                        "deleted_by": user_id,
                    },
                )

                return f"ユーザー '{target_user_id}' ({target_user.name}) を正常に削除しました"
            else:
                raise ValueError(f"ユーザー '{target_user_id}' の削除に失敗しました")

        except ValueError as e:
            await ctx.error(str(e))
            raise
        except Exception as e:
            await ctx.error(f"ユーザー削除エラー: {str(e)}")
            raise
