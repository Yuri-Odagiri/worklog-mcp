"""プロジェクトコンテキストのテスト"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch

from worklog_mcp.project_context import ProjectContext, ProjectConfig


def test_default_project_context():
    """デフォルトプロジェクトコンテキストのテスト"""
    context = ProjectContext()
    
    assert context.get_project_name() == "default"
    assert context.get_project_description() == "デフォルトプロジェクト"
    assert context.project_path is None


def test_project_context_with_path():
    """プロジェクトパス指定時のテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        context = ProjectContext(temp_dir)
        
        project_name = context.get_project_name()
        assert project_name != "default"
        # ディレクトリ名がプロジェクト名に含まれることを確認
        temp_dir_name = Path(temp_dir).name
        assert temp_dir_name in project_name or project_name.replace('_', '') in temp_dir_name


def test_project_context_with_path_auto_generation():
    """プロジェクトパスからの自動生成テスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # プロジェクトコンテキスト作成
        context = ProjectContext(temp_dir)
        
        project_name = context.get_project_name()
        assert project_name != "default"
        assert temp_dir.split('/')[-1] in project_name
        assert context.get_project_description() == f"プロジェクト: {Path(temp_dir).name}"




def test_database_path_separation():
    """データベースパスの分離テスト"""
    with tempfile.TemporaryDirectory() as temp_dir1, \
         tempfile.TemporaryDirectory() as temp_dir2:
        
        context1 = ProjectContext(temp_dir1)
        context2 = ProjectContext(temp_dir2)
        
        db_path1 = context1.get_database_path()
        db_path2 = context2.get_database_path()
        
        # 異なるプロジェクトは異なるデータベースパスを持つ
        assert db_path1 != db_path2
        assert context1.get_project_name() in db_path1
        assert context2.get_project_name() in db_path2




def test_get_project_info():
    """プロジェクト情報取得のテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        context = ProjectContext(temp_dir)
        info = context.get_project_info()
        
        assert info["project_name"] != "default"
        assert info["description"] == f"プロジェクト: {Path(temp_dir).name}"
        assert info["project_path"] == temp_dir
        assert info["config_file_exists"] is False
        assert "database_path" in info



def test_safe_project_name_generation():
    """安全なプロジェクト名生成のテスト"""
    # 特殊文字を含むパス
    test_cases = [
        ("/path/with spaces/project", "project"),  # スペースは_に変換される
        ("/path/with-hyphens/project", "project"),  # ハイフンはそのまま
        ("/path/with_underscores/project", "project"),  # アンダースコアはそのまま
        ("/path/with@symbols/project", "project"),  # @は_に変換される
        ("/path/with.dots/project", "project")  # .は_に変換される
    ]
    
    for path, expected_base in test_cases:
        context = ProjectContext(path)
        project_name = context.get_project_name()
        
        # 英数字、ハイフン、アンダースコアのみ使用
        import re
        assert re.match(r'^[a-zA-Z0-9-_]+$', project_name)
        # ベース名がプロジェクト名に含まれることを確認
        assert expected_base in project_name


def test_current_directory_usage():
    """現在のディレクトリ使用時のテスト"""
    import os
    current_dir = os.getcwd()
    
    # 現在のディレクトリを使用してプロジェクトコンテキストを作成
    context = ProjectContext(current_dir)
    
    project_name = context.get_project_name()
    expected_basename = os.path.basename(current_dir)
    
    # プロジェクト名にディレクトリ名が含まれていることを確認
    assert expected_basename in project_name
    assert context.get_project_description() == f"プロジェクト: {expected_basename}"
    assert context.project_path == current_dir