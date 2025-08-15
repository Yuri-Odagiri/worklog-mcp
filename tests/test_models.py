"""データモデルのテスト"""

import pytest
from datetime import datetime

from worklog_mcp.models import User, WorklogEntry, WorkSummary, generate_id


def test_generate_id():
    """ID生成のテスト"""
    id1 = generate_id()
    id2 = generate_id()
    
    assert isinstance(id1, str)
    assert isinstance(id2, str)
    assert id1 != id2
    assert len(id1) == 36  # UUID4の長さ


def test_user_model():
    """Userモデルのテスト"""
    user = User(user_id="test-user", name="テストユーザー", role="開発者")
    
    assert user.user_id == "test-user"
    assert user.name == "テストユーザー"
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.last_active, datetime)


def test_user_id_validation():
    """user_idバリデーションのテスト"""
    # 有効なuser_id
    valid_ids = ["user1", "test-user", "user_123", "test_user"]
    for user_id in valid_ids:
        user = User(user_id=user_id, name="テストユーザー", role="開発者")
        assert user.user_id == user_id
    
    # 無効なuser_id
    invalid_ids = ["user@domain", "user space", "ユーザー1", "user.123"]
    for user_id in invalid_ids:
        with pytest.raises(ValueError):
            User(user_id=user_id, name="テストユーザー", role="開発者")


def test_worklog_entry_model():
    """WorklogEntryモデルのテスト"""
    entry = WorklogEntry(
        user_id="test-user",
        markdown_content="## 作業\n- テスト実装"
    )
    
    assert entry.user_id == "test-user"
    assert entry.markdown_content == "## 作業\n- テスト実装"
    assert entry.related_entry_id is None
    assert isinstance(entry.id, str)
    assert isinstance(entry.created_at, datetime)
    assert isinstance(entry.updated_at, datetime)


def test_worklog_entry_with_related():
    """関連エントリー付きWorklogEntryのテスト"""
    parent_id = generate_id()
    entry = WorklogEntry(
        user_id="test-user",
        markdown_content="返信内容",
        related_entry_id=parent_id
    )
    
    assert entry.related_entry_id == parent_id


def test_work_summary_model():
    """WorkSummaryモデルのテスト"""
    start_time = datetime.now()
    end_time = datetime.now()
    
    summary = WorkSummary(
        user_id="test-user",
        period_start=start_time,
        period_end=end_time,
        entry_count=5,
        work_entries=["作業1", "作業2"],
        completed_items=["完了1"],
        issues=["問題1"],
        log_type_counts={"work": 2, "completed": 1, "issue": 1}
    )
    
    assert summary.user_id == "test-user"
    assert summary.period_start == start_time
    assert summary.period_end == end_time
    assert summary.entry_count == 5
    assert len(summary.work_entries) == 2
    assert len(summary.completed_items) == 1
    assert len(summary.issues) == 1
    assert summary.log_type_counts["work"] == 2
    assert isinstance(summary.generated_at, datetime)


def test_worklog_entry_default_values():
    """WorklogEntryのデフォルト値テスト"""
    entry = WorklogEntry()
    
    assert entry.user_id == ""
    assert entry.markdown_content == ""
    assert entry.related_entry_id is None
    assert isinstance(entry.id, str)
    assert len(entry.id) == 36  # UUID4の長さ
    assert isinstance(entry.created_at, datetime)
    assert isinstance(entry.updated_at, datetime)


def test_work_summary_default_values():
    """WorkSummaryのデフォルト値テスト"""
    start_time = datetime.now()
    end_time = datetime.now()
    
    summary = WorkSummary(
        user_id="test-user",
        period_start=start_time,
        period_end=end_time,
        entry_count=0
    )
    
    assert summary.work_entries == []
    assert summary.completed_items == []
    assert summary.issues == []
    assert summary.log_type_counts == {}
    assert isinstance(summary.generated_at, datetime)