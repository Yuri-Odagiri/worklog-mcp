"""完全リセット機能のテスト"""

import tempfile
import pytest
from pathlib import Path
import asyncio
import os
import shutil

from worklog_mcp.project_context import ProjectContext
from worklog_mcp.database import Database
from worklog_mcp.models import User, WorklogEntry


@pytest.mark.asyncio
async def test_delete_project_directory():
    """プロジェクトディレクトリ削除機能のテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # テスト用プロジェクトパス
        project_path = os.path.join(temp_dir, "test_project")
        os.makedirs(project_path, exist_ok=True)
        
        # ProjectContextを作成
        context = ProjectContext(project_path)
        
        # プロジェクトディレクトリを初期化（ファイルやディレクトリを作成）
        context.initialize_project_directories()
        
        # ディレクトリが作成されたことを確認
        project_dir = context._get_project_dir()
        assert project_dir.exists()
        
        # 削除を実行
        result = context.delete_project_directory()
        
        # 削除が成功し、ディレクトリが存在しないことを確認
        assert result is True
        assert not project_dir.exists()


@pytest.mark.asyncio
async def test_delete_project_directory_not_exists():
    """存在しないプロジェクトディレクトリの削除テスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 存在しないプロジェクトパス
        project_path = os.path.join(temp_dir, "nonexistent_project")
        
        # ProjectContextを作成（ディレクトリは作成しない）
        context = ProjectContext(project_path)
        
        # 削除を実行（ディレクトリが存在しないので失敗するはず）
        result = context.delete_project_directory()
        
        # 削除が失敗することを確認
        assert result is False


@pytest.mark.asyncio
async def test_full_project_reset():
    """完全プロジェクトリセット機能のテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # テスト用プロジェクトパス
        project_path = os.path.join(temp_dir, "test_reset_project")
        os.makedirs(project_path, exist_ok=True)
        
        # ProjectContextとDatabaseを作成
        context = ProjectContext(project_path)
        
        # プロジェクトディレクトリを初期化
        context.initialize_project_directories()
        
        # データベースを初期化
        db_path = context.get_database_path()
        db = Database(db_path)
        await db.initialize()
        
        # テストデータを追加
        import uuid
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        test_user = User(
            user_id=test_user_id,
            name="Test User",
            role="test",
            personality="friendly",
            appearance="tall",
            theme_color="Red"
        )
        await db.create_user(test_user)
        
        test_entry = WorklogEntry(
            user_id=test_user_id,
            markdown_content="テストエントリー"
        )
        await db.create_entry(test_entry)
        
        # プロジェクトディレクトリが存在することを確認
        project_dir = context._get_project_dir()
        assert project_dir.exists()
        
        # 完全リセットを実行
        result = await db.full_project_reset(context)
        
        # 結果を確認
        assert result["project_directory_deleted"] is True
        assert result["eventbus_deleted"] is True
        assert result["jobqueue_deleted"] is True
        assert result["users_truncated"] is True
        
        # プロジェクトディレクトリが削除されたことを確認
        assert not project_dir.exists()


@pytest.mark.asyncio
async def test_full_project_reset_with_files():
    """ファイルが存在するプロジェクトの完全リセットテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # テスト用プロジェクトパス
        project_path = os.path.join(temp_dir, "test_files_project")
        os.makedirs(project_path, exist_ok=True)
        
        # ProjectContextを作成
        context = ProjectContext(project_path)
        context.initialize_project_directories()
        
        # データベースを初期化
        db_path = context.get_database_path()
        db = Database(db_path)
        await db.initialize()
        
        # 追加のファイルを作成
        project_dir = context._get_project_dir()
        test_file = project_dir / "test_file.txt"
        test_file.write_text("テストファイル")
        
        # avatarディレクトリにファイルを作成
        avatar_dir = Path(context.get_avatar_path())
        avatar_file = avatar_dir / "test_avatar.png"
        avatar_file.write_bytes(b"fake image data")
        
        # ファイルが存在することを確認
        assert test_file.exists()
        assert avatar_file.exists()
        
        # 完全リセットを実行
        result = await db.full_project_reset(context)
        
        # 全ファイルが削除されたことを確認
        assert result["project_directory_deleted"] is True
        assert not project_dir.exists()
        assert not test_file.exists()
        assert not avatar_file.exists()