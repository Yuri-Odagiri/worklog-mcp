"""プロジェクトコンテキスト管理"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ProjectConfig:
    """プロジェクト設定"""

    project_name: str = "default"
    description: str = ""
    project_path: Optional[str] = None


class ProjectContext:
    """プロジェクトコンテキスト管理クラス"""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path
        self.config: Optional[ProjectConfig] = None
        self._load_config()

    def _load_config(self) -> None:
        """プロジェクト設定を読み込み"""
        if not self.project_path:
            # プロジェクトパスが指定されていない場合はデフォルト設定
            self.config = ProjectConfig(
                project_name="default", description="デフォルトプロジェクト"
            )
            return

        # 設定ファイルは使わず、プロジェクトパスから自動生成
        self.config = ProjectConfig(
            project_name=self._generate_project_name(),
            description=f"プロジェクト: {Path(self.project_path).name}",
            project_path=self.project_path,
        )

    def _generate_project_name(self) -> str:
        """プロジェクトパスからプロジェクト名を生成"""
        if not self.project_path:
            return "default"

        # プロジェクトパスを絶対パスに変換してディレクトリ名を取得
        abs_path = Path(self.project_path).resolve()
        dir_name = abs_path.name

        # 安全なプロジェクト名（英数字、ハイフン、アンダースコアのみ）
        safe_dir_name = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in dir_name
        )

        return safe_dir_name

    def get_project_name(self) -> str:
        """プロジェクト名を取得"""
        return self.config.project_name if self.config else "default"

    def get_project_description(self) -> str:
        """プロジェクト説明を取得"""
        return self.config.description if self.config else ""

    def get_default_user(self) -> Optional[str]:
        """プロジェクトのデフォルトユーザーを取得（削除予定）"""
        # MCPツールでは常にユーザーIDが指定されるため不要
        return None

    def get_database_path(self) -> str:
        """プロジェクト専用のデータベースパスを取得"""
        base_path = os.environ.get("WORKLOG_DB_PATH", os.path.expanduser("~/.worklog"))

        # プロジェクト名でディレクトリを分離
        project_dir = Path(base_path) / self.get_project_name()
        database_dir = project_dir / "database"
        database_dir.mkdir(parents=True, exist_ok=True)

        return str(database_dir / "worklog.db")

    def get_avatar_path(self) -> str:
        """プロジェクト専用のアバターディレクトリパスを取得"""
        base_path = os.environ.get("WORKLOG_DB_PATH", os.path.expanduser("~/.worklog"))

        # プロジェクト名でディレクトリを分離
        project_dir = Path(base_path) / self.get_project_name()
        avatar_dir = project_dir / "avatar"
        avatar_dir.mkdir(parents=True, exist_ok=True)

        return str(avatar_dir)

    def initialize_project_directories(self) -> None:
        """プロジェクトの全ディレクトリを初期化"""
        # データベースディレクトリ作成（get_database_path内で実行済み）
        self.get_database_path()

        # アバターディレクトリ作成
        self.get_avatar_path()

    def create_config_file(
        self,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """プロジェクト設定ファイルを作成（非推奨：プロジェクト名は引数で指定してください）"""
        # 設定ファイルは使用しないため、何もしない
        pass

    def get_project_info(self) -> Dict[str, Any]:
        """プロジェクト情報を取得"""
        return {
            "project_name": self.get_project_name(),
            "description": self.get_project_description(),
            "project_path": self.project_path,
            "database_path": self.get_database_path(),
            "config_file_exists": False,  # 設定ファイルは使用しない
        }


class ProjectContextError(Exception):
    """プロジェクトコンテキスト関連のエラー"""

    pass
