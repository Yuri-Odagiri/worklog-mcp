"""MCP設定動的生成"""

import json
from pathlib import Path
from typing import Dict, Any, List
import logging
from ..models import AgentConfig, AgentSession

logger = logging.getLogger(__name__)


class MCPConfigGenerator:
    """MCP設定ファイル動的生成クラス"""
    
    def __init__(self, base_config_path: str = None):
        self.base_config_path = base_config_path or "config/agent_templates/mcp_config_template.json"
        self.generated_configs_dir = Path("temp/mcp_configs")
        self.generated_configs_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_agent_config(
        self,
        session: AgentSession,
        agent_config: AgentConfig,
        project_path: str
    ) -> str:
        """エージェント専用のMCP設定ファイルを生成"""
        try:
            # テンプレートを読み込み
            template = await self._load_template()
            
            # 変数を置換
            config = self._substitute_variables(
                template,
                session=session,
                agent_config=agent_config,
                project_path=project_path
            )
            
            # エージェント固有の設定を適用
            config = self._apply_agent_specific_config(config, agent_config)
            
            # ファイルに保存
            config_path = self._get_config_path(session.session_id)
            await self._save_config(config, config_path)
            
            logger.info(f"MCP設定ファイルを生成しました: {config_path}")
            return str(config_path)
            
        except Exception as e:
            logger.error(f"MCP設定生成に失敗: {e}")
            raise
    
    async def cleanup_config(self, session_id: str):
        """セッション終了時の設定ファイルクリーンアップ"""
        config_path = self._get_config_path(session_id)
        try:
            if config_path.exists():
                config_path.unlink()
                logger.info(f"MCP設定ファイルを削除しました: {config_path}")
        except Exception as e:
            logger.warning(f"設定ファイル削除に失敗: {e}")
    
    async def _load_template(self) -> Dict[str, Any]:
        """テンプレートファイルを読み込み"""
        try:
            with open(self.base_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"テンプレート読み込みに失敗: {e}")
            # フォールバック用のデフォルト設定
            return self._get_default_template()
    
    def _substitute_variables(
        self,
        template: Dict[str, Any],
        session: AgentSession,
        agent_config: AgentConfig,
        project_path: str
    ) -> Dict[str, Any]:
        """テンプレート内の変数を置換"""
        variables = {
            "agent_id": session.agent_id,
            "user_id": session.user_id,
            "session_id": session.session_id,
            "project_path": project_path,
            "workspace_path": session.workspace_path or project_path
        }
        
        # JSON文字列に変換して一括置換
        template_str = json.dumps(template)
        for key, value in variables.items():
            template_str = template_str.replace(f"{{{key}}}", str(value))
        
        return json.loads(template_str)
    
    def _apply_agent_specific_config(
        self,
        config: Dict[str, Any],
        agent_config: AgentConfig
    ) -> Dict[str, Any]:
        """エージェント固有の設定を適用"""
        
        # MCPサーバー設定を追加
        if agent_config.mcp_servers:
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            config["mcpServers"].update(agent_config.mcp_servers)
        
        # セッション設定を適用
        if agent_config.session_config:
            config.update(agent_config.session_config)
        
        # ツール制限を適用
        if agent_config.allowed_tools:
            config["allowedTools"] = agent_config.allowed_tools
        
        return config
    
    def _get_config_path(self, session_id: str) -> Path:
        """設定ファイルのパスを取得"""
        return self.generated_configs_dir / f"mcp_config_{session_id}.json"
    
    async def _save_config(self, config: Dict[str, Any], path: Path):
        """設定をファイルに保存"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定ファイル保存に失敗: {e}")
            raise
    
    def _get_default_template(self) -> Dict[str, Any]:
        """デフォルトのMCP設定テンプレート"""
        return {
            "mcpServers": {
                "worklog-mcp-{agent_id}": {
                    "command": "uv",
                    "args": [
                        "run", 
                        "python", 
                        "-m", 
                        "worklog_mcp", 
                        "--project", 
                        "{project_path}",
                        "--transport", 
                        "stdio",
                        "--user",
                        "{user_id}",
                        "--agent-mode",
                        "{agent_id}"
                    ],
                    "env": {
                        "WORKLOG_AGENT_ID": "{agent_id}",
                        "WORKLOG_USER_ID": "{user_id}",
                        "WORKLOG_PROJECT_PATH": "{project_path}",
                        "WORKLOG_SESSION_ID": "{session_id}"
                    },
                    "disabled": False
                }
            },
            "serverConfig": {
                "timeout": 30000,
                "retryAttempts": 3,
                "enableLogging": True
            },
            "agentSpecific": {
                "isolation": True,
                "permissions": {
                    "readOnly": False,
                    "allowNetworkAccess": True,
                    "allowFileSystem": True,
                    "restrictedPaths": []
                }
            }
        }
    
    async def list_generated_configs(self) -> List[Dict[str, Any]]:
        """生成済み設定ファイル一覧を取得"""
        configs = []
        
        try:
            for config_file in self.generated_configs_dir.glob("mcp_config_*.json"):
                session_id = config_file.stem.replace("mcp_config_", "")
                stat = config_file.stat()
                
                configs.append({
                    "session_id": session_id,
                    "config_path": str(config_file),
                    "created_at": stat.st_ctime,
                    "size": stat.st_size
                })
        except Exception as e:
            logger.error(f"設定ファイル一覧取得に失敗: {e}")
        
        return configs
    
    async def cleanup_old_configs(self, max_age_hours: int = 24):
        """古い設定ファイルをクリーンアップ"""
        import time
        
        current_time = time.time()
        cleanup_count = 0
        
        try:
            for config_file in self.generated_configs_dir.glob("mcp_config_*.json"):
                if current_time - config_file.stat().st_ctime > max_age_hours * 3600:
                    config_file.unlink()
                    cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"{cleanup_count}個の古い設定ファイルをクリーンアップしました")
                
        except Exception as e:
            logger.error(f"設定ファイルクリーンアップに失敗: {e}")


# グローバルインスタンス
mcp_config_generator = MCPConfigGenerator()