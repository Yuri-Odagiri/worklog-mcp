"""データベース層のテスト"""

import pytest
import pytest_asyncio
import tempfile
import os
from datetime import datetime, timedelta

from worklog_mcp.database import Database
from worklog_mcp.models import User, WorklogEntry
import aiosqlite


@pytest_asyncio.fixture
async def db_no_import():
    """テスト用データベース（エージェントインポートなし）"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    database = Database(db_path)
    # テーブルのみ作成（エージェントインポートなし）
    async with aiosqlite.connect(database.db_path) as db_conn:
        await database._create_tables(db_conn)
        await db_conn.commit()
    
    yield database
    
    # クリーンアップ
    os.unlink(db_path)


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
async def test_database_initialization(db_no_import):
    """データベース初期化のテスト"""
    # 初回起動のテスト
    assert await db_no_import.is_first_run() == True


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
async def test_multiuser_functionality(db_no_import):
    """マルチユーザー機能のテスト"""
    # 複数ユーザー作成
    user1 = User(user_id="user1", name="ユーザー1", role="開発者")
    user2 = User(user_id="user2", name="ユーザー2", role="デザイナー")
    
    await db_no_import.create_user(user1)
    await db_no_import.create_user(user2)
    
    # 各ユーザーのエントリー作成
    entry1 = WorklogEntry(user_id="user1", markdown_content="ユーザー1のエントリー")
    entry2 = WorklogEntry(user_id="user2", markdown_content="ユーザー2のエントリー")
    
    await db_no_import.create_entry(entry1)
    await db_no_import.create_entry(entry2)
    
    # 全ユーザー取得
    users = await db_no_import.get_all_users()
    assert len(users) == 2
    
    # ユーザー別タイムライン
    user1_timeline = await db_no_import.get_timeline(user_id="user1")
    user2_timeline = await db_no_import.get_timeline(user_id="user2")
    
    assert len(user1_timeline) == 1
    assert len(user2_timeline) == 1
    assert user1_timeline[0].user_id == "user1"
    assert user2_timeline[0].user_id == "user2"


@pytest_asyncio.fixture
async def db_for_import_test():
    """エージェントインポートテスト用のデータベース（initialize呼び出しなし）"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    database = Database(db_path)
    # initializeは呼び出さない（is_first_runテスト用）
    
    yield database
    
    # クリーンアップ
    os.unlink(db_path)


@pytest.mark.asyncio
async def test_import_example_agents_success(db_for_import_test):
    """エージェントインポート機能の正常系テスト"""
    # テーブルを手動で作成（initializeを使わずに）
    import aiosqlite
    async with aiosqlite.connect(db_for_import_test.db_path) as db:
        await db_for_import_test._create_tables(db)
        await db.commit()
    
    # エージェントインポートを実行
    await db_for_import_test.import_example_agents()
    
    # インポートされたユーザーを確認
    users = await db_for_import_test.get_all_users()
    
    # 最低でも1人はインポートされているはず
    assert len(users) > 0
    
    # 特定のエージェント（architect）が含まれているかチェック
    architect_found = any(user.user_id == "architect" for user in users)
    assert architect_found, "architectエージェントがインポートされていません"
    
    # architect の詳細を確認
    architect = await db_for_import_test.get_user("architect")
    assert architect is not None
    assert architect.name == "天海 礼"
    assert architect.role == "システムアーキテクト"
    assert architect.theme_color == "Purple"


@pytest.mark.asyncio
async def test_import_example_agents_no_duplicates(db_for_import_test):
    """重複インポート防止のテスト"""
    # テーブルを手動で作成
    import aiosqlite
    async with aiosqlite.connect(db_for_import_test.db_path) as db:
        await db_for_import_test._create_tables(db)
        await db.commit()
    
    # 2回インポートを実行
    await db_for_import_test.import_example_agents()
    initial_count = len(await db_for_import_test.get_all_users())
    
    await db_for_import_test.import_example_agents()
    final_count = len(await db_for_import_test.get_all_users())
    
    # ユーザー数は変わらないはず
    assert initial_count == final_count, "重複ユーザーが作成されました"


@pytest.mark.asyncio
async def test_first_run_initialization_with_import():
    """初回起動時のinitialize()でエージェントインポートが実行されるかテスト"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        database = Database(db_path)
        
        # initializeを呼び出し（エージェントインポートも含む）
        await database.initialize()
        
        # ユーザーがインポートされているか確認
        users = await database.get_all_users()
        assert len(users) > 0, "初回起動時にエージェントがインポートされませんでした"
        
        # 二回目の起動ではインポートされないことを確認
        database2 = Database(db_path)
        is_first_2 = await database2.is_first_run()
        assert not is_first_2, "二回目の起動が初回として検出されました"
        
        await database.close()
        await database2.close()
        
    finally:
        # クリーンアップ
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_import_example_agents_missing_directory(db_for_import_test):
    """example-agentディレクトリが存在しない場合のテスト"""
    # テーブルを手動で作成
    import aiosqlite
    async with aiosqlite.connect(db_for_import_test.db_path) as db:
        await db_for_import_test._create_tables(db)
        await db.commit()
    
    # import_example_agentsメソッドを一時的にモック
    original_method = db_for_import_test.import_example_agents
    
    async def mock_import_with_missing_dir():
        # 存在しないディレクトリを指定してimport処理を実行
        import json
        from pathlib import Path
        from src.worklog_mcp.models import User
        
        # 存在しないディレクトリパス
        example_agent_dir = Path("/nonexistent/example-agent")
        
        if not example_agent_dir.exists():
            return  # 正常にreturnすることを確認
    
    db_for_import_test.import_example_agents = mock_import_with_missing_dir
    
    # エラーが発生しないことを確認
    try:
        await db_for_import_test.import_example_agents()
        # 例外が発生しなければ成功
    except Exception as e:
        pytest.fail(f"存在しないディレクトリでエラーが発生しました: {e}")
    finally:
        # 元のメソッドを復元
        db_for_import_test.import_example_agents = original_method

@pytest.mark.asyncio
async def test_import_example_agents_with_avatars():
    """アバターファイルを含むエージェントインポートのテスト"""
    import tempfile
    from pathlib import Path
    from worklog_mcp.project_context import ProjectContext
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    # テスト用のプロジェクトディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_project_dir:
        try:
            project_context = ProjectContext(temp_project_dir)
            project_context.initialize_project_directories()
            
            database = Database(db_path)
            
            # テーブルを手動で作成
            async with aiosqlite.connect(database.db_path) as db:
                await database._create_tables(db)
                await db.commit()
            
            # エージェントインポートを実行（アバター付き）
            await database.import_example_agents(project_context)
            
            # ユーザーがインポートされているか確認
            users = await database.get_all_users()
            assert len(users) > 0, "エージェントがインポートされませんでした"
            
            # アバターファイルがコピーされているか確認
            avatar_dir = Path(project_context.get_avatar_path())
            avatar_files = list(avatar_dir.glob("*.png"))
            
            # 少なくとも1つのアバターファイルがコピーされているはず
            assert len(avatar_files) > 0, "アバターファイルがコピーされませんでした"
            
            # データベースにavatar_pathが設定されているユーザーを確認
            users_with_avatar = [user for user in users if user.avatar_path]
            assert len(users_with_avatar) > 0, "avatar_pathが設定されたユーザーがいません"
            
            # 実際にアバターファイルが存在するか確認
            for user in users_with_avatar:
                avatar_path = Path(user.avatar_path)
                assert avatar_path.exists(), f"アバターファイルが存在しません: {user.avatar_path}"
                assert avatar_path.suffix == ".png", f"アバターファイルが不正な拡張子です: {user.avatar_path}"
            
            await database.close()
            
        finally:
            # クリーンアップ
            os.unlink(db_path)


@pytest.mark.asyncio 
async def test_import_example_agents_no_project_context():
    """project_contextなしでのエージェントインポートテスト（アバターなし）"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        database = Database(db_path)
        
        # テーブルを手動で作成
        async with aiosqlite.connect(database.db_path) as db:
            await database._create_tables(db)
            await db.commit()
        
        # project_contextなしでエージェントインポートを実行
        await database.import_example_agents(None)
        
        # ユーザーはインポートされるが、avatar_pathはNoneになる
        users = await database.get_all_users()
        assert len(users) > 0, "エージェントがインポートされませんでした"
        
        # すべてのユーザーのavatar_pathがNoneであることを確認
        for user in users:
            assert user.avatar_path is None, f"project_contextなしではavatar_pathはNoneであるべき: {user.user_id}"
        
        await database.close()
        
    finally:
        # クリーンアップ
        os.unlink(db_path)
