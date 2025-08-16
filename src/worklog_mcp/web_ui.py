"""シンプルなWebビューアー実装"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .database import Database
from .models import WorklogEntry

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
                    "created_at": entry.created_at.isoformat(),
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

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """個別ユーザー情報を取得"""
        user = await self.db.get_user(user_id)
        if not user:
            return None
        
        return {
            "user_id": user.user_id,
            "name": user.name,
            "role": user.role,
            "personality": user.personality,
            "appearance": user.appearance,
            "theme_color": user.theme_color,
            "avatar_path": user.avatar_path,
            "created_at": user.created_at.isoformat(),
            "last_active": user.last_active.isoformat()
        }

    async def get_thread_for_api(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Web API用スレッド取得（スレッド機能は削除されたため単一エントリーを返す）"""
        # 単一エントリーの取得
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute(
                "SELECT id, user_id, markdown_content, created_at FROM entries WHERE id = ?",
                (entry_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        entry = WorklogEntry(
            id=row[0],
            user_id=row[1],
            markdown_content=row[2],
            created_at=datetime.fromisoformat(row[3])
            if isinstance(row[3], str)
            else row[3],
        )

        # ユーザー情報取得
        user = await self.db.get_user(entry.user_id)

        return {
            "id": entry.id,
            "user_id": entry.user_id,
            "markdown_content": entry.markdown_content,
            "created_at": entry.created_at.isoformat(),
            "user_name": user.name if user else entry.user_id,
            "user_avatar_path": user.avatar_path if user else None,
            "replies": [],  # スレッド機能は削除されたため空配列
        }

    async def delete_entry_for_api(self, entry_id: str) -> bool:
        """エントリー削除（Web API用）"""
        return await self.db.delete_entry(entry_id)

    async def truncate_entries_for_api(self) -> int:
        """全エントリー削除（Web API用）"""
        return await self.db.truncate_entries()


class WebUIServer:
    """分報Web UIサーバークラス"""

    def __init__(self, db: Database, project_context=None, job_queue=None, event_bus=None):
        self.db_adapter = WebDatabaseAdapter(db)
        self.project_context = project_context
        self.job_queue = job_queue
        self.event_bus = event_bus
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

        @self.app.post("/api/users/{user_id}/regenerate-avatar")
        async def regenerate_user_avatar(user_id: str):
            """ユーザーアバターの個別再生成"""
            try:
                # ユーザー情報を取得
                user = await self.db_adapter.get_user(user_id)
                if not user:
                    raise HTTPException(404, "ユーザーが見つかりません")

                # 1. 即座にグラデーション画像を生成
                from worklog_mcp.avatar_generator import generate_gradient_avatar
                
                theme_color = user.get("theme_color", "Blue")
                temp_avatar_path = await generate_gradient_avatar(
                    theme_color, user_id, self.project_context
                )
                
                # 2. DBを仮アバターパスで即座に更新
                await self.db_adapter.db.update_user_avatar_path(user_id, temp_avatar_path)
                
                # 3. EventBusで即座にアバター更新を通知（仮画像として）
                if hasattr(self, 'event_bus') and self.event_bus:
                    await self.event_bus.publish(
                        "avatar_updated",
                        {"user_id": user_id, "avatar_path": temp_avatar_path}
                    )
                
                # 4. Webクライアントにも即座に通知
                await self.notify_clients(
                    "avatar_updated",
                    {"user_id": user_id, "avatar_path": temp_avatar_path}
                )

                # 5. ジョブキューにavatar_generationジョブをエンキュー（AI生成用）
                if hasattr(self, 'job_queue') and self.job_queue:
                    job_payload = {
                        "user_id": user["user_id"],
                        "name": user["name"],
                        "role": user.get("role", ""),
                        "personality": user.get("personality", ""),
                        "appearance": user.get("appearance", ""),
                        "theme_color": theme_color
                    }
                    
                    job_id = await self.job_queue.enqueue("avatar_generation", job_payload)
                    
                    logger.info(f"アバター再生成ジョブを開始: {user_id} (Job ID: {job_id})")
                    
                    return {
                        "success": True, 
                        "message": f"{user['name']} のアバター再生成を開始しました",
                        "job_id": job_id,
                        "temp_avatar_path": temp_avatar_path
                    }
                else:
                    # ジョブキューが利用できない場合はエラー
                    logger.error("ジョブキューが初期化されていません")
                    raise HTTPException(503, "アバター生成サービスが利用できません")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"API Error in regenerate_user_avatar: {e}")
                raise HTTPException(status_code=500, detail="アバター再生成エラー")

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

                logger.debug(f"削除オプション: {delete_option}")

                # 完全リセットの場合は新しいメソッドを使用
                if delete_option == "full_reset":
                    result = await self.db_adapter.db.full_project_reset(
                        self.project_context
                    )
                    logger.debug(f"完全リセット結果: {result}")

                    # クライアントに完全リセット通知
                    await self.notify_clients(
                        "entries_truncated",
                        {
                            "deleted_count": "全データ",
                            "users_deleted": "全ユーザー",
                            "avatars_deleted": "全アバター",
                            "eventbus_deleted": result["eventbus_deleted"],
                            "jobqueue_deleted": result["jobqueue_deleted"],
                            "project_directory_deleted": result[
                                "project_directory_deleted"
                            ],
                            "delete_option": delete_option,
                        },
                    )

                    if result["project_directory_deleted"]:
                        message = "プロジェクトを完全にリセットしました（全データ、DB、EventBus、JobQueue、画像を削除）"
                    else:
                        message = "プロジェクトのリセットに失敗しました"

                    return {
                        "success": result["project_directory_deleted"],
                        "message": message,
                        "result": result,
                    }
                else:
                    # 従来の動作（分報のみまたは分報+ユーザー）
                    include_users = delete_option == "users_and_worklogs"

                    # 新しいtruncate_allメソッドを使用
                    avatar_dir = (
                        self.project_context.get_avatar_path()
                        if include_users
                        else None
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
                        message += (
                            f"（{result['users_deleted']} 件のユーザー情報も削除）"
                        )
                    if include_users and result["avatars_deleted"] > 0:
                        message += (
                            f"（{result['avatars_deleted']} 件のアバター画像も削除）"
                        )

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
