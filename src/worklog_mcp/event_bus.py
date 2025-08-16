"""
イベントバス実装 - MCPサーバーとWebビューアー間の非同期通信
SQLiteベースの軽量イベントキューを提供
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class EventBus:
    """プロセス間通信用のイベントバス"""

    def __init__(self, db_path: Path):
        """
        イベントバスの初期化

        Args:
            db_path: イベントデータベースのパス
        """
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """データベースとテーブルの初期化"""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0
            )
        """)

        # インデックスの作成
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created_at 
            ON events(created_at)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_processed 
            ON events(processed, created_at)
        """)

        await self._db.commit()
        logger.info(f"イベントバス初期化完了: {self.db_path}")

    async def close(self) -> None:
        """データベース接続のクローズ"""
        if self._db:
            await self._db.close()
            self._db = None

    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        イベントを発行

        Args:
            event_type: イベントタイプ
            data: イベントデータ
        """
        if not self._db:
            raise RuntimeError("EventBus not initialized")

        try:
            await self._db.execute(
                """
                INSERT INTO events (event_type, data, created_at)
                VALUES (?, ?, ?)
                """,
                (event_type, json.dumps(data), datetime.now().isoformat()),
            )
            await self._db.commit()
            logger.debug(f"イベント発行: {event_type}")
        except Exception as e:
            logger.error(f"イベント発行エラー: {e}")
            raise

    async def consume(
        self,
        limit: int = 100,
        mark_processed: bool = True,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        未処理のイベントを取得

        Args:
            limit: 取得する最大イベント数
            mark_processed: 取得後に処理済みマークを付けるか
            since: この時刻以降のイベントのみ取得

        Returns:
            イベントのリスト
        """
        if not self._db:
            raise RuntimeError("EventBus not initialized")

        try:
            # 未処理イベントを取得
            query = """
                SELECT id, event_type, data, created_at 
                FROM events 
                WHERE processed = 0
            """
            params = []

            if since:
                query += " AND created_at > ?"
                params.append(since.isoformat())

            query += " ORDER BY created_at ASC LIMIT ?"
            params.append(limit)

            cursor = await self._db.execute(query, params)
            rows = await cursor.fetchall()

            events = []
            event_ids = []

            for row in rows:
                events.append(
                    {
                        "id": row["id"],
                        "event_type": row["event_type"],
                        "data": json.loads(row["data"]),
                        "created_at": row["created_at"],
                    }
                )
                event_ids.append(row["id"])

            # 処理済みマークを付ける
            if mark_processed and event_ids:
                placeholders = ",".join("?" * len(event_ids))
                await self._db.execute(
                    f"UPDATE events SET processed = 1 WHERE id IN ({placeholders})",
                    event_ids,
                )
                await self._db.commit()

            return events

        except Exception as e:
            logger.error(f"イベント取得エラー: {e}")
            raise

    async def cleanup(self, older_than_hours: int = 24) -> int:
        """
        古いイベントを削除

        Args:
            older_than_hours: この時間より古いイベントを削除

        Returns:
            削除されたイベント数
        """
        if not self._db:
            raise RuntimeError("EventBus not initialized")

        try:
            cutoff = datetime.now() - timedelta(hours=older_than_hours)
            cursor = await self._db.execute(
                "DELETE FROM events WHERE created_at < ?", (cutoff.isoformat(),)
            )
            await self._db.commit()
            deleted = cursor.rowcount

            if deleted > 0:
                logger.info(f"古いイベント {deleted} 件を削除しました")

            return deleted

        except Exception as e:
            logger.error(f"イベントクリーンアップエラー: {e}")
            raise

    async def get_pending_count(self) -> int:
        """
        未処理イベント数を取得

        Returns:
            未処理イベント数
        """
        if not self._db:
            raise RuntimeError("EventBus not initialized")

        try:
            cursor = await self._db.execute(
                "SELECT COUNT(*) as count FROM events WHERE processed = 0"
            )
            row = await cursor.fetchone()
            return row["count"] if row else 0

        except Exception as e:
            logger.error(f"イベント数取得エラー: {e}")
            raise


class EventBusPoller:
    """イベントバスのポーリング機能"""

    def __init__(self, event_bus: EventBus, poll_interval: float = 0.5):
        """
        ポーラーの初期化

        Args:
            event_bus: イベントバスインスタンス
            poll_interval: ポーリング間隔（秒）
        """
        self.event_bus = event_bus
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, callback) -> None:
        """
        ポーリング開始

        Args:
            callback: イベント受信時のコールバック関数
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop(callback))
        logger.info("イベントポーリング開始")

    async def stop(self) -> None:
        """ポーリング停止"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("イベントポーリング停止")

    async def _poll_loop(self, callback) -> None:
        """ポーリングループ"""
        while self._running:
            try:
                # 未処理イベントを取得
                events = await self.event_bus.consume(limit=50)

                # イベントを並行処理でコールバックに送信
                tasks = []
                for event in events:
                    task = asyncio.create_task(self._process_event(callback, event))
                    tasks.append(task)

                # 全タスクの完了を待機（タイムアウト付き）
                if tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*tasks, return_exceptions=True),
                            timeout=30.0,  # 30秒でタイムアウト
                        )
                    except asyncio.TimeoutError:
                        logger.warning("一部のイベント処理がタイムアウトしました")

                # 定期的にクリーンアップ（1時間に1回程度）
                if asyncio.get_event_loop().time() % 3600 < self.poll_interval:
                    await self.event_bus.cleanup(older_than_hours=24)

            except Exception as e:
                logger.error(f"ポーリングエラー: {e}")

            # 次のポーリングまで待機
            await asyncio.sleep(self.poll_interval)

    async def _process_event(self, callback, event) -> None:
        """個別イベントの処理"""
        try:
            await callback(event["event_type"], event["data"])
        except Exception as e:
            logger.error(f"イベント処理エラー ({event['event_type']}): {e}")
