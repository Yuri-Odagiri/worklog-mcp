"""
アバター生成ジョブキューシステム
長時間かかる処理をEventBusから分離して非同期実行
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """ジョブステータス"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobQueue:
    """ジョブキューシステム"""

    def __init__(self, db_path: Path):
        """
        ジョブキューの初期化

        Args:
            db_path: ジョブデータベースのパス
        """
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """データベースとテーブルの初期化"""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)

        # インデックスの作成
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status_created 
            ON jobs(status, created_at)
        """)

        await self._db.commit()
        logger.info(f"ジョブキュー初期化完了: {self.db_path}")

    async def close(self) -> None:
        """データベース接続のクローズ"""
        if self._db:
            await self._db.close()
            self._db = None

    async def enqueue(self, job_type: str, payload: Dict[str, Any]) -> int:
        """
        ジョブをキューに追加

        Args:
            job_type: ジョブタイプ
            payload: ジョブデータ

        Returns:
            ジョブID
        """
        if not self._db:
            raise RuntimeError("JobQueue not initialized")

        try:
            cursor = await self._db.execute(
                """
                INSERT INTO jobs (job_type, payload, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    job_type,
                    json.dumps(payload),
                    JobStatus.PENDING.value,
                    datetime.now().isoformat(),
                ),
            )
            await self._db.commit()
            job_id = cursor.lastrowid
            logger.info(f"ジョブ追加: {job_type} (ID: {job_id})")
            return job_id
        except Exception as e:
            logger.error(f"ジョブ追加エラー: {e}")
            raise

    async def dequeue(self, job_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        ジョブをキューから取得して処理開始状態にする

        Args:
            job_type: 特定のジョブタイプのみ取得（None の場合は全種類）

        Returns:
            ジョブデータまたはNone
        """
        if not self._db:
            raise RuntimeError("JobQueue not initialized")

        try:
            # 未処理ジョブを取得
            query = """
                SELECT id, job_type, payload, created_at, retry_count
                FROM jobs 
                WHERE status = ?
            """
            params = [JobStatus.PENDING.value]

            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)

            query += " ORDER BY created_at ASC LIMIT 1"

            cursor = await self._db.execute(query, params)
            row = await cursor.fetchone()

            if not row:
                return None

            job_id = row["id"]

            # ジョブを処理中状態に更新
            await self._db.execute(
                """
                UPDATE jobs SET status = ?, started_at = ?
                WHERE id = ?
                """,
                (JobStatus.PROCESSING.value, datetime.now().isoformat(), job_id),
            )
            await self._db.commit()

            return {
                "id": job_id,
                "job_type": row["job_type"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
                "retry_count": row["retry_count"],
            }

        except Exception as e:
            logger.error(f"ジョブ取得エラー: {e}")
            raise

    async def complete_job(
        self, job_id: int, result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        ジョブを完了状態にする

        Args:
            job_id: ジョブID
            result: 結果データ（オプション）
        """
        if not self._db:
            raise RuntimeError("JobQueue not initialized")

        try:
            update_data = {
                "status": JobStatus.COMPLETED.value,
                "completed_at": datetime.now().isoformat(),
            }

            if result:
                update_data["payload"] = json.dumps(result)

            await self._db.execute(
                """
                UPDATE jobs SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (update_data["status"], update_data["completed_at"], job_id),
            )
            await self._db.commit()
            logger.info(f"ジョブ完了: ID {job_id}")

        except Exception as e:
            logger.error(f"ジョブ完了エラー: {e}")
            raise

    async def fail_job(self, job_id: int, error_message: str) -> None:
        """
        ジョブを失敗状態にする

        Args:
            job_id: ジョブID
            error_message: エラーメッセージ
        """
        if not self._db:
            raise RuntimeError("JobQueue not initialized")

        try:
            await self._db.execute(
                """
                UPDATE jobs SET status = ?, completed_at = ?, error_message = ?
                WHERE id = ?
                """,
                (
                    JobStatus.FAILED.value,
                    datetime.now().isoformat(),
                    error_message,
                    job_id,
                ),
            )
            await self._db.commit()
            logger.warning(f"ジョブ失敗: ID {job_id} - {error_message}")

        except Exception as e:
            logger.error(f"ジョブ失敗マークエラー: {e}")
            raise

    async def cleanup(self, older_than_hours: int = 24) -> int:
        """
        古い完了済みジョブを削除

        Args:
            older_than_hours: この時間より古いジョブを削除

        Returns:
            削除されたジョブ数
        """
        if not self._db:
            raise RuntimeError("JobQueue not initialized")

        try:
            from datetime import timedelta

            cutoff = datetime.now() - timedelta(hours=older_than_hours)

            cursor = await self._db.execute(
                """
                DELETE FROM jobs 
                WHERE status IN (?, ?) AND completed_at < ?
                """,
                (JobStatus.COMPLETED.value, JobStatus.FAILED.value, cutoff.isoformat()),
            )
            await self._db.commit()
            deleted = cursor.rowcount

            if deleted > 0:
                logger.info(f"古いジョブ {deleted} 件を削除しました")

            return deleted

        except Exception as e:
            logger.error(f"ジョブクリーンアップエラー: {e}")
            raise


class JobWorker:
    """ジョブワーカー"""

    def __init__(self, job_queue: JobQueue, poll_interval: float = 1.0):
        """
        ワーカーの初期化

        Args:
            job_queue: ジョブキューインスタンス
            poll_interval: ポーリング間隔（秒）
        """
        self.job_queue = job_queue
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._handlers = {}

    def register_handler(self, job_type: str, handler):
        """
        ジョブハンドラーを登録

        Args:
            job_type: ジョブタイプ
            handler: ハンドラー関数
        """
        self._handlers[job_type] = handler
        logger.info(f"ジョブハンドラー登録: {job_type}")

    async def start(self) -> None:
        """ワーカー開始"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._work_loop())
        logger.info("ジョブワーカー開始")

    async def stop(self) -> None:
        """ワーカー停止"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("ジョブワーカー停止")

    async def _work_loop(self) -> None:
        """ワーカーループ"""
        while self._running:
            try:
                # ジョブを取得
                job = await self.job_queue.dequeue()

                if job:
                    await self._process_job(job)
                else:
                    # ジョブがない場合は少し待機
                    await asyncio.sleep(self.poll_interval)

                # 定期的にクリーンアップ
                if asyncio.get_event_loop().time() % 3600 < self.poll_interval:
                    await self.job_queue.cleanup(older_than_hours=24)

            except Exception as e:
                logger.error(f"ワーカーループエラー: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _process_job(self, job: Dict[str, Any]) -> None:
        """ジョブを処理"""
        job_id = job["id"]
        job_type = job["job_type"]
        payload = job["payload"]

        try:
            handler = self._handlers.get(job_type)
            if not handler:
                await self.job_queue.fail_job(
                    job_id, f"ハンドラーが見つかりません: {job_type}"
                )
                return

            logger.info(f"ジョブ処理開始: {job_type} (ID: {job_id})")

            # ハンドラー実行
            result = await handler(payload)

            # 完了
            await self.job_queue.complete_job(job_id, result)
            logger.info(f"ジョブ処理完了: {job_type} (ID: {job_id})")

        except Exception as e:
            error_msg = f"ジョブ処理エラー: {str(e)}"
            logger.error(f"{error_msg} (ID: {job_id})")
            await self.job_queue.fail_job(job_id, error_msg)
