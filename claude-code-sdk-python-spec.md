# Claude Code SDK Python仕様詳細調査

## 概要

Claude Code SDK Pythonは、Anthropic社が提供する公式のPython SDKで、Claude CodeのAIコーディング機能をプログラムから利用するためのライブラリです。

## インストール

### 必要条件
- Python 3.10以上
- Node.js（Claude Code CLIが必要）

### インストール手順

```bash
# Claude Code SDK Pythonをインストール
pip install claude-code-sdk

# 必須依存関係（Claude Code CLI）もインストール
npm install -g @anthropic-ai/claude-code
```

## 基本的な使用方法

### シンプルなクエリ

```python
import anyio
from claude_code_sdk import query

async def main():
    async for message in query(prompt="What is 2 + 2?"):
        print(message)

anyio.run(main)
```

### メッセージ処理

```python
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, TextBlock

# シンプルなクエリでテキストブロックを処理
async for message in query(prompt="Hello Claude"):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)
```

## 設定オプション

### ClaudeCodeOptionsを使用した設定

```python
from claude_code_sdk import query, ClaudeCodeOptions

options = ClaudeCodeOptions(
    system_prompt="You are a helpful assistant",
    max_turns=1
)

async for message in query(prompt="Tell me a joke", options=options):
    print(message)
```

### ツール使用の設定

```python
from claude_code_sdk import query, ClaudeCodeOptions

options = ClaudeCodeOptions(
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode='acceptEdits'  # ファイル編集を自動承認
)

async for message in query(
    prompt="Create a hello.py file", 
    options=options
):
    # ツール使用と結果を処理
    pass
```

### 作業ディレクトリの設定

```python
from pathlib import Path
from claude_code_sdk import ClaudeCodeOptions

options = ClaudeCodeOptions(
    cwd="/path/to/project"  # または Path("/path/to/project")
)
```

## エラーハンドリング

### SDKの例外処理

```python
from claude_code_sdk import (
    ClaudeSDKError,      # ベースエラー
    CLINotFoundError,    # Claude Code未インストール
    CLIConnectionError,  # 接続問題
    ProcessError,        # プロセス失敗
    CLIJSONDecodeError,  # JSON解析問題
)

try:
    async for message in query(prompt="Hello"):
        pass
except CLINotFoundError:
    print("Please install Claude Code")
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
except CLIJSONDecodeError as e:
    print(f"Failed to parse response: {e}")
```

## 開発環境設定

### 仮想環境セットアップ

```bash
# 仮想環境作成
python -m venv claude-env

# 仮想環境有効化
# macOS/Linux:
source claude-env/bin/activate
# Windows:
claude-env\Scripts\activate

# SDKインストール
pip install claude-code-sdk
```

### 環境変数設定

```bash
# Anthropic API キーを設定
export ANTHROPIC_API_KEY='your-api-key-here'
```

## コード品質管理

### 開発時の必須コマンド

```bash
# コードリント・フォーマット
python -m ruff check src/ tests/ --fix
python -m ruff format src/ tests/

# 型チェック
python -m mypy src/

# テスト実行
python -m pytest tests/

# 特定のテストファイル実行
python -m pytest tests/test_client.py
```

## API認証方法

### 1. Anthropic API認証
- Anthropic Consoleアカウントが必要
- APIキーまたはConsoleクレデンシャル使用

### 2. サードパーティ認証
- 他のサービスとの統合用

## 主な機能

### 1. マルチターン会話
- 継続的な対話セッション管理
- コンテキスト保持

### 2. カスタムシステムプロンプト
- 特定の役割や動作指定

### 3. プランモード
- 構造化されたタスク実行

### 4. カスタムツール (MCP)
- Message Content Processing経由

### 5. 出力形式サポート
- Text、JSON、Streaming JSON

### 6. 入力形式サポート
- Text、Streaming JSON

## 使用例: ファイル操作

```python
from claude_code_sdk import query, ClaudeCodeOptions

async def create_project_files():
    options = ClaudeCodeOptions(
        allowed_tools=["Write", "Read", "LS"],
        permission_mode='acceptEdits',
        cwd="./my_project"
    )
    
    async for message in query(
        prompt="Create a Python project structure with main.py, requirements.txt, and README.md",
        options=options
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
```

## Claude Code CLI コマンド

### 基本コマンド

```bash
# インタラクティブセッション開始
claude

# 一回限りのタスク実行
claude "fix the build error"

# クエリ実行して終了
claude -p "explain this function"

# 最新の会話継続
claude -c

# 前の会話セッション再開
claude -r

# Git コミット作成
claude commit

# ヘルプ表示
claude --help

# バージョン確認
claude --version

# アップデート
claude update

# MCP設定
claude mcp
```

### インストール方法

```bash
# NPM経由（推奨）
npm install -g @anthropic-ai/claude-code

# ネイティブバイナリ（macOS、Linux、WSL）
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex
```

### システム要件

- **OS**: macOS 10.15+、Ubuntu 20.04+/Debian 10+、Windows 10+（WSL 1/2またはGit for Windows）
- **ハードウェア**: 4GB以上のRAM
- **ソフトウェア**: Node.js 18+
- **ネットワーク**: インターネット接続必須（認証とAI処理用）
- **シェル**: Bash、Zsh、Fish推奨
- **地域**: Anthropic対応国

## 制限事項

1. **Python 3.10以上必須** - 古いバージョンは非対応
2. **Node.js依存** - Claude Code CLIが必要
3. **ネットワーク接続必須** - 認証とAI処理用
4. **地域制限** - Anthropic対応国のみ

## トラブルシューティング

### よくある問題

1. **CLIが見つからない**
```bash
npm install -g @anthropic-ai/claude-code
claude --version  # インストール確認
```

2. **認証エラー**
```bash
claude login  # Claude認証
```

3. **権限エラー**
```python
# 適切なツール権限設定
options = ClaudeCodeOptions(
    allowed_tools=["Read", "Write"],
    permission_mode='acceptEdits'
)
```

4. **WSLでのNode未検出エラー**
```bash
which npm
which node
# Node.jsをLinuxパッケージマネージャまたはnvm経由でインストール
```

5. **OS/プラットフォーム検出問題（WSL）**
```bash
npm config set os linux
npm install -g @anthropic-ai/claude-code --force --no-os-check
```

## Claude Code機能

### ファイル操作
- プロジェクトファイルの読み取り・書き込み・編集
- ディレクトリ構造の作成・管理
- Git操作（コミット、ブランチ作成、マージ競合解決）

### コード分析
- コードベース理解・説明
- アーキテクチャ分析・改善提案
- バグ検出・修正
- リファクタリング支援

### 開発支援
- テストコード作成
- ドキュメント生成・更新
- CI/CD統合
- パッケージ管理

### 対話機能
- 自然言語でのタスク指示
- コンテキスト保持
- プロジェクト固有の設定記憶

## 推奨されるベストプラクティス

1. **エラーハンドリング実装** - 全てのクエリでtry-catch使用
2. **適切なツール権限設定** - 必要最小限の権限のみ許可
3. **コンテキスト管理** - 長いセッションでのメモリ使用量注意
4. **テスト環境分離** - 本番とテストで異なる設定使用
5. **セキュリティ考慮** - 機密情報の取り扱い注意
6. **バージョン管理** - 定期的なSDK・CLI更新

## まとめ

Claude Code SDK Pythonは、PythonアプリケーションにClaude Codeの強力なAIコーディング機能を統合するための包括的なソリューションです。適切な設定とエラーハンドリングにより、堅牢なAI支援開発環境を構築できます。

非同期処理ベースの設計により、大規模なコードベースでも効率的に動作し、豊富なツール機能とカスタマイズオプションにより、様々な開発ワークフローに対応できます。