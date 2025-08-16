"""AI Agents システムのテスト（マルチLLM対応）"""

import pytest
from pathlib import Path
import tempfile
from worklog_mcp.models import User, AgentConfig
from worklog_mcp.ai_agents.user_config_converter import UserConfigConverter
from worklog_mcp.ai_agents.personality_engine import PersonalityEngine


class TestUserConfigConverter:
    """UserConfigConverter のテスト（マルチプロバイダー対応）"""

    def setup_method(self):
        """テストセットアップ"""
        self.converter = UserConfigConverter()
        self.test_user = User(
            user_id="test_user",
            name="テストユーザー",
            role="developer",
            personality="明るく協力的で、常に学習意欲を持っています。",
            appearance="笑顔を絶やさず、親しみやすい雰囲気です。",
            instruction="詳細な説明を心がけ、具体例を多用してください。",
            model="claude-3-5-sonnet-20241022",
            tools="Read,Write,Edit,Bash",
            mcp='{"worklog": {"enabled": true}}'
        )

    def test_convert_user_to_agent_config_claude(self):
        """ユーザー設定からエージェント設定への変換テスト（Claude）"""
        workspace_path = "/tmp/test_workspace"
        agent_config = self.converter.convert_user_to_agent_config(
            self.test_user, workspace_path, provider="claude"
        )

        assert isinstance(agent_config, AgentConfig)
        assert agent_config.agent_id == "agent_test_user"
        assert agent_config.user_id == "test_user"
        assert agent_config.claude_model == "claude-3-5-sonnet-20241022"
        assert agent_config.workspace_path == workspace_path
        assert "developer" in agent_config.system_prompt
        assert "明るく協力的" in agent_config.system_prompt
        assert "笑顔" in agent_config.system_prompt
        assert "詳細な説明" in agent_config.system_prompt

    def test_convert_user_to_agent_config_openai(self):
        """ユーザー設定からエージェント設定への変換テスト（OpenAI）"""
        workspace_path = "/tmp/test_workspace"
        agent_config = self.converter.convert_user_to_agent_config(
            self.test_user, workspace_path, provider="openai"
        )

        assert isinstance(agent_config, AgentConfig)
        assert agent_config.agent_id == "agent_test_user"
        assert agent_config.claude_model == "claude-3-5-sonnet-20241022"  # TODO: rename field
        assert "OpenAI向け最適化" in agent_config.system_prompt or "設定に基づいて" in agent_config.system_prompt

    def test_unsupported_provider(self):
        """サポートされていないプロバイダーのテスト"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            self.converter.convert_user_to_agent_config(
                self.test_user, provider="unsupported"
            )

    def test_build_system_prompt_with_provider(self):
        """プロバイダー別システムプロンプト構築テスト"""
        # Claude
        claude_prompt = self.converter._build_system_prompt(self.test_user, "claude")
        assert "日本語で会話し" in claude_prompt
        assert "一貫して保持" in claude_prompt

        # OpenAI
        openai_prompt = self.converter._build_system_prompt(self.test_user, "openai")
        assert "日本語で会話し" in openai_prompt
        assert "一貫した人格で" in openai_prompt

    def test_build_session_config(self):
        """プロバイダー別セッション設定テスト"""
        # Claude
        claude_config = self.converter._build_session_config("claude")
        assert claude_config["temperature"] == 0.1
        assert claude_config["max_tokens"] == 4096

        # OpenAI
        openai_config = self.converter._build_session_config("openai")
        assert openai_config["temperature"] == 0.2
        assert openai_config["max_tokens"] == 4000

    def test_generate_llm_settings_claude(self):
        """Claude用LLM設定生成テスト"""
        agent_config = self.converter.convert_user_to_agent_config(self.test_user, provider="claude")
        settings = self.converter.generate_llm_settings(agent_config, provider="claude")

        assert settings["model"] == "claude-3-5-sonnet-20241022"
        assert "systemPrompt" in settings
        assert settings["tools"]["permissionMode"] == "acceptEdits"
        assert "session" in settings

    def test_generate_llm_settings_openai(self):
        """OpenAI用LLM設定生成テスト"""
        agent_config = self.converter.convert_user_to_agent_config(self.test_user, provider="openai")
        settings = self.converter.generate_llm_settings(agent_config, provider="openai")

        assert settings["model"] == "claude-3-5-sonnet-20241022"  # TODO: field rename
        assert "system_message" in settings
        assert "tools" in settings
        assert "parameters" in settings

    def test_save_llm_settings(self):
        """LLM設定ファイル保存テスト"""
        agent_config = self.converter.convert_user_to_agent_config(self.test_user, provider="claude")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            
            # Claude設定保存
            claude_file = self.converter.save_llm_settings(agent_config, output_path, "claude")
            assert claude_file.exists()
            assert claude_file.name == f"claude_settings_{agent_config.agent_id}.json"
            
            # OpenAI設定保存
            openai_file = self.converter.save_llm_settings(agent_config, output_path, "openai")
            assert openai_file.exists()
            assert openai_file.name == f"openai_settings_{agent_config.agent_id}.json"

    def test_get_supported_providers(self):
        """サポートプロバイダー一覧テスト"""
        providers = self.converter.get_supported_providers()
        
        assert "claude" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        
        assert "default_model" in providers["claude"]
        assert "executable" in providers["claude"]

    def test_detect_provider_from_model(self):
        """モデル名からプロバイダー推定テスト"""
        assert self.converter.detect_provider_from_model("claude-3-5-sonnet") == "claude"
        assert self.converter.detect_provider_from_model("gpt-4") == "openai"
        assert self.converter.detect_provider_from_model("anthropic-claude") == "anthropic"
        assert self.converter.detect_provider_from_model("unknown-model") == "claude"  # default

    def test_validate_agent_config(self):
        """エージェント設定検証テスト"""
        agent_config = self.converter.convert_user_to_agent_config(self.test_user)
        errors = self.converter.validate_agent_config(agent_config)
        assert len(errors) == 0

        # 不正な設定のテスト
        invalid_config = AgentConfig(
            agent_id="",
            claude_model="",
            system_prompt="",
            allowed_tools=[],
            mcp_servers={},
            session_config={},
            user_id=""
        )
        errors = self.converter.validate_agent_config(invalid_config)
        assert len(errors) > 0


class TestPersonalityEngine:
    """PersonalityEngine のテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.engine = PersonalityEngine()
        self.test_user = User(
            user_id="test_user",
            name="テストユーザー",
            role="developer",
            personality="明るい協力的で、論理的な思考を持っています。",
            appearance="笑顔を絶やさず、落ち着いた雰囲気です。",
            instruction="常に具体例を示してください。"
        )

    def test_build_system_prompt(self):
        """システムプロンプト構築テスト"""
        prompt = self.engine.build_system_prompt(self.test_user)
        
        assert "日本語で会話し" in prompt
        assert "developer" in prompt or "開発者" in prompt
        assert "明るい" in prompt
        assert "協力的" in prompt
        assert "論理的" in prompt
        assert "笑顔" in prompt
        assert "落ち着いた" in prompt
        assert "具体例を示して" in prompt
        assert "作業ログシステム" in prompt
        assert "一貫性の保持" in prompt

    def test_generate_role_prompt(self):
        """役割プロンプト生成テスト"""
        # 定義済み役割
        developer_prompt = self.engine._generate_role_prompt("developer")
        assert "ソフトウェア開発者" in developer_prompt
        assert "コードの品質" in developer_prompt

        # カスタム役割
        custom_prompt = self.engine._generate_role_prompt("カスタム専門家")
        assert "カスタム専門家" in custom_prompt

    def test_generate_personality_prompt(self):
        """性格プロンプト生成テスト"""
        personality = "明るい協力的論理的です"
        prompt = self.engine._generate_personality_prompt(personality)
        
        assert "明るい協力的論理的です" in prompt
        assert "前向きで楽観的" in prompt  # 明るいのパターン
        assert "チームワークを重視" in prompt  # 協力的のパターン
        assert "論理的に判断" in prompt  # 論理的のパターン

    def test_generate_style_prompt(self):
        """スタイルプロンプト生成テスト"""
        appearance = "笑顔で元気な雰囲気です"
        prompt = self.engine._generate_style_prompt(appearance)
        
        assert "笑顔で元気な雰囲気です" in prompt
        assert "温かく親しみやすい" in prompt  # 笑顔のスタイル
        assert "エネルギッシュ" in prompt  # 元気のスタイル

    def test_generate_persona_instructions(self):
        """人格指示生成テスト"""
        instructions = self.engine.generate_persona_instructions(
            "明るい", "笑顔", "developer"
        )
        
        assert "役割: developer" in instructions
        assert "性格: 明るい" in instructions
        assert "スタイル: 笑顔" in instructions
        assert "一貫した人格を保持" in instructions

    def test_optimize_for_model(self):
        """モデル最適化テスト"""
        base_prompt = "テストプロンプト"
        
        # Claude 3用最適化
        claude_prompt = self.engine.optimize_for_model(base_prompt, "claude-3-5-sonnet")
        assert len(claude_prompt) > len(base_prompt)
        assert "一貫性のある人格" in claude_prompt

        # 未知のモデル
        unknown_prompt = self.engine.optimize_for_model(base_prompt, "unknown-model")
        assert unknown_prompt == base_prompt

    def test_extract_personality_traits(self):
        """性格特性抽出テスト"""
        text = "明るい協力的論理的な性格です"
        traits = self.engine.extract_personality_traits(text)
        
        assert "明るい" in traits
        assert "協力的" in traits
        assert "論理的" in traits

    def test_suggest_personality_enhancements(self):
        """人格向上提案テスト"""
        # 基本的なユーザー
        basic_user = User(
            user_id="basic",
            name="基本ユーザー",
            role="developer",
            personality="普通",
            appearance=""
        )
        
        suggestions = self.engine.suggest_personality_enhancements(basic_user)
        
        assert "missing_elements" in suggestions
        assert "enhancement_ideas" in suggestions
        assert "consistency_tips" in suggestions
        
        # 詳細が不足している場合は提案が含まれる
        assert len(suggestions["missing_elements"]) > 0 or len(suggestions["enhancement_ideas"]) > 0