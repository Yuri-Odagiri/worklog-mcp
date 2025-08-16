"""
UserConfigConverter - ユーザー設定を各種LLM設定に変換
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from ..models import User, AgentConfig


class UserConfigConverter:
    """ユーザー設定をエージェント設定に変換するクラス（マルチLLM対応）"""

    # ユーザーフィールドからLLM設定へのマッピング
    USER_FIELD_MAPPING = {
        "personality": "system_prompt_personality",
        "appearance": "system_prompt_appearance",
        "role": "system_prompt_role",
        "instruction": "system_prompt_custom",
        "model": "llm_model",
        "mcp": "mcp_servers_config",
        "tools": "allowed_tools",
    }

    # サポートしているLLMプロバイダー
    SUPPORTED_PROVIDERS = {
        "claude": {
            "default_model": "claude-3-5-sonnet-20241022",
            "executable": "claude",
            "config_format": "claude_code",
        },
        "openai": {
            "default_model": "gpt-4",
            "executable": "openai-cli",  # 仮想的
            "config_format": "openai_api",
        },
        "anthropic": {
            "default_model": "claude-3-5-sonnet-20241022",
            "executable": "anthropic-cli",  # 仮想的
            "config_format": "anthropic_api",
        },
    }

    def __init__(self):
        self.default_tools = [
            "Read",
            "Write",
            "Edit",
            "Bash",
            "LS",
            "Glob",
            "Grep",
            "TodoWrite",
            "WebSearch",
            "WebFetch",
        ]
        self.default_mcp_servers = {}

    def convert_user_to_agent_config(
        self, user: User, workspace_path: str = "", provider: str = "claude"
    ) -> AgentConfig:
        """ユーザー設定をエージェント設定に変換（マルチプロバイダー対応）"""

        # プロバイダー検証
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. Supported: {list(self.SUPPORTED_PROVIDERS.keys())}"
            )

        provider_config = self.SUPPORTED_PROVIDERS[provider]

        # システムプロンプトを構築
        system_prompt = self._build_system_prompt(user, provider)

        # ツール設定の解析
        allowed_tools = self._parse_tools_config(user.tools)

        # MCPサーバー設定の解析
        mcp_servers = self._parse_mcp_config(user.mcp)

        # LLMモデルの決定
        llm_model = user.model if user.model else provider_config["default_model"]

        # セッション設定（プロバイダー固有）
        session_config = self._build_session_config(provider)

        return AgentConfig(
            agent_id=f"agent_{user.user_id}",
            claude_model=llm_model,  # TODO: claude_model → llm_model にリネーム予定
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            mcp_servers=mcp_servers,
            session_config=session_config,
            user_id=user.user_id,
            workspace_path=workspace_path,
        )

    def _build_system_prompt(self, user: User, provider: str) -> str:
        """ユーザー設定からシステムプロンプトを構築（プロバイダー最適化）"""
        prompt_parts = []

        # 基本的な日本語対応設定
        prompt_parts.append(
            "あなたは日本語で会話し、日本語でコードや文書を作成するAIアシスタントです。"
        )

        # 役割の設定
        if user.role:
            prompt_parts.append(f"あなたの役割: {user.role}")

        # 性格の設定
        if user.personality:
            prompt_parts.append(f"性格特性: {user.personality}")

        # 外見・キャラクター設定
        if user.appearance:
            prompt_parts.append(f"キャラクター設定: {user.appearance}")

        # カスタム指示
        if user.instruction:
            prompt_parts.append(f"特別な指示: {user.instruction}")

        # 作業ログシステムとの連携
        prompt_parts.append(
            "作業ログ（分報）システムと連携して、ユーザーの作業を支援してください。"
        )
        prompt_parts.append(
            "一貫した人格とトーンを保ちながら、効率的で協力的なサポートを提供してください。"
        )

        # プロバイダー固有の最適化
        base_prompt = "\n\n".join(prompt_parts)
        return self._optimize_prompt_for_provider(base_prompt, provider)

    def _optimize_prompt_for_provider(self, prompt: str, provider: str) -> str:
        """プロバイダー固有のプロンプト最適化"""
        if provider == "claude":
            # Claude向け最適化（長いプロンプトに強い）
            return (
                prompt
                + "\n\n重要: 設定された人格を一貫して保持し、日本語での自然なコミュニケーションを心がけてください。"
            )
        elif provider == "openai":
            # OpenAI向け最適化（簡潔な指示が効果的）
            return prompt + "\n\n設定に基づいて一貫した人格でサポートしてください。"
        else:
            return prompt

    def _build_session_config(self, provider: str) -> Dict[str, Any]:
        """プロバイダー固有のセッション設定構築"""
        base_config = {"max_turns": 100, "timeout": 300}

        if provider == "claude":
            base_config.update(
                {
                    "temperature": 0.1,
                    "max_tokens": 4096,
                }
            )
        elif provider == "openai":
            base_config.update(
                {
                    "temperature": 0.2,
                    "max_tokens": 4000,
                }
            )

        return base_config

    def _parse_tools_config(self, tools_config: str) -> List[str]:
        """ツール設定文字列を解析"""
        if not tools_config:
            return self.default_tools

        try:
            # JSON形式の場合
            if tools_config.strip().startswith("["):
                return json.loads(tools_config)
            # カンマ区切りの場合
            elif "," in tools_config:
                return [
                    tool.strip() for tool in tools_config.split(",") if tool.strip()
                ]
            # 単一ツールの場合
            else:
                return [tools_config.strip()]
        except (json.JSONDecodeError, ValueError):
            # 解析失敗時はデフォルトを返す
            return self.default_tools

    def _parse_mcp_config(self, mcp_config: str) -> Dict[str, Any]:
        """MCP設定文字列を解析"""
        if not mcp_config:
            return self.default_mcp_servers

        try:
            if mcp_config.strip().startswith("{"):
                return json.loads(mcp_config)
        except json.JSONDecodeError:
            pass

        return self.default_mcp_servers

    def generate_llm_settings(
        self, agent_config: AgentConfig, provider: str = "claude"
    ) -> Dict[str, Any]:
        """LLM用設定生成（プロバイダー対応）"""
        if provider == "claude":
            return self._generate_claude_settings(agent_config)
        elif provider == "openai":
            return self._generate_openai_settings(agent_config)
        else:
            # デフォルトはClaude形式
            return self._generate_claude_settings(agent_config)

    def _generate_claude_settings(self, agent_config: AgentConfig) -> Dict[str, Any]:
        """Claude Code用settings.json生成"""
        settings = {
            "model": agent_config.claude_model,
            "systemPrompt": agent_config.system_prompt,
            "tools": {
                "allowed": agent_config.allowed_tools,
                "permissionMode": "acceptEdits",
            },
            "mcp": {"servers": agent_config.mcp_servers},
            "session": agent_config.session_config,
        }

        return settings

    def _generate_openai_settings(self, agent_config: AgentConfig) -> Dict[str, Any]:
        """OpenAI API用設定生成（将来的な拡張用）"""
        settings = {
            "model": agent_config.claude_model,  # TODO: model field名の統一
            "system_message": agent_config.system_prompt,
            "tools": agent_config.allowed_tools,
            "parameters": agent_config.session_config,
        }

        return settings

    def save_llm_settings(
        self, agent_config: AgentConfig, output_path: Path, provider: str = "claude"
    ) -> Path:
        """LLM設定をファイルに保存"""
        settings = self.generate_llm_settings(agent_config, provider)

        settings_file = (
            output_path / f"{provider}_settings_{agent_config.agent_id}.json"
        )
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        return settings_file

    def validate_agent_config(self, agent_config: AgentConfig) -> List[str]:
        """エージェント設定の検証"""
        errors = []

        if not agent_config.agent_id:
            errors.append("agent_idが設定されていません")

        if not agent_config.user_id:
            errors.append("user_idが設定されていません")

        if not agent_config.claude_model:  # TODO: claude_model → llm_model
            errors.append("llm_modelが設定されていません")

        if not agent_config.system_prompt:
            errors.append("system_promptが設定されていません")

        if not agent_config.allowed_tools:
            errors.append("allowed_toolsが設定されていません")

        return errors

    def get_supported_providers(self) -> Dict[str, Dict[str, Any]]:
        """サポートしているプロバイダー一覧を取得"""
        return self.SUPPORTED_PROVIDERS.copy()

    def detect_provider_from_model(self, model_name: str) -> str:
        """モデル名からプロバイダーを推定"""
        model_lower = model_name.lower()

        # anthropicを先にチェック（claude-3がanthropicのモデルの場合があるため）
        if "anthropic" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "claude"
        else:
            # デフォルトはclaude
            return "claude"
