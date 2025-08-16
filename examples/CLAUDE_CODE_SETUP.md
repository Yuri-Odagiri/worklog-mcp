# Claude Code での worklog-mcp 設定方法

## 🔧 設定手順

### 1. プロジェクトディレクトリで `.mcp.json` を作成

```bash
cd /path/to/your/project
```

### 2. `.mcp.json` に以下の設定を追加

```json
{
  "mcpServers": {
    "worklog": {
      "type": "http",
      "url": "http://127.0.0.1:8001/mcp",
      "command": "./scripts/claude-mcp.sh",
      "args": [
        "/path/to/your/project"
      ],
      "cwd": "/mnt/c/Users/ixixi/dev/worklog-mcp",
      "env": {
        "WORKLOG_BASE_PATH": "~/.worklog"
      }
    }
  }
}
```

### 3. パラメータ設定

| パラメータ | 説明 | 設定例 |
|-----------|------|--------|
| `args[0]` | プロジェクトパス | `/mnt/c/Users/ixixi/dev/simpleapp` |
| `cwd` | worklog-mcpのパス | `/mnt/c/Users/ixixi/dev/worklog-mcp` |
| `WORKLOG_BASE_PATH` | データベースベースパス | `~/.worklog` |

## 🚀 使用方法

### Claude Code起動
```bash
cd /path/to/your/project
claude
```

### 利用可能なツール
- `post_worklog` - 分報投稿
- `search_worklogs` - 分報検索  
- `get_worklog_summary` - サマリー取得
- `delete_worklog` - 分報削除

## 📊 動作確認

```bash
# MCPサーバーの状態確認
ps aux | grep worklog_mcp | grep -v grep

# ログの確認
tail -f /tmp/worklog-mcp-claude.log

# エンドポイントのテスト
curl http://127.0.0.1:8001/mcp
```

## 🔧 トラブルシューティング

### MCPサーバーが起動しない場合

1. **依存関係確認**
```bash
cd /mnt/c/Users/ixixi/dev/worklog-mcp
uv sync
```

2. **手動起動テスト**
```bash
./scripts/start-mcp.sh /path/to/your/project
```

3. **ログ確認**
```bash
tail -f /tmp/worklog-mcp-claude.log
```

### プロセスが重複している場合

```bash
# 全停止
cd /mnt/c/Users/ixixi/dev/worklog-mcp
./scripts/stop-all.sh

# Claude Code再起動
```

### ポートが使用中の場合

```bash
# ポート8001の使用状況確認
lsof -i :8001

# 占有プロセスを停止
kill [PID]
```

## 📁 ファイル構成

```
your-project/
├── .mcp.json          # Claude Code設定
└── .worklog/          # 自動生成されるデータディレクトリ
    ├── worklog.db     # 分報データベース
    ├── eventbus.db    # イベントバス
    └── avatar/        # アバター画像
```

## 🌐 Webビューアーとの併用

MCPサーバーとは独立してWebビューアーも利用可能：

```bash
# Webビューアーを起動
cd /mnt/c/Users/ixixi/dev/worklog-mcp
./scripts/start-web.sh /path/to/your/project

# アクセス
open http://localhost:8080
```

## ⚙️ 高度な設定

### カスタム環境変数

```json
"env": {
  "WORKLOG_BASE_PATH": "~/.worklog",
  "LOG_LEVEL": "DEBUG",
  "MCP_PORT": "8001"
}
```

### 複数プロジェクト対応

```json
{
  "mcpServers": {
    "worklog-project1": {
      "type": "http",
      "url": "http://127.0.0.1:8001/mcp",
      "command": "./scripts/claude-mcp.sh",
      "args": ["/path/to/project1"],
      "cwd": "/mnt/c/Users/ixixi/dev/worklog-mcp"
    },
    "worklog-project2": {
      "type": "http", 
      "url": "http://127.0.0.1:8002/mcp",
      "command": "./scripts/claude-mcp.sh",
      "args": ["/path/to/project2"],
      "cwd": "/mnt/c/Users/ixixi/dev/worklog-mcp"
    }
  }
}
```

> **注意**: 複数プロジェクトの場合は、ポート番号を変更する必要があります。