"""
PersonalityEngine - 人格一貫性保持とプロンプト生成エンジン
"""

from typing import Dict, Any, List
from ..models import User


class PersonalityEngine:
    """人格設定からシステムプロンプト生成とキャラクター一貫性管理"""

    def __init__(self):
        # 役割別のベースプロンプトテンプレート
        self.role_templates = {
            "developer": "あなたは経験豊富なソフトウェア開発者です。コードの品質と効率性を重視し、ベストプラクティスに従って開発を行います。",
            "designer": "あなたはクリエイティブなデザイナーです。ユーザビリティとデザインの美しさを追求し、直感的なインターフェースの作成を得意とします。",
            "manager": "あなたはプロジェクトマネージャーです。チーム全体の進捗管理と効率的なワークフロー構築を通じて、プロジェクトの成功を導きます。",
            "analyst": "あなたは分析の専門家です。データを詳細に分析し、問題の根本原因を特定して、実用的な解決策を提案します。",
            "tester": "あなたは品質保証の専門家です。システムの品質向上とバグの早期発見を通じて、安定したソフトウェアの提供を支援します。",
        }

        # 性格特性のキーワードとそれに対応する行動指針
        self.personality_patterns = {
            "明るい": "常に前向きで楽観的な視点を持ち、チームの士気を高めるコミュニケーションを心がけます。",
            "協力的": "チームワークを重視し、他のメンバーとの協調と相互支援を大切にします。",
            "慎重": "リスクを十分に検討し、慎重に判断を下して確実な進歩を目指します。",
            "革新的": "新しいアイデアや技術の導入に積極的で、創造的な解決策を模索します。",
            "論理的": "データと事実に基づいて論理的に判断し、構造化されたアプローチを取ります。",
            "親しみやすい": "フレンドリーで親しみやすいコミュニケーションスタイルを維持します。",
        }

        # 外見設定からコミュニケーションスタイルへのマッピング
        self.appearance_styles = {
            "笑顔": "温かく親しみやすい口調で、ポジティブな雰囲気を作ります。",
            "真面目": "丁寧で礼儀正しい口調を保ち、プロフェッショナルな対応を心がけます。",
            "元気": "エネルギッシュで活発な表現を使い、積極性を示します。",
            "落ち着いた": "冷静で安定した口調で、信頼感のあるコミュニケーションを行います。",
        }

    def build_system_prompt(self, user: User) -> str:
        """ユーザー設定から包括的なシステムプロンプトを生成"""
        prompt_sections = []

        # 基本的なAIの設定
        prompt_sections.append(self._get_base_ai_config())

        # 役割に基づいたベースプロンプト
        if user.role:
            role_prompt = self._generate_role_prompt(user.role)
            if role_prompt:
                prompt_sections.append(role_prompt)

        # 性格特性の統合
        if user.personality:
            personality_prompt = self._generate_personality_prompt(user.personality)
            if personality_prompt:
                prompt_sections.append(personality_prompt)

        # 外見・コミュニケーションスタイル
        if user.appearance:
            style_prompt = self._generate_style_prompt(user.appearance)
            if style_prompt:
                prompt_sections.append(style_prompt)

        # カスタム指示の統合
        if user.instruction:
            prompt_sections.append(f"特別な指示: {user.instruction}")

        # 作業ログシステム連携の説明
        prompt_sections.append(self._get_worklog_integration_prompt())

        # 一貫性保持の指示
        prompt_sections.append(self._get_consistency_prompt())

        return "\n\n".join(prompt_sections)

    def _get_base_ai_config(self) -> str:
        """基本的なAI設定"""
        return """あなたは日本語で会話し、日本語でコードや文書を作成するAIアシスタントです。
ユーザーの作業効率向上と目標達成を支援することが主な目的です。"""

    def _generate_role_prompt(self, role: str) -> str:
        """役割に基づいたプロンプト生成"""
        # 役割名の正規化（小文字、空白除去）
        normalized_role = role.lower().strip()

        # 定義済みテンプレートの確認
        for template_role, template_text in self.role_templates.items():
            if template_role in normalized_role or normalized_role in template_role:
                return f"役割と専門性: {template_text}"

        # カスタム役割の場合
        return f"役割と専門性: あなたは{role}として、その専門知識と経験を活かしてユーザーを支援します。"

    def _generate_personality_prompt(self, personality: str) -> str:
        """性格特性からプロンプト生成"""
        personality_instructions = []

        for pattern, instruction in self.personality_patterns.items():
            if pattern in personality:
                personality_instructions.append(instruction)

        if personality_instructions:
            base_text = f"性格特性: {personality}\n行動指針: "
            return base_text + " ".join(personality_instructions)
        else:
            return f"性格特性: {personality}\nこの性格特性を反映したコミュニケーションを心がけてください。"

    def _generate_style_prompt(self, appearance: str) -> str:
        """外見設定からコミュニケーションスタイル生成"""
        style_instructions = []

        for style_key, instruction in self.appearance_styles.items():
            if style_key in appearance:
                style_instructions.append(instruction)

        if style_instructions:
            base_text = f"キャラクター設定: {appearance}\nコミュニケーションスタイル: "
            return base_text + " ".join(style_instructions)
        else:
            return f"キャラクター設定: {appearance}\nこの設定に合った話し方と振る舞いを保ってください。"

    def _get_worklog_integration_prompt(self) -> str:
        """作業ログシステム連携の説明"""
        return """作業ログシステム連携: あなたは分報（作業ログ）システムと連携して動作します。
ユーザーの作業記録の作成、検索、分析を支援し、効率的な作業管理をサポートしてください。
作業の進捗状況を把握し、適切なアドバイスや次のステップの提案を行ってください。"""

    def _get_consistency_prompt(self) -> str:
        """一貫性保持の指示"""
        return """一貫性の保持: 会話を通じて、設定された人格、役割、コミュニケーションスタイルを一貫して保ってください。
ユーザーとの長期的な関係において、信頼できるパートナーとしての存在感を維持してください。
専門知識の提供と人間らしいサポートのバランスを取りながら、効果的な支援を行ってください。"""

    def generate_persona_instructions(
        self, personality: str, appearance: str, role: str
    ) -> str:
        """人格一貫性保持用の短縮指示生成"""
        instructions = []

        if role:
            instructions.append(f"役割: {role}")

        if personality:
            instructions.append(f"性格: {personality}")

        if appearance:
            instructions.append(f"スタイル: {appearance}")

        instructions.append("設定に基づいた一貫した人格を保持してください。")

        return " | ".join(instructions)

    def optimize_for_model(self, prompt: str, model: str) -> str:
        """モデル固有の最適化"""
        if "claude-3" in model.lower():
            # Claude 3シリーズ用の最適化
            return self._optimize_for_claude3(prompt)
        elif "gpt" in model.lower():
            # GPT用の最適化（将来的な拡張用）
            return self._optimize_for_gpt(prompt)
        else:
            return prompt

    def _optimize_for_claude3(self, prompt: str) -> str:
        """Claude 3用の最適化"""
        # Claude 3は長いプロンプトを効率的に処理できるため、
        # 詳細な指示を含めて精度を向上させる
        optimization_suffix = "\n\n重要: 上記の設定に基づいて、一貫性のある人格で対応してください。日本語での自然なコミュニケーションを心がけ、ユーザーの作業効率向上を最優先に考えてサポートを提供してください。"
        return prompt + optimization_suffix

    def _optimize_for_gpt(self, prompt: str) -> str:
        """GPT用の最適化（将来的な拡張用）"""
        # GPT用の最適化ロジックをここに実装
        return prompt

    def extract_personality_traits(self, text: str) -> List[str]:
        """テキストから性格特性キーワードを抽出"""
        traits = []
        for pattern in self.personality_patterns.keys():
            if pattern in text:
                traits.append(pattern)
        return traits

    def suggest_personality_enhancements(self, user: User) -> Dict[str, Any]:
        """ユーザー設定に基づいた人格向上提案"""
        suggestions = {
            "missing_elements": [],
            "enhancement_ideas": [],
            "consistency_tips": [],
        }

        # 不足している要素の確認
        if not user.personality or len(user.personality) < 10:
            suggestions["missing_elements"].append("性格特性の詳細化")

        if not user.appearance or len(user.appearance) < 10:
            suggestions["missing_elements"].append("コミュニケーションスタイルの明確化")

        if not user.instruction:
            suggestions["missing_elements"].append("特別な指示やカスタマイズ")

        # 向上案の提案
        current_traits = self.extract_personality_traits(user.personality or "")
        if len(current_traits) < 2:
            suggestions["enhancement_ideas"].append(
                "複数の性格特性を組み合わせることで、より豊かなキャラクターを作成できます"
            )

        # 一貫性のヒント
        suggestions["consistency_tips"].append(
            "役割、性格、外見設定が相互に補完し合うように調整すると効果的です"
        )

        return suggestions
