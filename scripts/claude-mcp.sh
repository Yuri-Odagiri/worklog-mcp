#!/bin/bash
# Claude Code専用のMCPサーバー起動スクリプト
# - プロセス重複チェックと自動停止
# - ログ出力を最小化
# - バックグラウンド実行でプロンプトブロックを回避

if [ -z "$1" ]; then
    echo "エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 <プロジェクトパス>"
    exit 1
fi

PROJECT_PATH="$1"
LOG_FILE="/tmp/worklog-mcp-claude.log"

# 既存のMCPサーバープロセスをチェック
EXISTING_MCP=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
if [ ! -z "$EXISTING_MCP" ]; then
    # 既存プロセスを静かに停止
    echo "$(date): 既存MCPサーバーを停止中..." >> "$LOG_FILE"
    ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}' | xargs -r kill
    sleep 3
    
    # 強制終了が必要な場合
    REMAINING=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
    if [ ! -z "$REMAINING" ]; then
        ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}' | xargs -r kill -9
        sleep 1
    fi
fi

# MCPサーバーを起動（単体モード）
echo "$(date): MCPサーバーを起動中 (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
exec uv run python -m worklog_mcp --project "$PROJECT_PATH" --transport http --mcp-only >> "$LOG_FILE" 2>&1