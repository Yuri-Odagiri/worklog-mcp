"""データモデル定義"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


def generate_id() -> str:
    """ユニークIDを生成"""
    return str(uuid.uuid4())


@dataclass
class User:
    """ユーザー情報"""

    user_id: str
    name: str
    role: str  # 役割（必須）
    theme_color: str = "Blue"  # Red/Blue/Green/Yellow/Purple/Orange/Pink/Cyanのみ
    personality: str = (
        "明るく協力的で、チームワークを重視する性格です。"  # デフォルトの性格
    )
    appearance: str = (
        "親しみやすい外見で、いつも笑顔を絶やしません。"  # デフォルトの外観
    )
    avatar_path: Optional[str] = None  # アバター画像のパス
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """user_idとtheme_colorの検証"""
        import re

        if not re.match(r"^[a-zA-Z0-9-_]+$", self.user_id):
            raise ValueError(
                "user_idは英数字、ハイフン、アンダースコアのみ使用可能です"
            )

        valid_colors = {
            "Red",
            "Blue",
            "Green",
            "Yellow",
            "Purple",
            "Orange",
            "Pink",
            "Cyan",
        }
        if self.theme_color not in valid_colors:
            raise ValueError(
                f"theme_colorは {', '.join(sorted(valid_colors))} のいずれかを指定してください"
            )


@dataclass
class WorklogEntry:
    """分報エントリー"""

    id: str = field(default_factory=generate_id)
    user_id: str = ""
    markdown_content: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkSummary:
    """作業サマリー"""

    user_id: str
    period_start: datetime
    period_end: datetime
    entry_count: int
    work_entries: List[str] = field(default_factory=list)
    completed_items: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    log_type_counts: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
