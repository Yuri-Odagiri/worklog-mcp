"""MCPツールの実装 - 新しいモジュラー構造への橋渡し"""

# 新しいモジュラー構造から直接インポート
from .tools import register_tools

__all__ = ["register_tools"]
