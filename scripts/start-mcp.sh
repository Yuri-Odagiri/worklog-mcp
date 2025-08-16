#!/bin/bash
# StreamableHTTP MCPサーバーのみ起動

if [ -z "$1" ]; then
    echo "エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 <プロジェクトパス>"
    exit 1
fi

PROJECT_PATH="$1"
LOG_DIR="/tmp"
LOG_FILE="$LOG_DIR/worklog-mcp-server.log"

echo "🚀 Streamable HTTP MCPサーバーを起動中..."
echo "📁 プロジェクトパス: $PROJECT_PATH"
echo "📝 ログファイル: $LOG_FILE"

# 既存のMCPサーバープロセスをチェック
if ps aux | grep "worklog_mcp.*--transport http" | grep -v grep > /dev/null; then
    echo "⚠️  MCPサーバーが既に起動中です:"
    ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print "  PID " $2 ": " $0}'
    echo "📌 停止するには: ./scripts/stop-mcp.sh"
    exit 1
fi

# MCPサーバーを起動（MCP単体モード）
echo "🔄 MCPサーバーを起動中..."
uv run python -m worklog_mcp --project "$PROJECT_PATH" --transport http --mcp-only > "$LOG_FILE" 2>&1 &
MCP_PID=$!

echo "⏳ サーバーの起動を待機中..."
sleep 5

# プロセスが正常に起動したかチェック
if ps -p $MCP_PID > /dev/null; then
    echo "✅ MCPサーバーが起動されました"
    echo "🌐 MCP エンドポイント: http://127.0.0.1:8001/mcp"
    echo "📊 プロセスID: $MCP_PID"
    echo "📝 ログファイル: $LOG_FILE"
    echo ""
    echo "📌 停止するには: ./scripts/stop-mcp.sh"
    echo "📌 ログ確認: tail -f $LOG_FILE"
else
    echo "❌ MCPサーバーの起動に失敗しました"
    echo "📝 ログファイルを確認してください: $LOG_FILE"
    exit 1
fi