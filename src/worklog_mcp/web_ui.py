"""シンプルなWebビューアー実装"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .database import Database

logger = logging.getLogger(__name__)


class WebDatabaseAdapter:
    """Web API用のデータベースアダプター"""

    def __init__(self, database: Database):
        self.db = database

    async def get_entries_for_api(
        self,
        page: int = 1,
        limit: int = 20,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Web API用エントリー取得"""

        if search:
            entries = await self.db.search_entries(search, user_id=user_id)
        else:
            count = limit * page  # ページネーション用に多めに取得
            entries = await self.db.get_timeline(user_id=user_id, count=count)

        # ページネーション適用
        offset = (page - 1) * limit
        paginated_entries = entries[offset : offset + limit]

        # ユーザー情報を効率的に取得
        user_ids = list(set(entry.user_id for entry in paginated_entries))
        users_dict = {}
        for uid in user_ids:
            user = await self.db.get_user(uid)
            if user:
                users_dict[uid] = user

        # レスポンス形式に変換
        result_entries = []
        for entry in paginated_entries:
            user = users_dict.get(entry.user_id)
            result_entries.append(
                {
                    "id": entry.id,
                    "user_id": entry.user_id,
                    "markdown_content": entry.markdown_content,
                    "related_entry_id": entry.related_entry_id,
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat(),
                    "user_name": user.name if user else entry.user_id,
                    "user_avatar_path": user.avatar_path if user else None,
                }
            )

        return {
            "entries": result_entries,
            "page": page,
            "limit": limit,
            "total_count": len(entries),
        }

    async def get_users_for_api(self) -> List[Dict[str, Any]]:
        """Web API用ユーザー一覧取得"""
        users = await self.db.get_all_users()
        return [
            {
                "user_id": user.user_id,
                "name": user.name,
                "theme_color": user.theme_color,
                "role": user.role,
                "personality": user.personality,
                "appearance": user.appearance,
                "avatar_path": user.avatar_path,
                "created_at": user.created_at.isoformat(),
                "last_active": user.last_active.isoformat(),
            }
            for user in users
        ]

    async def get_thread_for_api(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Web API用スレッド取得"""
        thread_entries = await self.db.get_thread(entry_id)
        if not thread_entries:
            return None

        # ユーザー情報取得
        user_ids = list(set(entry.user_id for entry in thread_entries))
        users_dict = {}
        for user_id in user_ids:
            user = await self.db.get_user(user_id)
            if user:
                users_dict[user_id] = user

        main_entry = thread_entries[0]
        replies = thread_entries[1:] if len(thread_entries) > 1 else []

        main_user = users_dict.get(main_entry.user_id)
        result = {
            "id": main_entry.id,
            "user_id": main_entry.user_id,
            "markdown_content": main_entry.markdown_content,
            "related_entry_id": main_entry.related_entry_id,
            "created_at": main_entry.created_at.isoformat(),
            "updated_at": main_entry.updated_at.isoformat(),
            "user_name": main_user.name if main_user else main_entry.user_id,
            "user_avatar_path": main_user.avatar_path if main_user else None,
            "replies": [],
        }

        for reply in replies:
            reply_user = users_dict.get(reply.user_id)
            result["replies"].append(
                {
                    "id": reply.id,
                    "user_id": reply.user_id,
                    "markdown_content": reply.markdown_content,
                    "created_at": reply.created_at.isoformat(),
                    "user_name": reply_user.name if reply_user else reply.user_id,
                    "user_avatar_path": reply_user.avatar_path if reply_user else None,
                }
            )

        return result

    async def delete_entry_for_api(self, entry_id: str) -> bool:
        """エントリー削除（Web API用）"""
        return await self.db.delete_entry(entry_id)

    async def truncate_entries_for_api(self) -> int:
        """全エントリー削除（Web API用）"""
        return await self.db.truncate_entries()


class WebUIServer:
    """分報Web UIサーバークラス"""

    def __init__(self, db: Database, project_context=None):
        self.db_adapter = WebDatabaseAdapter(db)
        self.project_context = project_context
        self.app = FastAPI(title="分報ビューアー", version="1.0.0")
        self.sse_connections: List[asyncio.Queue] = []
        self._setup_routes()
        self._setup_static_files()

    def _setup_routes(self):
        """APIルート設定"""

        @self.app.get("/api/entries")
        async def get_entries(
            page: int = Query(1, ge=1, description="ページ番号"),
            limit: int = Query(20, ge=1, le=100, description="件数"),
            user_id: Optional[str] = Query(None, description="ユーザーID"),
            search: Optional[str] = Query(None, description="検索キーワード"),
        ):
            """エントリー一覧取得"""
            try:
                result = await self.db_adapter.get_entries_for_api(
                    page=page, limit=limit, user_id=user_id, search=search
                )
                return result
            except Exception as e:
                logger.error(f"API Error in get_entries: {e}")
                raise HTTPException(status_code=500, detail="エントリー取得エラー")

        @self.app.get("/api/users")
        async def get_users():
            """ユーザー一覧取得"""
            try:
                return await self.db_adapter.get_users_for_api()
            except Exception as e:
                logger.error(f"API Error in get_users: {e}")
                raise HTTPException(status_code=500, detail="ユーザー取得エラー")

        @self.app.get("/api/entries/{entry_id}")
        async def get_entry_thread(entry_id: str):
            """特定エントリーとスレッド取得"""
            try:
                thread_data = await self.db_adapter.get_thread_for_api(entry_id)
                if not thread_data:
                    raise HTTPException(404, "エントリーが見つかりません")
                return thread_data
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"API Error in get_entry_thread: {e}")
                raise HTTPException(status_code=500, detail="スレッド取得エラー")

        @self.app.get("/events")
        async def stream_events():
            """SSEストリーム"""
            queue = asyncio.Queue(maxsize=10)
            self.sse_connections.append(queue)

            return StreamingResponse(
                self._event_stream(queue),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"API Error: {exc}")
            return JSONResponse(
                status_code=500, content={"error": "内部サーバーエラーが発生しました"}
            )

        @self.app.exception_handler(404)
        async def not_found_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=404, content={"error": "リソースが見つかりません"}
            )

        @self.app.delete("/api/entries/{entry_id}")
        async def delete_entry(entry_id: str):
            """エントリー削除"""
            try:
                result = await self.db_adapter.delete_entry_for_api(entry_id)
                if not result:
                    raise HTTPException(404, "エントリーが見つかりません")

                # クライアントに削除通知
                await self.notify_clients("entry_deleted", {"id": entry_id})

                return {"success": True, "message": "エントリーを削除しました"}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"API Error in delete_entry: {e}")
                raise HTTPException(status_code=500, detail="エントリー削除エラー")

        @self.app.delete("/api/entries")
        async def truncate_entries(request: Request):
            """全エントリー削除"""
            try:
                # リクエストボディを取得（オプション）
                body = {}
                try:
                    body = await request.json()
                except Exception as e:
                    logger.debug(
                        f"JSONボディの解析に失敗（デフォルト動作を継続）: {type(e).__name__}: {e}"
                    )

                delete_option = body.get("delete_option", "worklogs_only")
                include_users = delete_option == "full_reset"

                logger.debug(
                    f"削除オプション: {delete_option}, ユーザー削除: {include_users}"
                )

                # 新しいtruncate_allメソッドを使用
                avatar_dir = (
                    self.project_context.get_avatar_path() if include_users else None
                )
                logger.debug(f"アバターディレクトリ: {avatar_dir}")

                result = await self.db_adapter.db.truncate_all(
                    include_users=include_users, avatar_dir=avatar_dir
                )
                logger.debug(f"削除結果: {result}")

                # クライアントに全削除通知
                await self.notify_clients(
                    "entries_truncated",
                    {
                        "deleted_count": result["entries_deleted"],
                        "users_deleted": result["users_deleted"],
                        "avatars_deleted": result["avatars_deleted"],
                        "delete_option": delete_option,
                    },
                )

                message = f"{result['entries_deleted']} 件の分報を削除しました"
                if include_users and result["users_deleted"] > 0:
                    message += f"（{result['users_deleted']} 件のユーザー情報も削除）"
                if include_users and result["avatars_deleted"] > 0:
                    message += f"（{result['avatars_deleted']} 件のアバター画像も削除）"

                return {"success": True, "message": message, "result": result}
            except Exception as e:
                logger.error(f"API Error in truncate_entries: {type(e).__name__}: {e}")
                logger.debug("truncate_entries エラー詳細", exc_info=True)
                raise HTTPException(status_code=500, detail="全エントリー削除エラー")

    def _setup_static_files(self):
        """静的ファイル設定"""
        static_path = os.path.join(os.path.dirname(__file__), "static")

        # 静的ファイル配信（ディレクトリが存在する場合のみ）
        if os.path.exists(static_path):
            self.app.mount("/static", StaticFiles(directory=static_path), name="static")

        # アバター画像配信（プロジェクト別パス）
        if self.project_context:
            avatar_path = self.project_context.get_avatar_path()
        else:
            # フォールバック（プロジェクトコンテキストなし）
            avatar_path = os.path.expanduser("~/.worklog/default/avatar")

        if os.path.exists(avatar_path):
            self.app.mount("/avatar", StaticFiles(directory=avatar_path), name="avatar")

        # ルートアクセス時のindex.html配信
        @self.app.get("/")
        async def serve_index():
            index_path = os.path.join(static_path, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            else:
                return JSONResponse(
                    status_code=200,
                    content={"message": "分報MCPサーバー Web API", "status": "running"},
                )

        # favicon.ico配信
        @self.app.get("/favicon.ico")
        async def serve_favicon():
            favicon_path = os.path.join(static_path, "favicon.ico")
            if os.path.exists(favicon_path):
                return FileResponse(favicon_path)
            else:
                raise HTTPException(status_code=404, detail="Favicon not found")

    async def _event_stream(self, queue: asyncio.Queue):
        """SSEイベントストリーム生成"""
        try:
            # 接続通知
            yield 'data: {"type":"connected"}\n\n'

            while True:
                try:
                    # 30秒タイムアウトでイベント待機
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_data = json.dumps(event, ensure_ascii=False)
                    yield f"data: {event_data}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield 'data: {"type":"ping"}\n\n'

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            # 接続終了時のクリーンアップ
            if queue in self.sse_connections:
                self.sse_connections.remove(queue)

    async def notify_clients(self, event_type: str, data: dict):
        """全クライアントへの通知"""
        if not self.sse_connections:
            return

        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        # 切断された接続を追跡
        disconnected = []
        for queue in self.sse_connections:
            try:
                queue.put_nowait(event)  # ノンブロッキング
            except asyncio.QueueFull:
                logger.warning("SSE queue full, skipping event")
            except Exception as e:
                logger.debug(
                    f"SSE接続でエラーが発生（切断として処理）: {type(e).__name__}: {e}"
                )
                disconnected.append(queue)

        # 切断されたクライアントを削除
        for queue in disconnected:
            self.sse_connections.remove(queue)

        logger.debug(f"Notified {len(self.sse_connections)} clients: {event_type}")
