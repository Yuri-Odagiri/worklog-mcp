# 分報MCPサーバー

Model Context Protocol (MCP) を使用した分報管理サーバー + Webビューアー

## 概要

分報MCPサーバーは、リアルタイムの作業ログ（分報）の記録・管理・検索機能をAIアシスタントに提供するPythonパッケージです。`uvx`コマンドで簡単に起動でき、複数ユーザーの細かい作業記録を時系列で管理します。

**NEW**: 完全独立アーキテクチャ！MCPサーバーとWebビューアーが分離され、それぞれ個別起動可能になりました！

## 特徴

- 🚀 **簡単起動**: `uvx`コマンドで環境を汚さずに実行
- 🔧 **独立アーキテクチャ**: MCPサーバーとWebビューアーを個別または統合で起動可能
- 🌐 **Webビューアー**: ブラウザでのリアルタイム分報閲覧（独立起動対応）
- 🔄 **プロセス間通信**: SQLiteベースのイベントバスによる非同期通信
- 🏗️ **プロジェクト分離**: プロジェクト単位での完全なデータ分離
- 👥 **マルチユーザー対応**: チームメンバーの分報を統合管理
- 🎨 **AI生成アバター**: OpenAI GPT-5による個性的なアバター自動生成（リアルタイム更新対応）
- 🔍 **高機能検索**: キーワード、日付、ユーザー別の柔軟な検索
- 🧵 **スレッド機能**: 分報に対する返信・続報の記録
- 📊 **統計・サマリー**: 作業状況の自動分析とレポート生成
- 💾 **ローカル保存**: SQLiteによる安全なローカルデータ管理
- ⚡ **リアルタイム更新**: Server-Sent EventsによるWebUI即座更新

## インストールと起動

### 起動方法の選択

分報MCPサーバーは3つの方法で起動できます：

1. **MCPサーバーのみ**: Claude Desktop等からMCP経由でのみ利用
2. **Webビューアーのみ**: ブラウザでの閲覧専用
3. **統合起動**: MCPサーバーとWebビューアーを同時起動（推奨）

### 方法1: 開発モード（最も簡単）

パッケージ化不要で、すぐに使用開始できます：

```bash
# リポジトリのクローン
git clone <repository-url>
cd worklog-mcp

# 依存関係のインストール
uv sync

# === 起動方法の選択 ===

# 1. MCPサーバーのみ起動
uv run python -m worklog_mcp.mcp_server --project .

# 2. Webビューアーのみ起動
uv run python -m worklog_mcp.web_server --project . --port 8080

# 3. 統合起動（推奨）
uv run python -m worklog_mcp --project . --web-port 8080
```

### 方法2: uvxでの実行（配布用）

`uvx`は単一パッケージの実行に特化したツールです：

```bash
# === PyPI公開後の実行 ===

# 1. MCPサーバーのみ
uvx worklog-mcp.mcp_server --project .

# 2. Webビューアーのみ
uvx worklog-mcp.web_server --project . --port 8080

# 3. 統合起動
uvx worklog-mcp --project . --web-port 8080

# === ローカルパッケージでの実行 ===
uvx /path/to/worklog-mcp/dist/worklog_mcp-0.1.0-py3-none-any.whl

# === Git リポジトリから直接実行 ===
uvx --from git+https://github.com/Yuri-Odagiri/worklog-mcp.git worklog-mcp
```

**uvx vs uv の違い:**
- `uv run`: プロジェクト環境でスクリプト実行（開発・個人利用）
- `uvx`: パッケージを一時環境で実行（配布・共有用）

## 環境変数設定

### AI生成アバター機能

ユーザー登録時にOpenAI GPT-5を使用してパーソナライズされたアバター画像を生成できます。

#### OpenAI API設定

```bash
# OpenAI APIキーを設定（AI生成アバター用）
export OPENAI_API_KEY="your-openai-api-key-here"

# 設定確認
echo $OPENAI_API_KEY
```

**Windows（PowerShell）:**
```powershell
# 環境変数設定
$env:OPENAI_API_KEY = "your-openai-api-key-here"

# 設定確認
echo $env:OPENAI_API_KEY
```

**Windows（コマンドプロンプト）:**
```cmd
rem 環境変数設定
set OPENAI_API_KEY=your-openai-api-key-here

rem 設定確認
echo %OPENAI_API_KEY%
```

#### アバター生成の動作

- **即座表示**: 登録時にテーマカラーのグラデーション画像を即座に表示
- **AI生成（バックグラウンド）**: OpenAI GPT-5がユーザー情報を基にオリジナルアバターを生成
- **自動更新**: AI生成完了時に表示中のアバターが自動的にリアルタイム更新
- **キャッシュ対応**: 異なるファイル名により、ブラウザキャッシュ問題を完全回避
- **API未設定時**: グラデーション画像がそのまま使用される

### データベース保存場所

```bash
# カスタムベースパス（オプション）
export WORKLOG_BASE_PATH="/custom/path"

# デフォルト: ~/.worklog
```

データは `WORKLOG_BASE_PATH` 以下にプロジェクト名で分離して保存されます。

### Claude Desktop設定での環境変数

```json
{
  "mcpServers": {
    "worklog-project": {
      "command": "uv",
      "args": ["run", "python", "-m", "worklog_mcp", "--project", "/path/to/project"],
      "cwd": "/absolute/path/to/worklog-mcp",
      "env": {
        "WORKLOG_BASE_PATH": "~/.worklog",
        "OPENAI_API_KEY": "your-openai-api-key-here"
      }
    }
  }
}
```

**注意事項:**
- OpenAI APIキーは有料サービスです。使用量に応じて課金されます
- APIキーが未設定でも基本機能は正常に動作します（グラデーションアバター使用）
- セキュリティのため、APIキーを公開リポジトリにコミットしないよう注意してください

## 新アーキテクチャ: 独立起動システム

### アーキテクチャの特徴

分報MCPサーバーは完全に独立したアーキテクチャに進化しました：

- **MCPサーバー**: Claude Desktop等からのMCP通信専用
- **Webビューアー**: ブラウザでの閲覧・操作専用  
- **イベントバス**: SQLiteベースでプロセス間通信
- **統合起動**: 便利用として両方を自動起動

### プロセス間通信

```
MCPサーバー → イベントバス → Webビューアー → ブラウザ
     ↓              ↓              ↓           ↓
 分報投稿      SQLiteイベント    SSE通知   リアルタイム更新
```

### Webビューアー機能

#### アクセス方法

Webビューアー起動後、以下のURLでアクセス可能：

- **Webビューアー**: `http://localhost:8080`
- **REST API**: `http://localhost:8080/api/*`
- **SSEストリーム**: `http://localhost:8080/events`

#### 主な機能

- **リアルタイム更新**: MCP経由の投稿が即座にWebUIに反映
- **アバター自動更新**: AI生成完了時に表示中のアバターが自動切り替え
- **検索機能**: キーワード検索とリアルタイムフィルタリング
- **レスポンシブデザイン**: モバイル端末でも快適な表示
- **キーボードショートカット**: 
  - `Ctrl+R` / `Cmd+R`: 更新
  - `Ctrl+F` / `Cmd+F`: 検索欄にフォーカス

#### 起動例

```bash
# === 個別起動 ===

# MCPサーバーのみ（バックグラウンド）
uv run python -m worklog_mcp.mcp_server --project . &

# Webビューアーのみ
uv run python -m worklog_mcp.web_server --project . --port 8080

# === 統合起動（推奨） ===
uv run python -m worklog_mcp --project . --web-port 8080
```

## プロジェクト分離機能

### プロジェクト単位での分報管理

各プロジェクトで独立した分報データを管理できます：

```bash
# プロジェクトAの分報
uvx worklog-mcp --project /path/to/project-a

# プロジェクトBの分報（完全に分離される）  
uvx worklog-mcp --project /path/to/project-b

# 現在のディレクトリをプロジェクトとして使用（--project未指定時）
cd /path/to/my-project
uvx worklog-mcp
```

### データ分離の仕組み

- **データベース**: `{WORKLOG_BASE_PATH}/{project_name}/database/worklog.db`
- **アバター画像**: `{WORKLOG_BASE_PATH}/{project_name}/avatar/{user_id}.png` 
- **イベントバス**: `{WORKLOG_BASE_PATH}/{project_name}/events/event_bus.db`
- **プロジェクト名**: `--project`で指定したパス（未指定時は現在のディレクトリ）から自動生成

## Claude Desktop での設定

### MCP設定（推奨）

Claude DesktopでMCPサーバーとして利用する場合：

#### 方法1: Claude Code (推奨)

```bash
# MCPサーバーのみ（通常の使用方法）
claude mcp add worklog-project -s project -- uv run python -m worklog_mcp.mcp_server --project .

# 現在のディレクトリをプロジェクトとして追加
cd /path/to/your-project
claude mcp add worklog-current -s project -- uv run python -m worklog_mcp.mcp_server

# Gitリポジトリから直接追加
claude mcp add worklog -s project -- uvx --from git+https://github.com/Yuri-Odagiri/worklog-mcp.git worklog-mcp.mcp_server
```

#### 方法2: 手動設定（開発モード）

開発環境から直接実行する場合：

```json
{
  "mcpServers": {
    "worklog-project-a": {
      "command": "uv",
      "args": ["run", "python", "-m", "worklog_mcp.mcp_server", "--project", "/path/to/project-a"],
      "cwd": "/absolute/path/to/worklog-mcp"
    },
    "worklog-project-b": {
      "command": "uv", 
      "args": ["run", "python", "-m", "worklog_mcp.mcp_server", "--project", "/path/to/project-b"],
      "cwd": "/absolute/path/to/worklog-mcp"
    }
  }
}
```

**注意**: 
- MCPサーバーは`worklog_mcp.mcp_server`を使用（Webビューアーは含まれません）
- `cwd`は`worklog-mcp`プロジェクトディレクトリの絶対パス
- `--project`引数でプロジェクトディレクトリを指定
- 複数プロジェクトで完全にデータが分離される

### Webビューアーの起動

Claude Desktop設定とは別に、Webビューアーを起動：

```bash
# === Webビューアーのみ起動 ===
cd /path/to/project-a
uv run python -m worklog_mcp.web_server --project . --port 8080

# === 統合起動（MCPサーバー + Webビューアー） ===
uv run python -m worklog_mcp --project . --web-port 8080

# ブラウザでアクセス
open http://localhost:8080
```

**使い分け:**
- **MCPサーバーのみ**: Claude Desktop経由でのみ利用
- **Webビューアーのみ**: ブラウザでの閲覧専用（データは既存のものを参照）
- **統合起動**: MCPとWebの両方が必要な場合

### 方法3: ローカルパッケージでの実行

ローカルでビルドしたパッケージを使用する場合：

```json
{
  "mcpServers": {
    "worklog-project-a": {
      "command": "uvx",
      "args": ["/absolute/path/to/worklog-mcp/dist/worklog_mcp-0.1.0-py3-none-any.whl", "mcp_server", "--project", "/path/to/project-a"]
    }
  }
}
```

**注意**: パスは絶対パスで指定してください。例：
- Windows: `C:/Users/username/dev/worklog-mcp/dist/worklog_mcp-0.1.0-py3-none-any.whl`
- macOS/Linux: `/home/username/dev/worklog-mcp/dist/worklog_mcp-0.1.0-py3-none-any.whl`

### 方法4: Gitリポジトリから直接実行

公開されたGitリポジトリから直接実行：

```json
{
  "mcpServers": {
    "worklog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Yuri-Odagiri/worklog-mcp.git", "worklog-mcp", "mcp_server", "--project", "."]
    }
  }
}
```


### 方法5: PyPI公開後

PyPI公開後の実行：

```json
{
  "mcpServers": {
    "worklog": {
      "command": "uvx",
      "args": ["worklog-mcp", "mcp_server", "--project", "."]
    }
  }
}
```

## 使用方法

### 1. プロジェクト設定（推奨）

プロジェクトディレクトリで設定ファイルを作成：

```bash
# プロジェクトディレクトリで実行
cd /path/to/your-project

# Claude Desktop経由で設定ファイル作成
init_project_config project_name="my-project" description="プロジェクトの説明"
```

### 2. 初回起動とユーザー登録

初回起動時には必ずユーザー登録が必要です。登録時にAI生成またはテーマカラーのアバター画像が自動生成されます：

```
register_user "my-user-id" "山田太郎" Blue "チームリーダー" "責任感が強く、チームを引っ張る性格です。" "凛とした佇まいで、頼りになる雰囲気を持っています。"
```

**アバター生成について:**
- 性格・外見情報を詳細に入力すると、より個性的なAIアバターが生成されます
- 登録直後：テーマカラーのグラデーション画像が即座に表示（`{user_id}_gradient.png`）
- バックグラウンド処理：OpenAI GPT-5がオリジナルアバターを生成（`{user_id}_ai.png`）
- 自動切り替え：AI生成完了時に表示中のアバターがリアルタイム更新
- ファイル保存先：`~/.worklog/{project_name}/avatar/` ディレクトリ
- キャッシュ問題：異なるファイル名により、ブラウザキャッシュ問題を回避

### 3. 基本的な分報投稿

```
post_worklog "my-user-id" "## 作業
- API実装開始  
- エンドポイント設計完了

## 感想
コーヒー美味しい。今日は調子良さそう

## 困りごと  
JWTトークンの有効期限設定がうまくいかない"
```

### 4. 主要な機能

#### 分報の投稿・管理
- `post_worklog`: 新しい分報を投稿
- `reply_worklog`: 既存分報への返信

#### タイムライン・検索
- `read_timeline`: 時系列での分報表示
- `search_worklogs`: キーワード検索
- `read_worklog_thread`: スレッド表示
- `read_user_worklogs`: 特定ユーザーの分報取得

#### チーム管理
- `list_users`: 登録ユーザー一覧
- `get_team_status`: チーム全体の状況

#### 分析・統計
- `generate_worklog_summary`: 期間別サマリー生成
- `get_user_stats`: ユーザー別統計情報

## データ保存場所

### ディレクトリ構造
```
{WORKLOG_BASE_PATH}/             # デフォルト: ~/.worklog
├── {project_name}/
│   ├── database/
│   │   └── worklog.db          # SQLiteデータベース
│   ├── events/
│   │   └── event_bus.db        # イベントバス（プロセス間通信）
│   └── avatar/
│       ├── {user_id}_gradient.png  # グラデーションアバター（即座表示）
│       ├── {user_id}_ai.png        # AI生成アバター（バックグラウンド生成）
│       └── ...
└── ...
```

### 保存パス
- **データベース**: `{WORKLOG_BASE_PATH}/{project_name}/database/worklog.db`
- **イベントバス**: `{WORKLOG_BASE_PATH}/{project_name}/events/event_bus.db`
- **アバター画像**: `{WORKLOG_BASE_PATH}/{project_name}/avatar/` ディレクトリ
  - グラデーション: `{user_id}_gradient.png`（登録時即座生成）
  - AI生成: `{user_id}_ai.png`（バックグラウンド生成、自動切り替え）
- **デフォルトベースパス**: `~/.worklog`（WORKLOG_BASE_PATH未設定時）

### 環境変数での設定
```bash
# カスタムベースパスを指定
export WORKLOG_BASE_PATH="/custom/path"
# → /custom/path/{project_name}/database/worklog.db
```


## データ形式

### 分報エントリー

```json
{
  "id": "unique-entry-id",
  "user_id": "user-id",
  "user_name": "表示名",
  "markdown_content": "## 作業\n- タスク1\n- タスク2",
  "related_entry_id": null,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00"
}
```

### タイムライン取得例

```bash
# 過去24時間の全ユーザーの分報
read_timeline "my-user-id"

# 過去8時間の分報
read_timeline "my-user-id" hours=8

# 最新20件の分報
read_timeline "my-user-id" count=20

# 特定ユーザーの分報
read_timeline "my-user-id" target_user_id="other-user-id"
```

## 開発・テスト

### データベーススクリプト

プロジェクト用のデータベース初期化・ダミーデータ投入スクリプトが利用可能です：

```bash
# データベース初期化
uv run python scripts/init_db.py --project worklog-mcp

# 既存DBを強制削除して再作成
uv run python scripts/init_db.py --project worklog-mcp --force

# ダミーデータ投入（デフォルト: 7日間、10エントリー/日/ユーザー）
uv run python scripts/seed_dummy_data.py --project worklog-mcp

# カスタム設定でダミーデータ投入
uv run python scripts/seed_dummy_data.py --project worklog-mcp --days 14 --entries-per-day 15

# ヘルプ表示
uv run python scripts/init_db.py --help
uv run python scripts/seed_dummy_data.py --help
```

#### ダミーデータ内容
- **ユーザー**: 田中太郎、山田花子、佐藤次郎、鈴木美咲、高橋健一（5名）
- **分報内容**: 作業開始、技術調査、バグ修正、ミーティング、休憩、振り返り等のリアルな分報
- **スレッド機能**: 10%確率で他ユーザーの分報に返信
- **統計情報**: 投入完了時にユーザー別統計を表示

### テストの実行

```bash
# 全テストの実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=worklog_mcp

# 特定テストファイルの実行
uv run pytest tests/test_database.py
```

### コード品質チェック

```bash
# Ruffによるコードチェック
uv run ruff check src/

# コードフォーマット
uv run ruff format src/
```

### MCPインスペクターでのテスト

```bash
# === MCPサーバー単体テスト ===

# 開発版でのテスト
npx @modelcontextprotocol/inspector uv run python -m worklog_mcp.mcp_server --project .

# パッケージ版でのテスト（PyPI公開後）
npx @modelcontextprotocol/inspector uvx worklog-mcp mcp_server --project .
```

### Webサーバーのテスト

```bash
# === Webビューアー単体テスト ===

# Webビューアーのみ起動
uv run python -m worklog_mcp.web_server --project . --port 8080

# === 統合テスト ===

# 統合サーバー起動
uv run python -m worklog_mcp --project . --web-port 8080

# === API疎通確認 ===

# 基本API確認
curl http://localhost:8080/api/entries

# SSE接続テスト
curl -N http://localhost:8080/events

# イベントバス確認（プロセス間通信テスト）
# - MCPサーバーで分報投稿
# - Webビューアーでリアルタイム更新を確認
```

## 技術仕様

### バックエンド
- **言語**: Python 3.10+
- **プロトコル**: Model Context Protocol (MCP)
- **データベース**: SQLite (aiosqlite)
- **非同期処理**: asyncio
- **パッケージマネージャー**: uv
- **AI画像生成**: OpenAI GPT-5 Image Generation Tools
- **画像処理**: Pillow (PIL)

### Webサーバー
- **フレームワーク**: FastAPI
- **サーバー**: uvicorn  
- **リアルタイム通信**: Server-Sent Events (SSE)
- **静的ファイル**: HTML/CSS/JavaScript (Vanilla)

### 新アーキテクチャ
- **独立プロセス**: MCPサーバーとWebビューアーが完全分離
- **プロセス間通信**: SQLiteベースのイベントバス
- **通知システム**: MCP投稿 → イベントバス → SSE → Webクライアント即座更新
- **統合起動**: 便利用として両プロセスを自動管理

## API仕様

### プロジェクト管理ツール

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `init_project_config` | 設定ファイル作成 | `project_name?`, `description?` |

### 必須ツール

| ツール名 | 説明 | 必須パラメータ |
|---------|------|---------------|
| `register_user` | ユーザー登録（初回必須・AI生成アバター付き） | `user_id`, `name`, `theme_color`(Red/Blue/Green/Yellow/Purple/Orange/Pink/Cyan), `role`, `personality`, `appearance` |
| `post_worklog` | 分報投稿 | `user_id`, `markdown_content` |

### 管理ツール

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `reply_worklog` | 返信投稿 | `user_id`, `related_entry_id`, `markdown_content` |
| `read_worklog_thread` | スレッド表示 | `user_id`, `entry_id` |

### 検索・表示ツール

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `read_timeline` | タイムライン取得 | `user_id`, `target_user_id?`, `hours?`, `count?` |
| `search_worklogs` | 分報検索 | `user_id`, `keyword`, `target_user_id?`, `date_from?`, `date_to?` |
| `read_user_worklogs` | 特定ユーザーの分報取得 | `user_id`, `target_user_id`, `hours?` |

### 分析ツール

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `generate_worklog_summary` | サマリー生成 | `user_id`, `target_user_id?`, `hours?` |
| `get_user_stats` | 統計情報 | `user_id`, `target_user_id` |
| `get_team_status` | チーム状況 | `user_id` |
| `list_users` | ユーザー一覧 | `user_id` |

## セキュリティ

- **データプライバシー**: 全データはローカルに保存
- **ステートレス設計**: サーバー側でユーザー状態を保持しない
- **明示的認証**: 全ての操作で呼び出し元ユーザーIDが必須
- **入力検証**: SQLインジェクション対策、user_ID検証
- **マルチユーザー**: ユーザー間のデータ分離

## トラブルシューティング

### Claude Desktopで認識されない場合

1. **パスの確認**: 絶対パスで指定されているか確認
2. **パッケージの存在確認**: ファイルが実際に存在するか確認
3. **権限の確認**: ファイルに実行権限があるか確認
4. **ログの確認**: Claude Desktopのログでエラー内容を確認

### よくあるエラー

- **"Already running asyncio"**: 通常は無害。サーバーは正常に動作します
- **"ユーザーID 'xxx' が見つかりません"**: user_idが未登録。初回は`register_user`を実行
- **"user_idは英数字..."**: user_idは英数字、ハイフン、アンダースコアのみ使用可能
- **Webサーバー接続エラー**: ポートが使用中の場合は`--web-port`で別ポートを指定

### デバッグ方法

```bash
# === 個別デバッグ ===

# MCPサーバーのみでテスト
uv run python -m worklog_mcp.mcp_server --project .

# Webビューアーのみでテスト
uv run python -m worklog_mcp.web_server --project . --port 8080

# === 統合デバッグ ===

# 統合サーバーでテスト
uv run python -m worklog_mcp --project . --web-port 8080

# === MCP機能デバッグ ===

# MCPインスペクターでテスト
npx @modelcontextprotocol/inspector uv run python -m worklog_mcp.mcp_server --project .

# === Web機能デバッグ ===

# API疎通確認
curl -v http://localhost:8080/api/entries

# イベントバス動作確認
# 1. MCPサーバーとWebビューアーを個別起動
# 2. MCPから分報投稿
# 3. Webでリアルタイム更新確認
```

## ライセンス

MIT License

## 貢献

プルリクエストや課題報告をお待ちしています。

---

分報MCPサーバーで、チームの情報共有を効率化しましょう！