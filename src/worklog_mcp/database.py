"""データベース層の実装"""

import aiosqlite
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import User, WorklogEntry
from .logging_config import setup_logging

# ログ設定を確実に初期化
setup_logging()

logger = logging.getLogger(__name__)


class Database:
    """SQLiteデータベース管理クラス"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # データベースディレクトリを作成
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self, project_context=None) -> None:
        """データベースの初期化"""
        # 初回起動かどうかを事前に確認
        is_first = await self.is_first_run()

        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()

        # 初回起動時のみサンプルエージェントをインポート
        if is_first:
            logger.info(
                "初回起動が検出されました。サンプルエージェントをインポートします..."
            )
            await self.import_example_agents(project_context)

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
                description TEXT DEFAULT '',
                model TEXT DEFAULT '',
                mcp TEXT DEFAULT '',
                tools TEXT DEFAULT '',
                instruction TEXT DEFAULT '',
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
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
        # idx_entries_relatedインデックスは削除されました（related_entry_idカラムと一緒に）

    async def is_first_run(self) -> bool:
        """初回起動かどうか確認"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM users")
                count = await cursor.fetchone()
                return count[0] == 0
            except Exception:
                # テーブルが存在しない場合は初回起動と判定
                return True

    # ユーザー管理
    async def create_user(self, user: User) -> None:
        """ユーザー作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO users (user_id, name, theme_color, role, personality, appearance, description, model, mcp, tools, instruction, avatar_path, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user.user_id,
                    user.name,
                    user.theme_color,
                    user.role,
                    user.personality,
                    user.appearance,
                    user.description,
                    user.model,
                    user.mcp,
                    user.tools,
                    user.instruction,
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
                "SELECT user_id, name, theme_color, role, personality, appearance, description, model, mcp, tools, instruction, avatar_path, created_at, last_active FROM users WHERE user_id = ?",
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
                    description=row[6],
                    model=row[7],
                    mcp=row[8],
                    tools=row[9],
                    instruction=row[10],
                    avatar_path=row[11],
                    created_at=datetime.fromisoformat(row[12])
                    if isinstance(row[12], str)
                    else row[12],
                    last_active=datetime.fromisoformat(row[13])
                    if isinstance(row[13], str)
                    else row[13],
                )
            return None

    async def get_all_users(self) -> List[User]:
        """全ユーザー取得"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, name, theme_color, role, personality, appearance, description, model, mcp, tools, instruction, avatar_path, created_at, last_active FROM users ORDER BY last_active DESC"
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
                    description=row[6],
                    model=row[7],
                    mcp=row[8],
                    tools=row[9],
                    instruction=row[10],
                    avatar_path=row[11],
                    created_at=datetime.fromisoformat(row[12])
                    if isinstance(row[12], str)
                    else row[12],
                    last_active=datetime.fromisoformat(row[13])
                    if isinstance(row[13], str)
                    else row[13],
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

    async def update_user_info(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """ユーザー情報を更新する"""
        if not update_data:
            return False

        # 更新可能なフィールドのみを処理
        allowed_fields = {"personality", "appearance", "role", "instruction"}
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not filtered_data:
            return False

        # SQL文を動的に構築
        set_clauses = []
        values = []
        for field, value in filtered_data.items():
            set_clauses.append(f"{field} = ?")
            values.append(value)

        values.append(user_id)
        sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?"

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, values)
            await db.commit()
            return db.total_changes > 0

    async def delete_user(self, user_id: str) -> bool:
        """ユーザーを削除する（関連する分報エントリーも削除）"""
        async with aiosqlite.connect(self.db_path) as db:
            # まず関連する分報エントリーを削除
            await db.execute("DELETE FROM entries WHERE user_id = ?", (user_id,))

            # ユーザーを削除
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

            await db.commit()
            return db.total_changes > 0

    # エントリー管理
    async def create_entry(self, entry: WorklogEntry) -> None:
        """エントリー作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO entries (id, user_id, markdown_content, created_at) VALUES (?, ?, ?, ?)",
                (
                    entry.id,
                    entry.user_id,
                    entry.markdown_content,
                    entry.created_at,
                ),
            )
            await db.commit()

        # ユーザーの最終活動時刻を更新
        await self.update_user_last_active(entry.user_id)

    async def get_entry(self, entry_id: str) -> Optional[WorklogEntry]:
        """エントリー取得"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, user_id, markdown_content, created_at FROM entries WHERE id = ?",
                (entry_id,),
            )
            row = await cursor.fetchone()
            if row:
                return WorklogEntry(
                    id=row[0],
                    user_id=row[1],
                    markdown_content=row[2],
                    created_at=datetime.fromisoformat(row[3])
                    if isinstance(row[3], str)
                    else row[3],
                )
            return None

    async def update_entry(self, entry_id: str, markdown_content: str) -> bool:
        """エントリー更新"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE entries SET markdown_content = ? WHERE id = ?",
                (markdown_content, entry_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_entry(self, entry_id: str) -> bool:
        """エントリー削除"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM entries WHERE id = ?",
                (entry_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def truncate_entries(self, user_id: Optional[str] = None) -> int:
        """エントリー全削除（オプションで特定ユーザーのみ）"""
        async with aiosqlite.connect(self.db_path) as db:
            if user_id:
                cursor = await db.execute(
                    "DELETE FROM entries WHERE user_id = ?",
                    (user_id,),
                )
            else:
                cursor = await db.execute("DELETE FROM entries")
            await db.commit()
            return cursor.rowcount

    async def truncate_all(
        self, include_users: bool = False, avatar_dir: Optional[str] = None
    ) -> dict:
        """全データ削除（オプションでユーザーテーブルも含む）"""
        async with aiosqlite.connect(self.db_path) as db:
            entries_count = 0
            users_count = 0
            avatars_deleted = 0

            # エントリーテーブルの削除
            cursor = await db.execute("DELETE FROM entries")
            entries_count = cursor.rowcount

            # ユーザーテーブルの削除（オプション）
            if include_users:
                # avatarファイルを削除前に取得
                if avatar_dir and os.path.exists(avatar_dir):
                    cursor = await db.execute(
                        "SELECT avatar_path FROM users WHERE avatar_path IS NOT NULL"
                    )
                    avatar_paths = await cursor.fetchall()

                    for (avatar_path,) in avatar_paths:
                        if avatar_path and os.path.exists(avatar_path):
                            try:
                                os.remove(avatar_path)
                                avatars_deleted += 1
                            except OSError as e:
                                logger.warning(
                                    f"アバターファイル削除に失敗（続行）: {avatar_path} - {e}"
                                )

                    # avatarディレクトリが空になった場合は削除
                    try:
                        if not os.listdir(avatar_dir):
                            os.rmdir(avatar_dir)
                    except OSError as e:
                        logger.warning(
                            f"アバターディレクトリ削除に失敗（続行）: {avatar_dir} - {e}"
                        )

                cursor = await db.execute("DELETE FROM users")
                users_count = cursor.rowcount

            await db.commit()
            return {
                "entries_deleted": entries_count,
                "users_deleted": users_count if include_users else 0,
                "avatars_deleted": avatars_deleted if include_users else 0,
                "users_truncated": include_users,
            }

    async def full_project_reset(self, project_context) -> dict:
        """プロジェクト全体の完全リセット（DB、EventBus、JobQueue、ディレクトリ全削除）

        Args:
            project_context: ProjectContextインスタンス

        Returns:
            dict: 削除結果の詳細
        """
        # まずデータベースを閉じる
        await self.close()

        # プロジェクトディレクトリを削除
        deleted = project_context.delete_project_directory()

        if deleted:
            return {
                "entries_deleted": 0,  # ディレクトリごと削除なので正確な数は不明
                "users_deleted": 0,
                "avatars_deleted": 0,
                "eventbus_deleted": True,
                "jobqueue_deleted": True,
                "project_directory_deleted": True,
                "users_truncated": True,
            }
        else:
            return {
                "entries_deleted": 0,
                "users_deleted": 0,
                "avatars_deleted": 0,
                "eventbus_deleted": False,
                "jobqueue_deleted": False,
                "project_directory_deleted": False,
                "users_truncated": False,
            }

    async def get_timeline(
        self,
        user_id: Optional[str] = None,
        hours: Optional[int] = None,
        count: Optional[int] = None,
    ) -> List[WorklogEntry]:
        """タイムライン取得"""
        query = "SELECT id, user_id, markdown_content, created_at FROM entries"
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
                    created_at=datetime.fromisoformat(row[3])
                    if isinstance(row[3], str)
                    else row[3],
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
        query = "SELECT id, user_id, markdown_content, created_at FROM entries WHERE markdown_content LIKE ?"
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
                    created_at=datetime.fromisoformat(row[3])
                    if isinstance(row[3], str)
                    else row[3],
                )
                for row in rows
            ]

    # get_thread機能は削除されました（related_entry_id機能と一緒に）

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

    async def close(self) -> None:
        """データベース接続をクローズする（現在はコンテキストマネージャーを使用しているため、実際の処理は不要）"""
        # aiosqliteはコンテキストマネージャーで自動的に接続が閉じられるため、
        # 特別な処理は不要
        pass

    async def import_example_agents(self, project_context=None) -> None:
        """example-agentディレクトリからサンプルエージェントをインポート"""
        try:
            import json
            import shutil
            from pathlib import Path
            from .models import User

            # example-agentディレクトリのパスを取得
            current_dir = Path(__file__).parent.parent.parent
            example_agent_dir = current_dir / "example-agent"
            example_avatar_dir = example_agent_dir / "avatars"

            if not example_agent_dir.exists():
                logger.warning(
                    f"example-agentディレクトリが見つかりません: {example_agent_dir}"
                )
                return

            # JSONファイルを検索
            json_files = list(example_agent_dir.glob("*.json"))
            if not json_files:
                logger.warning(
                    f"example-agentディレクトリにJSONファイルが見つかりません: {example_agent_dir}"
                )
                return

            # プロジェクトのアバターディレクトリを取得
            target_avatar_dir = None
            if project_context:
                target_avatar_dir = Path(project_context.get_avatar_path())
                target_avatar_dir.mkdir(parents=True, exist_ok=True)

            imported_count = 0
            skipped_count = 0
            avatar_copied_count = 0

            async with aiosqlite.connect(self.db_path) as db:
                for json_file in json_files:
                    try:
                        # JSONファイルを読み込み
                        with open(json_file, "r", encoding="utf-8") as f:
                            agent_data = json.load(f)

                        # 必須フィールドの確認
                        required_fields = ["user_id", "name", "role"]
                        if not all(field in agent_data for field in required_fields):
                            logger.warning(
                                f"必須フィールドが不足しています: {json_file.name}"
                            )
                            skipped_count += 1
                            continue

                        # 既存ユーザーの確認
                        cursor = await db.execute(
                            "SELECT COUNT(*) FROM users WHERE user_id = ?",
                            (agent_data["user_id"],),
                        )
                        exists = (await cursor.fetchone())[0] > 0
                        if exists:
                            logger.info(
                                f"ユーザーは既に存在します: {agent_data['user_id']}"
                            )
                            skipped_count += 1
                            continue

                        # アバターファイルの処理
                        avatar_path = None
                        if target_avatar_dir and example_avatar_dir.exists():
                            # アバターファイル名のパターンを確認
                            user_id = agent_data["user_id"]
                            possible_avatar_names = [
                                f"{user_id}_ai.png",
                                f"{user_id}.png",
                                f"{user_id}_avatar.png",
                            ]

                            for avatar_name in possible_avatar_names:
                                source_avatar = example_avatar_dir / avatar_name
                                if source_avatar.exists():
                                    target_avatar = target_avatar_dir / avatar_name
                                    try:
                                        shutil.copy2(source_avatar, target_avatar)
                                        avatar_path = str(target_avatar)
                                        avatar_copied_count += 1
                                        logger.debug(
                                            f"アバターファイルをコピー: {source_avatar} -> {target_avatar}"
                                        )
                                        break
                                    except Exception as e:
                                        logger.warning(
                                            f"アバターファイルのコピーに失敗: {source_avatar} -> {e}"
                                        )

                        # Userモデルに変換
                        user = User(
                            user_id=agent_data["user_id"],
                            name=agent_data["name"],
                            role=agent_data["role"],
                            theme_color=agent_data.get("theme_color", "Blue"),
                            personality=agent_data.get(
                                "personality",
                                "明るく協力的で、チームワークを重視する性格です。",
                            ),
                            appearance=agent_data.get(
                                "appearance",
                                "親しみやすい外見で、いつも笑顔を絶やしません。",
                            ),
                            description=agent_data.get("description", ""),
                            model=agent_data.get("model", ""),
                            mcp=agent_data.get("mcp", ""),
                            tools=agent_data.get("tools", ""),
                            instruction=agent_data.get("instruction", ""),
                            avatar_path=avatar_path,  # コピーしたアバターのパスを設定
                        )

                        # データベースに挿入
                        await db.execute(
                            """
                            INSERT INTO users (
                                user_id, name, theme_color, role, personality, appearance,
                                description, model, mcp, tools, instruction, avatar_path,
                                created_at, last_active
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                user.user_id,
                                user.name,
                                user.theme_color,
                                user.role,
                                user.personality,
                                user.appearance,
                                user.description,
                                user.model,
                                user.mcp,
                                user.tools,
                                user.instruction,
                                user.avatar_path,
                                user.created_at,
                                user.last_active,
                            ),
                        )

                        imported_count += 1
                        avatar_status = (
                            f" (アバター: {avatar_path})" if avatar_path else ""
                        )
                        logger.info(
                            f"エージェントをインポートしました: {user.user_id} ({user.name}){avatar_status}"
                        )

                    except json.JSONDecodeError:
                        logger.error(f"JSONパースエラー: {json_file.name}")
                        skipped_count += 1
                    except ValueError as e:
                        logger.error(f"バリデーションエラー ({json_file.name}): {e}")
                        skipped_count += 1
                    except Exception as e:
                        logger.error(
                            f"エージェントインポートエラー ({json_file.name}): {e}"
                        )
                        skipped_count += 1

                await db.commit()

            logger.info(
                f"エージェントインポート完了: {imported_count}件成功, {skipped_count}件スキップ, アバター{avatar_copied_count}件コピー"
            )

        except Exception as e:
            logger.error(f"エージェントインポート処理でエラーが発生しました: {e}")

    async def update_missing_avatar_paths(self, project_context=None) -> dict:
        """既存ユーザーで欠けているアバターパスを更新する"""
        try:
            import shutil
            from pathlib import Path

            # example-agentディレクトリのパスを取得
            current_dir = Path(__file__).parent.parent.parent
            example_agent_dir = current_dir / "example-agent"
            example_avatar_dir = example_agent_dir / "avatars"

            if not example_avatar_dir.exists():
                logger.warning(
                    f"example-agentのavatarsディレクトリが見つかりません: {example_avatar_dir}"
                )
                return {
                    "updated_count": 0,
                    "avatar_copied_count": 0,
                    "error": "avatarsディレクトリが見つかりません",
                }

            # プロジェクトのアバターディレクトリを取得
            target_avatar_dir = None
            if project_context:
                target_avatar_dir = Path(project_context.get_avatar_path())
                target_avatar_dir.mkdir(parents=True, exist_ok=True)
            else:
                logger.warning("project_contextが提供されていません")
                return {
                    "updated_count": 0,
                    "avatar_copied_count": 0,
                    "error": "project_contextが提供されていません",
                }

            updated_count = 0
            avatar_copied_count = 0

            async with aiosqlite.connect(self.db_path) as db:
                # avatar_pathが空またはNullのユーザーを取得
                cursor = await db.execute(
                    "SELECT user_id, name FROM users WHERE avatar_path IS NULL OR avatar_path = ''"
                )
                users_without_avatar = await cursor.fetchall()

                for user_id, name in users_without_avatar:
                    # アバターファイル名のパターンを確認
                    possible_avatar_names = [
                        f"{user_id}_ai.png",
                        f"{user_id}.png",
                        f"{user_id}_avatar.png",
                    ]

                    avatar_path = None
                    for avatar_name in possible_avatar_names:
                        source_avatar = example_avatar_dir / avatar_name
                        if source_avatar.exists():
                            target_avatar = target_avatar_dir / avatar_name
                            try:
                                shutil.copy2(source_avatar, target_avatar)
                                avatar_path = str(target_avatar)
                                avatar_copied_count += 1
                                logger.info(
                                    f"アバターファイルをコピー: {source_avatar} -> {target_avatar}"
                                )
                                break
                            except Exception as e:
                                logger.warning(
                                    f"アバターファイルのコピーに失敗: {source_avatar} -> {e}"
                                )

                    # アバターパスを更新
                    if avatar_path:
                        await db.execute(
                            "UPDATE users SET avatar_path = ? WHERE user_id = ?",
                            (avatar_path, user_id),
                        )
                        updated_count += 1
                        logger.info(
                            f"ユーザー {user_id} ({name}) のアバターパスを更新: {avatar_path}"
                        )

                await db.commit()

            result = {
                "updated_count": updated_count,
                "avatar_copied_count": avatar_copied_count,
                "error": None,
            }

            logger.info(
                f"アバターパス更新完了: {updated_count}人のユーザー, {avatar_copied_count}個のアバターをコピー"
            )

            return result

        except Exception as e:
            logger.error(f"アバターパス更新処理でエラーが発生しました: {e}")
            return {"updated_count": 0, "avatar_copied_count": 0, "error": str(e)}
