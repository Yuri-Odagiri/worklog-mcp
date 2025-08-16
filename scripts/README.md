# worklog-mcp 管理スクリプト

プロセス管理を簡単にするためのスクリプト集です。

## 📁 スクリプト一覧

### 🚀 起動スクリプト

- **`start-all.sh`** - MCPサーバーとWebビューアーの両方を起動
- **`start-mcp.sh`** - Streamable HTTP MCPサーバーのみ起動
- **`start-web.sh`** - Webビューアーのみ起動

### 🛑 停止スクリプト

- **`stop-all.sh`** - 全worklog-mcpプロセスを停止
- **`stop-mcp.sh`** - MCPサーバーのみ停止
- **`stop-web.sh`** - Webビューアーのみ停止

### 📊 状態確認スクリプト

- **`status.sh`** - プロセス状態・リソース使用量・エンドポイント接続確認

## 🔧 使用方法

### 基本的な使用方法

```bash
# プロジェクトルートから実行
cd /mnt/c/Users/ixixi/dev/worklog-mcp

# 統合サーバー起動（推奨）
./scripts/start-all.sh /path/to/your/project

# 状態確認
./scripts/status.sh

# 全停止
./scripts/stop-all.sh
```

### 個別起動

```bash
# MCPサーバーのみ起動
./scripts/start-mcp.sh [プロジェクトパス]

# Webビューアーのみ起動
./scripts/start-web.sh [プロジェクトパス] [ポート番号]

# 個別停止
./scripts/stop-mcp.sh
./scripts/stop-web.sh
```

### パラメータ指定

```bash
# カスタムプロジェクトパスで起動
./scripts/start-all.sh /path/to/your/project

# カスタムプロジェクトパスとポートで起動
./scripts/start-all.sh /path/to/your/project 8090

# MCPサーバーのみカスタムプロジェクトで起動
./scripts/start-mcp.sh /path/to/your/project

# Webビューアーのみカスタム設定で起動
./scripts/start-web.sh /path/to/your/project 8090
```

## 📊 デフォルト設定

- **プロジェクトパス**: 必須（引数で指定）
- **Webポート**: `8080`
- **MCPポート**: `8001` (固定)
- **ログディレクトリ**: `/tmp`

## 🌐 アクセスURL

- **Webビューアー**: http://localhost:8080
- **MCP エンドポイント**: http://127.0.0.1:8001/mcp

## 📝 ログファイル

- **MCPサーバー**: `/tmp/worklog-mcp-server.log`
- **Webビューアー**: `/tmp/worklog-web-viewer.log`

```bash
# ログをリアルタイムで確認
tail -f /tmp/worklog-mcp-server.log
tail -f /tmp/worklog-web-viewer.log

# 両方同時に確認
tail -f /tmp/worklog-mcp-server.log /tmp/worklog-web-viewer.log
```

## 🔍 プロセス確認

```bash
# 詳細な状態確認（推奨）
./scripts/status.sh

# 手動でのプロセス確認
ps aux | grep worklog_mcp | grep -v grep

# ポート使用状況確認
lsof -i :8001  # MCPサーバー
lsof -i :8080  # Webビューアー
```

### 📊 status.sh が提供する情報

- **プロセス状態**: PID、CPU/メモリ使用量、起動時間
- **エンドポイント確認**: MCP/Web接続テスト
- **プロジェクト情報**: 使用中のプロジェクトパス
- **リソース状況**: 総使用量とポート状態  
- **ログファイル**: サイズと更新時刻
- **データベース**: worklog.db、eventbus.db、アバター状況
- **管理コマンド**: 起動・停止・確認方法

## ⚠️ トラブルシューティング

### プロセスが残存している場合

```bash
# 強制停止
./scripts/stop-all.sh

# 個別強制停止
pkill -f "worklog_mcp"
```

### ポートが使用中の場合

```bash
# ポート使用プロセスを確認
lsof -i :8080
lsof -i :8001

# 特定プロセスを停止
kill [PID]
```

### 起動に失敗する場合

1. ログファイルを確認
2. プロジェクトパスが正しいか確認
3. 依存関係が正しくインストールされているか確認

```bash
# 依存関係の確認・再インストール
uv sync
```

## 🎯 よくある使用パターン

### 開発時の起動・停止

```bash
# 開発開始
./scripts/start-all.sh /path/to/your/project

# 状態確認
./scripts/status.sh

# 設定変更後の再起動
./scripts/stop-all.sh
./scripts/start-all.sh /path/to/your/project

# 開発終了
./scripts/stop-all.sh
```

### Claude Code用のMCPサーバーのみ

```bash
# ローカルサーバー使用（既存を使い回し）
./scripts/claude-mcp.sh /path/to/your/project

# ローカルサーバー強制再起動
./scripts/claude-mcp.sh --force /path/to/your/project

# リモートサーバー指定
./scripts/claude-mcp.sh --url http://remote-server:8001/mcp /path/to/your/project

# 状態確認
./scripts/status.sh

# 停止
./scripts/stop-mcp.sh
```

### Webビューアーのみ

```bash
# Webビューアーのみ起動（MCPサーバーは別途起動済みの場合）
./scripts/start-web.sh /path/to/your/project

# 状態確認
./scripts/status.sh

# 停止
./scripts/stop-web.sh
```