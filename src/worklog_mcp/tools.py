"""MCPツールの実装"""

import logging
import functools
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import re

from mcp.server.fastmcp import FastMCP, Context

from .database import Database
from .project_context import ProjectContext
from .models import User, WorklogEntry

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
    web_server=None,
) -> None:
    """全ツールをMCPサーバーに登録（Web通知機能付き）"""

    async def get_project_info(ctx: Context) -> Dict[str, Any]:
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

            # アバター画像を即座に生成（グラデーション版）
            from .avatar_generator import generate_user_avatar

            await ctx.info(
                "アバター画像を生成中（即座にグラデーション版を作成、AI版は背景で処理中）..."
            )
            avatar_path = await generate_user_avatar(
                name,
                role,
                personality,
                appearance,
                theme_color,
                user_id,
                project_context,
            )

            # ユーザー作成
            user = User(
                user_id=user_id,
                name=name,
                theme_color=theme_color,
                role=role,
                personality=personality,
                appearance=appearance,
                avatar_path=avatar_path,
            )
            await db.create_user(user)

            await ctx.info(f"ユーザー '{name}' ({user_id}) の登録が完了しました")
            return f"ユーザー '{name}' ({user_id}) を登録しました\nテーマカラー: {theme_color}\n役割: {role}\n性格: {personality}\n外観: {appearance}\nアバター: {avatar_path}\n\nNote: AI生成アバターは背景で処理中です。数分後に 'check_avatar_status {user_id}' で確認できます。"

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

            # Web側に通知（Webサーバーが起動している場合のみ）
            if web_server:
                await web_server.notify_clients(
                    "entry_created",
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "user_name": user.name,
                        "markdown_content": entry.markdown_content,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        "related_entry_id": entry.related_entry_id,
                        "is_reply": False,
                    },
                )

            await ctx.info(f"分報が投稿されました (ID: {entry.id})")
            return f"分報を投稿しました (ID: {entry.id})"

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

    @mcp.tool(
        name="reply_worklog",
        description="既存の分報に返信または続報を投稿します。元の分報に関連する追加情報や返信を投稿する際に使用します。",
    )
    @log_mcp_tool
    async def reply_to_entry(
        user_id: str, related_entry_id: str, markdown_content: str, ctx: Context
    ) -> str:
        """既存の分報に返信・続報を投稿する"""
        try:
            # ユーザー存在確認
            user = await db.get_user(user_id)
            if not user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            # バリデーション
            if not related_entry_id or not markdown_content.strip():
                raise ValueError("関連エントリーIDと返信内容は必須です")

            # 関連エントリーの存在確認
            related_entry = await db.get_entry(related_entry_id)
            if not related_entry:
                raise ValueError(f"エントリーID '{related_entry_id}' が見つかりません")

            await ctx.info(f"エントリー '{related_entry_id}' に返信中...")

            # 返信エントリー作成
            entry = WorklogEntry(
                user_id=user_id,
                markdown_content=markdown_content.strip(),
                related_entry_id=related_entry_id,
            )

            await db.create_entry(entry)

            # Web側に通知（Webサーバーが起動している場合のみ）
            if web_server:
                await web_server.notify_clients(
                    "entry_created",
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "user_name": user.name,
                        "markdown_content": entry.markdown_content,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        "related_entry_id": entry.related_entry_id,
                        "is_reply": True,
                    },
                )

            await ctx.info(f"返信が投稿されました (ID: {entry.id})")
            return f"エントリー '{related_entry_id}' に返信しました (ID: {entry.id})"

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
            raise

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
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "user_name": user_name,
                        "markdown_content": entry.markdown_content,
                        "related_entry_id": entry.related_entry_id,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
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
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "user_name": target_user.name,
                        "markdown_content": entry.markdown_content,
                        "related_entry_id": entry.related_entry_id,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
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
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "user_name": user_name,
                        "markdown_content": entry.markdown_content,
                        "related_entry_id": entry.related_entry_id,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
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

    @mcp.tool(
        name="read_worklog_thread",
        description="特定の分報とそれに関連する返信・続報をスレッド形式で取得します。会話の流れを把握したい場合に使用します。",
    )
    @log_mcp_tool
    async def get_thread(
        user_id: str, entry_id: str, ctx: Context
    ) -> List[Dict[str, Any]]:
        """特定エントリーのスレッド表示（関連する返信を含む）"""
        try:
            # 呼び出し元ユーザー存在確認
            caller_user = await db.get_user(user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{user_id}' が見つかりません")

            if not entry_id:
                raise ValueError("entry_idは必須です")

            await ctx.info(f"エントリー '{entry_id}' のスレッドを取得中...")

            # スレッド取得
            entries = await db.get_thread(entry_id)

            if not entries:
                raise ValueError(f"エントリーID '{entry_id}' が見つかりません")

            # 結果を変換
            result = []
            for entry in entries:
                # ユーザー情報を取得
                user = await db.get_user(entry.user_id)
                user_name = user.name if user else "Unknown"

                result.append(
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "user_name": user_name,
                        "markdown_content": entry.markdown_content,
                        "related_entry_id": entry.related_entry_id,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                    }
                )

            await ctx.info(f"スレッド取得完了: {len(result)}件")
            return result

        except ValueError as e:
            await ctx.error(f"エラー: {str(e)}")
            raise
        except Exception as e:
            await ctx.error(f"予期しないエラー: {str(e)}")
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
                        "id": latest_entry.id,
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

            # Web側に通知（Webサーバーが起動している場合のみ）
            if web_server:
                await web_server.notify_clients(
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

            # Web側に通知（Webサーバーが起動している場合のみ）
            if web_server:
                await web_server.notify_clients(
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
