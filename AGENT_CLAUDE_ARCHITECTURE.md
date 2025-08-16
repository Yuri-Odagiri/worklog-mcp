# Agent Claude Code 実行システム アーキテクチャ

## 概要

本システムは、既存のworklog MCPサーバーのユーザー（agent）設定を活用し、各ユーザーの人格設定（personality、appearance、role、instruction）に基づいてClaude Codeを実行する統合システムです。

### 主要目標
- ユーザーごとの一貫した人格でのClaude Code実行
- 既存worklog MCPサーバーとのシームレス統合
- マルチエージェント同時実行サポート
- 設定の動的更新と管理

## システムアーキテクチャ

### 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Claude Code System                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Web Viewer    │  │   MCP Server    │  │   Database      │  │
│  │   (existing)    │  │   (existing)    │  │   (existing)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                     │                     │         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Agent Configuration Manager                  │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │ │
│  │  │ User Config │  │ Personality │  │  MCP Config        │ │ │
│  │  │ Converter   │  │ Engine      │  │  Generator         │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│           │                     │                     │         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Claude Integration Layer                     │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │ │
│  │  │  Session    │  │  Claude     │  │  Process            │ │ │
│  │  │  Manager    │  │  Executor   │  │  Isolation          │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│           │                     │                     │         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  API Gateway                              │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │ │
│  │  │   Agent     │  │   Execution │  │  Results            │ │ │
│  │  │  Selection  │  │   Control   │  │  Handler            │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│           │                     │                     │         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Claude Code Instances                     │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  [Agent A]      [Agent B]      [Agent C]      [Agent N]   │ │
│  │  Claude Code    Claude Code    Claude Code    Claude Code │ │
│  │  (Persona A)    (Persona B)    (Persona C)    (Persona N) │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## コンポーネント詳細設計

### 1. Agent Configuration Manager

#### 1.1 User Config Converter
**ファイル**: `src/worklog_mcp/claude_agents/user_config_converter.py`

```python
@dataclass
class AgentConfig:
    agent_id: str
    claude_model: str
    system_prompt: str
    allowed_tools: List[str]
    mcp_servers: Dict[str, Any]
    session_config: Dict[str, Any]
    persona_config: PersonaConfig

class UserConfigConverter:
    def convert_user_to_agent_config(self, user: User) -> AgentConfig:
        """ユーザー設定をエージェント設定に変換"""
        
    def generate_claude_settings(self, agent_config: AgentConfig) -> Dict[str, Any]:
        """Claude Code用settings.json生成"""
```

#### 1.2 Personality Engine
**ファイル**: `src/worklog_mcp/claude_agents/personality_engine.py`

```python
class PersonalityEngine:
    def build_system_prompt(self, user: User) -> str:
        """人格設定からシステムプロンプト生成"""
        
    def generate_persona_instructions(self, personality: str, appearance: str, role: str) -> str:
        """人格一貫性保持用指示生成"""
        
    def optimize_for_model(self, prompt: str, model: str) -> str:
        """モデル別プロンプト最適化"""
```

#### 1.3 MCP Config Generator
**ファイル**: `src/worklog_mcp/claude_agents/mcp_config_generator.py`

```python
class MCPConfigGenerator:
    def generate_agent_mcp_config(self, user: User) -> Dict[str, Any]:
        """エージェント専用MCP設定生成"""
        
    def create_isolated_mcp_server(self, agent_id: str, user: User) -> str:
        """分離されたMCPサーバー設定作成"""
```

### 2. Claude Integration Layer

#### 2.1 Claude Executor
**ファイル**: `src/worklog_mcp/claude_integration/claude_executor.py`

```python
class ClaudeExecutor:
    def __init__(self, agent_config: AgentConfig):
        self.agent_config = agent_config
        self.process_manager = ProcessManager()
        
    async def start_claude_session(self) -> str:
        """エージェント専用Claude Codeセッション開始"""
        
    async def execute_command(self, command: str, session_id: str) -> Dict[str, Any]:
        """コマンド実行"""
        
    async def stop_session(self, session_id: str) -> bool:
        """セッション終了"""
```

#### 2.2 Session Manager
**ファイル**: `src/worklog_mcp/claude_integration/session_manager.py`

```python
class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, AgentSession] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        
    async def create_agent_session(self, agent_id: str, user: User) -> str:
        """エージェント専用セッション作成"""
        
    async def get_session_status(self, session_id: str) -> SessionStatus:
        """セッション状態取得"""
        
    async def cleanup_inactive_sessions(self):
        """非アクティブセッションクリーンアップ"""
```

### 3. API Gateway

#### 3.1 Agent Selection Tools
**ファイル**: `src/worklog_mcp/tools/claude_agent_tools.py`

```python
def register_claude_agent_tools(mcp: FastMCP, db: Database, session_manager: SessionManager):
    
    @mcp.tool(
        name="start_claude_agent",
        description="指定したユーザーの人格設定でClaude Codeセッションを開始します。"
    )
    async def start_claude_agent(user_id: str, target_agent_id: str, ctx: Context) -> str:
        """エージェント選択してClaude Code開始"""
        
    @mcp.tool(
        name="execute_with_agent",
        description="指定したエージェントでコマンドを実行します。"
    )
    async def execute_with_agent(user_id: str, session_id: str, command: str, ctx: Context) -> str:
        """エージェントでコマンド実行"""
        
    @mcp.tool(
        name="list_agent_sessions",
        description="アクティブなエージェントセッション一覧を取得します。"
    )
    async def list_agent_sessions(user_id: str, ctx: Context) -> List[Dict[str, Any]]:
        """アクティブセッション一覧"""
```

## データモデル拡張

### 既存Userモデルの活用

```python
# src/worklog_mcp/models.py への追加

@dataclass
class AgentSession:
    session_id: str
    agent_id: str
    user_id: str
    claude_process_id: str
    workspace_path: str
    mcp_config_path: str
    status: SessionStatus
    created_at: datetime
    last_activity: datetime

@dataclass
class AgentExecutionResult:
    session_id: str
    command: str
    output: str
    error: Optional[str]
    execution_time: float
    timestamp: datetime

enum SessionStatus:
    STARTING = "starting"
    ACTIVE = "active"
    IDLE = "idle"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
```

### 設定マッピング

```python
# Userモデルの各フィールドをClaude Code設定へマッピング

USER_FIELD_MAPPING = {
    "personality": "system_prompt_personality",
    "appearance": "system_prompt_appearance", 
    "role": "system_prompt_role",
    "instruction": "system_prompt_custom",
    "model": "claude_model",
    "mcp": "mcp_servers_config",
    "tools": "allowed_tools"
}
```

## ディレクトリ構成

```
src/worklog_mcp/
├── claude_agents/              # 新規作成
│   ├── __init__.py
│   ├── user_config_converter.py
│   ├── personality_engine.py
│   ├── mcp_config_generator.py
│   └── templates/              # 設定テンプレート
│       ├── claude_settings_template.json
│       ├── mcp_config_template.json
│       └── personality_prompts.yaml
├── claude_integration/         # 新規作成
│   ├── __init__.py
│   ├── claude_executor.py
│   ├── session_manager.py
│   ├── process_isolation.py
│   └── monitoring.py
├── tools/                      # 既存拡張
│   ├── claude_agent_tools.py   # 新規追加
│   └── user_management.py      # 既存
├── models.py                   # 既存拡張
├── database.py                 # 既存拡張 
└── ...

scripts/                        # 既存拡張
├── start-claude-agent.sh       # 新規追加
├── claude-agent-manager.sh     # 新規追加
├── test-agent-personality.sh   # 新規追加
└── ...

config/                         # 新規作成
├── agent_templates/
│   ├── developer_template.json
│   ├── designer_template.json
│   └── manager_template.json
└── claude_environments/        # エージェント別環境設定
```

## 実装ステップ

### Phase 1: 基盤構築 (Week 1-2)
1. Agent Configuration Manager実装
2. 基本的なユーザー設定→Claude設定変換機能
3. 単体エージェント実行環境構築

### Phase 2: 人格エンジン (Week 3-4)
1. Personality Engine実装
2. システムプロンプト生成ロジック
3. 人格一貫性保持機能

### Phase 3: セッション管理 (Week 5-6)
1. Session Manager実装
2. マルチエージェント同時実行
3. プロセス分離とリソース管理

### Phase 4: API統合 (Week 7-8)
1. MCPツール追加
2. 既存webビューアーとの統合
3. ユーザーインターフェース拡張

### Phase 5: 運用機能 (Week 9-10)
1. 管理スクリプト作成
2. 監視・ログ機能
3. テスト・デバッグ機能

## 運用設計

### エージェント起動フロー

```bash
# 1. 特定エージェントでClaude Code起動
./scripts/start-claude-agent.sh [user_id] [project_path]

# 2. マルチエージェント管理
./scripts/claude-agent-manager.sh 
  --list                    # アクティブエージェント一覧
  --start [user_id]         # エージェント開始
  --stop [session_id]       # エージェント停止
  --status [session_id]     # ステータス確認

```

### 設定更新フロー

1. WebビューアーでユーザーのPersonality/Appearance/Instruction更新
2. 変更検知でエージェント設定再生成
3. アクティブセッションへの動的適用

### プロセス分離
- 各エージェントは専用プロセスで実行

## 拡張性

### 他のLLMサポート
- エグゼキューター抽象化により他LLM対応可能
- モデル固有最適化の分離

## まとめ

本アーキテクチャにより、既存のworklog MCPサーバーのユーザー設定を活用して、一貫した人格を持つClaude Codeエージェントシステムを構築できます。モジュラー設計により段階的実装が可能で、将来の機能拡張にも対応できる柔軟性を持ちます。