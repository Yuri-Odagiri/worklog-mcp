"""データベース層の実装"""

import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import User, WorklogEntry


class Database:
    """SQLiteデータベース管理クラス"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # データベースディレクトリを作成
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """データベースの初期化"""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()

    async def _create_tables(self, db: aiosqlite.Connection) -> None:
        """テーブル作成"""
        # ユーザーテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY CHECK(user_id GLOB '[a-zA-Z0-9-_]*'),
                name TEXT NOT NULL,
                theme_color TEXT DEFAULT 'Blue' CHECK(theme_color IN ('Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Orange', 'Pink', 'Cyan')),
                role TEXT DEFAULT 'メンバー',
                personality TEXT DEFAULT '明るく協力的で、チームワークを重視する性格です。',
                appearance TEXT DEFAULT '親しみやすい外見で、いつも笑顔を絶やしません。',
                avatar_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 分報エントリーテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                markdown_content TEXT NOT NULL,
                related_entry_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (related_entry_id) REFERENCES entries(id)
            )
        """)

        # 作業サマリーテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS work_summaries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                period_start DATETIME NOT NULL,
                period_end DATETIME NOT NULL,
                entry_count INTEGER,
                summary_json TEXT,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # インデックス作成
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_user_id ON entries(user_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_related ON entries(related_entry_id)"
        )

    async def is_first_run(self) -> bool:
        """初回起動かどうか確認"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            count = await cursor.fetchone()
            return count[0] == 0

    # ユーザー管理
    async def create_user(self, user: User) -> None:
        """ユーザー作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO users (user_id, name, theme_color, role, personality, appearance, avatar_path, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user.user_id,
                    user.name,
                    user.theme_color,
                    user.role,
                    user.personality,
                    user.appearance,
                    user.avatar_path,
                    user.created_at,
                    user.last_active,
                ),
            )
            await db.commit()

    async def get_user(self, user_id: str) -> Optional[User]:
        """ユーザー取得"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, name, theme_color, role, personality, appearance, avatar_path, created_at, last_active FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row:
                return User(
                    user_id=row[0],
                    name=row[1],
                    theme_color=row[2],
                    role=row[3],
                    personality=row[4],
                    appearance=row[5],
                    avatar_path=row[6],
                    created_at=datetime.fromisoformat(row[7])
                    if isinstance(row[7], str)
                    else row[7],
                    last_active=datetime.fromisoformat(row[8])
                    if isinstance(row[8], str)
                    else row[8],
                )
            return None

    async def get_all_users(self) -> List[User]:
        """全ユーザー取得"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, name, theme_color, role, personality, appearance, avatar_path, created_at, last_active FROM users ORDER BY last_active DESC"
            )
            rows = await cursor.fetchall()
            return [
                User(
                    user_id=row[0],
                    name=row[1],
                    theme_color=row[2],
                    role=row[3],
                    personality=row[4],
                    appearance=row[5],
                    avatar_path=row[6],
                    created_at=datetime.fromisoformat(row[7])
                    if isinstance(row[7], str)
                    else row[7],
                    last_active=datetime.fromisoformat(row[8])
                    if isinstance(row[8], str)
                    else row[8],
                )
                for row in rows
            ]

    async def update_user_last_active(self, user_id: str) -> None:
        """ユーザーの最終活動時刻を更新"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (datetime.now(), user_id),
            )
            await db.commit()

    async def update_user_avatar_path(self, user_id: str, avatar_path: str) -> bool:
        """ユーザーのアバターパスを更新する"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET avatar_path = ? WHERE user_id = ?",
                (avatar_path, user_id),
            )
            await db.commit()
            return db.total_changes > 0

    # エントリー管理
    async def create_entry(self, entry: WorklogEntry) -> None:
        """エントリー作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO entries (id, user_id, markdown_content, related_entry_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry.id,
                    entry.user_id,
                    entry.markdown_content,
                    entry.related_entry_id,
                    entry.created_at,
                    entry.updated_at,
                ),
            )
            await db.commit()

        # ユーザーの最終活動時刻を更新
        await self.update_user_last_active(entry.user_id)

    async def get_entry(self, entry_id: str) -> Optional[WorklogEntry]:
        """エントリー取得"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, user_id, markdown_content, related_entry_id, created_at, updated_at FROM entries WHERE id = ?",
                (entry_id,),
            )
            row = await cursor.fetchone()
            if row:
                return WorklogEntry(
                    id=row[0],
                    user_id=row[1],
                    markdown_content=row[2],
                    related_entry_id=row[3],
                    created_at=datetime.fromisoformat(row[4])
                    if isinstance(row[4], str)
                    else row[4],
                    updated_at=datetime.fromisoformat(row[5])
                    if isinstance(row[5], str)
                    else row[5],
                )
            return None

    async def update_entry(self, entry_id: str, markdown_content: str) -> bool:
        """エントリー更新"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE entries SET markdown_content = ?, updated_at = ? WHERE id = ?",
                (markdown_content, datetime.now(), entry_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_timeline(
        self,
        user_id: Optional[str] = None,
        hours: Optional[int] = None,
        count: Optional[int] = None,
    ) -> List[WorklogEntry]:
        """タイムライン取得"""
        query = "SELECT id, user_id, markdown_content, related_entry_id, created_at, updated_at FROM entries"
        params = []
        conditions = []

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            conditions.append("created_at >= ?")
            params.append(cutoff_time)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        if count:
            query += " LIMIT ?"
            params.append(count)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [
                WorklogEntry(
                    id=row[0],
                    user_id=row[1],
                    markdown_content=row[2],
                    related_entry_id=row[3],
                    created_at=datetime.fromisoformat(row[4])
                    if isinstance(row[4], str)
                    else row[4],
                    updated_at=datetime.fromisoformat(row[5])
                    if isinstance(row[5], str)
                    else row[5],
                )
                for row in rows
            ]

    async def search_entries(
        self,
        keyword: str,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[WorklogEntry]:
        """エントリー検索"""
        query = "SELECT id, user_id, markdown_content, related_entry_id, created_at, updated_at FROM entries WHERE markdown_content LIKE ?"
        params = [f"%{keyword}%"]

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)

        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to)

        query += " ORDER BY created_at DESC"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [
                WorklogEntry(
                    id=row[0],
                    user_id=row[1],
                    markdown_content=row[2],
                    related_entry_id=row[3],
                    created_at=datetime.fromisoformat(row[4])
                    if isinstance(row[4], str)
                    else row[4],
                    updated_at=datetime.fromisoformat(row[5])
                    if isinstance(row[5], str)
                    else row[5],
                )
                for row in rows
            ]

    async def get_thread(self, entry_id: str) -> List[WorklogEntry]:
        """スレッド取得（関連エントリー含む）"""
        entries = []

        # 元エントリーを取得
        main_entry = await self.get_entry(entry_id)
        if main_entry:
            entries.append(main_entry)

        # 関連エントリーを取得
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, user_id, markdown_content, related_entry_id, created_at, updated_at FROM entries WHERE related_entry_id = ? ORDER BY created_at ASC",
                (entry_id,),
            )
            rows = await cursor.fetchall()
            for row in rows:
                entries.append(
                    WorklogEntry(
                        id=row[0],
                        user_id=row[1],
                        markdown_content=row[2],
                        related_entry_id=row[3],
                        created_at=datetime.fromisoformat(row[4])
                        if isinstance(row[4], str)
                        else row[4],
                        updated_at=datetime.fromisoformat(row[5])
                        if isinstance(row[5], str)
                        else row[5],
                    )
                )

        return entries

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """ユーザー統計情報取得"""
        async with aiosqlite.connect(self.db_path) as db:
            # 総投稿数
            cursor = await db.execute(
                "SELECT COUNT(*) FROM entries WHERE user_id = ?", (user_id,)
            )
            total_posts = (await cursor.fetchone())[0]

            # 今日の投稿数
            today = datetime.now().date()
            cursor = await db.execute(
                "SELECT COUNT(*) FROM entries WHERE user_id = ? AND DATE(created_at) = ?",
                (user_id, today),
            )
            today_posts = (await cursor.fetchone())[0]

            # 最初の投稿日
            cursor = await db.execute(
                "SELECT MIN(created_at) FROM entries WHERE user_id = ?", (user_id,)
            )
            first_post_result = await cursor.fetchone()
            first_post = first_post_result[0] if first_post_result[0] else None

            # 最新の投稿日
            cursor = await db.execute(
                "SELECT MAX(created_at) FROM entries WHERE user_id = ?", (user_id,)
            )
            latest_post_result = await cursor.fetchone()
            latest_post = latest_post_result[0] if latest_post_result[0] else None

            return {
                "total_posts": total_posts,
                "today_posts": today_posts,
                "first_post": first_post,
                "latest_post": latest_post,
            }
