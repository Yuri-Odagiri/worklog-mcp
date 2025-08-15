"""データベース層のテスト"""

import pytest
import pytest_asyncio
import tempfile
import os
from datetime import datetime, timedelta

from worklog_mcp.database import Database
from worklog_mcp.models import User, WorklogEntry


@pytest_asyncio.fixture
async def db():
    """テスト用データベース"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    database = Database(db_path)
    await database.initialize()
    
    yield database
    
    # クリーンアップ
    os.unlink(db_path)


@pytest.mark.asyncio
async def test_database_initialization(db):
    """データベース初期化のテスト"""
    # 初回起動のテスト
    assert await db.is_first_run() == True


@pytest.mark.asyncio
async def test_user_creation(db):
    """ユーザー作成のテスト"""
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    
    # ユーザー作成
    await db.create_user(user)
    
    # ユーザー取得
    retrieved_user = await db.get_user("test-user")
    assert retrieved_user is not None
    assert retrieved_user.user_id == "test-user"
    assert retrieved_user.name == "テストユーザー"
    
    # 初回起動フラグの変更確認
    assert await db.is_first_run() == False


@pytest.mark.asyncio
async def test_user_validation():
    """ユーザーバリデーションのテスト"""
    # 無効なuser_id
    with pytest.raises(ValueError):
        User(user_id="invalid@user", name="Invalid User", role="テスター")


@pytest.mark.asyncio
async def test_entry_creation(db):
    """エントリー作成のテスト"""
    # ユーザー作成
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    await db.create_user(user)
    
    # エントリー作成
    entry = WorklogEntry(
        user_id="test-user",
        markdown_content="## 作業\n- テスト実装中"
    )
    await db.create_entry(entry)
    
    # エントリー取得
    retrieved_entry = await db.get_entry(entry.id)
    assert retrieved_entry is not None
    assert retrieved_entry.user_id == "test-user"
    assert retrieved_entry.markdown_content == "## 作業\n- テスト実装中"


@pytest.mark.asyncio
async def test_timeline_retrieval(db):
    """タイムライン取得のテスト"""
    # ユーザー作成
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    await db.create_user(user)
    
    # 複数エントリー作成
    for i in range(3):
        entry = WorklogEntry(
            user_id="test-user",
            markdown_content=f"テストエントリー {i}"
        )
        await db.create_entry(entry)
    
    # タイムライン取得
    timeline = await db.get_timeline()
    assert len(timeline) == 3
    
    # ユーザー指定のタイムライン取得
    user_timeline = await db.get_timeline(user_id="test-user")
    assert len(user_timeline) == 3
    
    # 件数指定のタイムライン取得
    limited_timeline = await db.get_timeline(count=2)
    assert len(limited_timeline) == 2


@pytest.mark.asyncio
async def test_search_entries(db):
    """エントリー検索のテスト"""
    # ユーザー作成
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    await db.create_user(user)
    
    # 検索対象エントリー作成
    entries = [
        "## 作業\n- バグ修正",
        "## 完了\n- 機能実装",
        "## 問題\n- バグが見つかった"
    ]
    
    for content in entries:
        entry = WorklogEntry(user_id="test-user", markdown_content=content)
        await db.create_entry(entry)
    
    # 検索テスト
    bug_results = await db.search_entries("バグ")
    assert len(bug_results) == 2
    
    completed_results = await db.search_entries("完了")
    assert len(completed_results) == 1


@pytest.mark.asyncio
async def test_entry_update(db):
    """エントリー更新のテスト"""
    # ユーザー作成
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    await db.create_user(user)
    
    # エントリー作成
    entry = WorklogEntry(
        user_id="test-user",
        markdown_content="元の内容"
    )
    await db.create_entry(entry)
    
    # エントリー更新
    success = await db.update_entry(entry.id, "更新された内容")
    assert success == True
    
    # 更新確認
    updated_entry = await db.get_entry(entry.id)
    assert updated_entry.markdown_content == "更新された内容"


# test_thread_functionalityは削除されました（related_entry_id機能と一緒に）


@pytest.mark.asyncio
async def test_user_stats(db):
    """ユーザー統計のテスト"""
    # ユーザー作成
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    await db.create_user(user)
    
    # エントリー作成
    for i in range(5):
        entry = WorklogEntry(
            user_id="test-user",
            markdown_content=f"エントリー {i}"
        )
        await db.create_entry(entry)
    
    # 統計情報取得
    stats = await db.get_user_stats("test-user")
    
    assert stats["total_posts"] == 5
    assert stats["today_posts"] == 5
    assert stats["first_post"] is not None
    assert stats["latest_post"] is not None


@pytest.mark.asyncio
async def test_multiuser_functionality(db):
    """マルチユーザー機能のテスト"""
    # 複数ユーザー作成
    user1 = User(user_id="user1", name="ユーザー1", role="開発者")
    user2 = User(user_id="user2", name="ユーザー2", role="デザイナー")
    
    await db.create_user(user1)
    await db.create_user(user2)
    
    # 各ユーザーのエントリー作成
    entry1 = WorklogEntry(user_id="user1", markdown_content="ユーザー1のエントリー")
    entry2 = WorklogEntry(user_id="user2", markdown_content="ユーザー2のエントリー")
    
    await db.create_entry(entry1)
    await db.create_entry(entry2)
    
    # 全ユーザー取得
    users = await db.get_all_users()
    assert len(users) == 2
    
    # ユーザー別タイムライン
    user1_timeline = await db.get_timeline(user_id="user1")
    user2_timeline = await db.get_timeline(user_id="user2")
    
    assert len(user1_timeline) == 1
    assert len(user2_timeline) == 1
    assert user1_timeline[0].user_id == "user1"
    assert user2_timeline[0].user_id == "user2"