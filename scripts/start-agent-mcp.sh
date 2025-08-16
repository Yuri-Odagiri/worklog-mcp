#!/bin/bash

# Agent MCP Server 起動スクリプト

set -e

# デフォルト設定
DEFAULT_HOST="localhost"
DEFAULT_PORT="8002"
DEFAULT_TRANSPORT="http"

# 使用方法を表示
show_usage() {
    echo "使用方法: $0 [OPTIONS] PROJECT_PATH"
    echo ""
    echo "Agent MCP Server を起動します"
    echo ""
    echo "オプション:"
    echo "  -h, --host HOST      ホストアドレス (デフォルト: $DEFAULT_HOST)"
    echo "  -p, --port PORT      ポート番号 (デフォルト: $DEFAULT_PORT)"
    echo "  -t, --transport TYPE トランスポートタイプ (stdio|http, デフォルト: $DEFAULT_TRANSPORT)"
    echo "  -u, --user USER_ID   ユーザーID"
    echo "  --help               このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 /path/to/project"
    echo "  $0 --host 0.0.0.0 --port 8003 /path/to/project"
    echo "  $0 --transport stdio --user developer /path/to/project"
}

# パラメータ解析
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
TRANSPORT="$DEFAULT_TRANSPORT"
USER_ID=""
PROJECT_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -t|--transport)
            TRANSPORT="$2"
            shift 2
            ;;
        -u|--user)
            USER_ID="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            if [[ -z "$PROJECT_PATH" ]]; then
                PROJECT_PATH="$1"
            else
                echo "エラー: 不明な引数: $1"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# プロジェクトパスの確認
if [[ -z "$PROJECT_PATH" ]]; then
    echo "エラー: プロジェクトパスが指定されていません"
    show_usage
    exit 1
fi

if [[ ! -d "$PROJECT_PATH" ]]; then
    echo "エラー: プロジェクトパスが存在しません: $PROJECT_PATH"
    exit 1
fi

# プロジェクトパスを絶対パスに変換
PROJECT_PATH=$(realpath "$PROJECT_PATH")

echo "🚀 Agent MCP Server を起動中..."
echo "  プロジェクトパス: $PROJECT_PATH"
echo "  トランスポート: $TRANSPORT"

if [[ "$TRANSPORT" == "http" ]]; then
    echo "  ホスト: $HOST"
    echo "  ポート: $PORT"
fi

if [[ -n "$USER_ID" ]]; then
    echo "  ユーザーID: $USER_ID"
fi

echo ""

# コマンド構築
CMD="uv run python -m worklog_agent_mcp --project \"$PROJECT_PATH\" --transport $TRANSPORT"

if [[ "$TRANSPORT" == "http" ]]; then
    CMD="$CMD --host $HOST --port $PORT"
fi

if [[ -n "$USER_ID" ]]; then
    CMD="$CMD --user \"$USER_ID\""
fi

# ログファイル設定
LOG_FILE="/tmp/worklog-agent-mcp.log"
PID_FILE="/tmp/worklog-agent-mcp.pid"

# 既存プロセスの確認
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  既存のAgent MCP Serverプロセスが実行中です (PID: $OLD_PID)"
        echo "既存プロセスを停止してから再実行してください:"
        echo "  ./scripts/stop-agent-mcp.sh"
        exit 1
    else
        # PIDファイルが古い場合は削除
        rm -f "$PID_FILE"
    fi
fi

# バックグラウンドでサーバーを起動
echo "Agent MCP Server をバックグラウンドで起動中..."
eval "$CMD" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# PIDを保存
echo "$SERVER_PID" > "$PID_FILE"

# 起動確認
sleep 2
if ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo "✅ Agent MCP Server が正常に起動しました"
    echo "  PID: $SERVER_PID"
    echo "  ログ: $LOG_FILE"
    
    if [[ "$TRANSPORT" == "http" ]]; then
        echo "  アクセスURL: http://$HOST:$PORT"
        echo ""
        echo "📡 Claude Code での利用例:"
        echo "  .mcp.json に以下を追加:"
        echo "  {"
        echo "    \"mcpServers\": {"
        echo "      \"worklog-agent\": {"
        echo "        \"url\": \"http://$HOST:$PORT/mcp\""
        echo "      }"
        echo "    }"
        echo "  }"
    fi
    
    echo ""
    echo "停止する場合: ./scripts/stop-agent-mcp.sh"
    echo "状態確認: ./scripts/status-agent-mcp.sh"
else
    echo "❌ Agent MCP Server の起動に失敗しました"
    echo "ログを確認してください: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi