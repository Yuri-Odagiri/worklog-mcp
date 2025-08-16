#!/bin/bash
# StreamableHTTP MCPサーバーとWebビューアーの両方を起動

if [ -z "$1" ]; then
    echo "エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 <プロジェクトパス> [Webポート番号]"
    exit 1
fi

PROJECT_PATH="$1"
WEB_PORT=${2:-8080}
LOG_DIR="/tmp"
MCP_LOG="$LOG_DIR/worklog-mcp-server.log"
WEB_LOG="$LOG_DIR/worklog-web-viewer.log"

echo "🚀 worklog-mcp統合サーバーを起動中..."
echo "📁 プロジェクトパス: $PROJECT_PATH"
echo "🌐 Webポート: $WEB_PORT"
echo "📝 ログディレクトリ: $LOG_DIR"

# 既存プロセスのチェック
EXISTING_PROCS=$(ps aux | grep "worklog_mcp" | grep -v grep)
if [ ! -z "$EXISTING_PROCS" ]; then
    echo "⚠️  worklog-mcpプロセスが既に起動中です:"
    echo "$EXISTING_PROCS" | awk '{print "  PID " $2 ": " $0}'
    echo ""
    read -p "🤔 既存プロセスを停止して続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 既存プロセスを停止中..."
        ./scripts/stop-all.sh
        sleep 2
    else
        echo "❌ 起動がキャンセルされました"
        echo "📌 手動停止: ./scripts/stop-all.sh"
        exit 1
    fi
fi

# MCPサーバーを起動（単体モード）
echo "🔄 MCPサーバーを起動中..."
uv run python -m worklog_mcp --project "$PROJECT_PATH" --transport http --mcp-only > "$MCP_LOG" 2>&1 &
MCP_PID=$!

# Webビューアーを起動
echo "🔄 Webビューアーを起動中..."
uv run python -m worklog_mcp.web_server --project "$PROJECT_PATH" --port $WEB_PORT > "$WEB_LOG" 2>&1 &
WEB_PID=$!

echo "⏳ サーバーの起動を待機中..."
sleep 8

# プロセスが正常に起動したかチェック
MCP_OK=false
WEB_OK=false

if ps -p $MCP_PID > /dev/null; then
    echo "✅ MCPサーバーが起動されました (PID: $MCP_PID)"
    MCP_OK=true
else
    echo "❌ MCPサーバーの起動に失敗しました"
fi

if ps -p $WEB_PID > /dev/null; then
    echo "✅ Webビューアーが起動されました (PID: $WEB_PID)"
    WEB_OK=true
else
    echo "❌ Webビューアーの起動に失敗しました"
fi

echo ""
if [ "$MCP_OK" = true ] && [ "$WEB_OK" = true ]; then
    echo "🎉 統合サーバーが正常に起動されました！"
    echo ""
    echo "🌐 サービスアクセス:"
    echo "  📝 Webビューアー: http://localhost:$WEB_PORT"
    echo "  🔌 MCP エンドポイント: http://127.0.0.1:8001/mcp"
    echo ""
    echo "📊 プロセス情報:"
    echo "  🔧 MCPサーバー: PID $MCP_PID"
    echo "  🌐 Webビューアー: PID $WEB_PID"
    echo ""
    echo "📝 ログファイル:"
    echo "  📜 MCPサーバー: $MCP_LOG"
    echo "  📜 Webビューアー: $WEB_LOG"
    echo ""
    echo "📌 管理コマンド:"
    echo "  🛑 全停止: ./scripts/stop-all.sh"
    echo "  🔧 MCP停止: ./scripts/stop-mcp.sh"
    echo "  🌐 Web停止: ./scripts/stop-web.sh"
    echo "  📊 ログ確認: tail -f $MCP_LOG $WEB_LOG"
else
    echo "❌ 一部またはすべてのサーバーの起動に失敗しました"
    echo "📝 ログファイルを確認してください:"
    if [ "$MCP_OK" = false ]; then
        echo "  📜 MCPサーバー: $MCP_LOG"
    fi
    if [ "$WEB_OK" = false ]; then
        echo "  📜 Webビューアー: $WEB_LOG"
    fi
    exit 1
fi