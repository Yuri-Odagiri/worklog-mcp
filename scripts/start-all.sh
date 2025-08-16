#!/bin/bash
# StreamableHTTP MCPサーバーとWebビューアーの両方を起動

if [ -z "$1" ]; then
    echo "エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 <プロジェクトパス> [Webポート番号] [Agentポート番号]"
    exit 1
fi

PROJECT_PATH="$1"
WEB_PORT=${2:-8080}
AGENT_PORT=${3:-8002}
LOG_DIR="/tmp"
MCP_LOG="$LOG_DIR/worklog-mcp-server.log"
WEB_LOG="$LOG_DIR/worklog-web-viewer.log"
JOB_LOG="$LOG_DIR/worklog-job-worker.log"
AGENT_LOG="$LOG_DIR/worklog-agent-mcp.log"

echo "🚀 worklog-mcp統合サーバーを起動中..."
echo "📁 プロジェクトパス: $PROJECT_PATH"
echo "🌐 Webポート: $WEB_PORT"
echo "🤖 Agentポート: $AGENT_PORT"
echo "📝 ログディレクトリ: $LOG_DIR"

# 既存プロセスのチェック
EXISTING_PROCS=$(ps aux | grep -E "(worklog_mcp|worklog_agent_mcp|job_worker_daemon)" | grep -v grep)
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

# ジョブワーカーを起動
echo "🔄 ジョブワーカーを起動中..."
uv run python -m worklog_mcp.job_worker_daemon --project "$PROJECT_PATH" > "$JOB_LOG" 2>&1 &
JOB_PID=$!

# Agent MCPサーバーを起動
echo "🔄 Agent MCPサーバーを起動中..."
uv run python -m worklog_agent_mcp --project "$PROJECT_PATH" --transport http --port $AGENT_PORT > "$AGENT_LOG" 2>&1 &
AGENT_PID=$!

echo "⏳ サーバーの起動を待機中..."
sleep 8

# プロセスが正常に起動したかチェック
MCP_OK=false
WEB_OK=false
JOB_OK=false
AGENT_OK=false

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

if ps -p $JOB_PID > /dev/null; then
    echo "✅ ジョブワーカーが起動されました (PID: $JOB_PID)"
    JOB_OK=true
else
    echo "❌ ジョブワーカーの起動に失敗しました"
fi

if ps -p $AGENT_PID > /dev/null; then
    echo "✅ Agent MCPサーバーが起動されました (PID: $AGENT_PID)"
    AGENT_OK=true
else
    echo "❌ Agent MCPサーバーの起動に失敗しました"
fi

echo ""
if [ "$MCP_OK" = true ] && [ "$WEB_OK" = true ] && [ "$JOB_OK" = true ] && [ "$AGENT_OK" = true ]; then
    echo "🎉 統合サーバーが正常に起動されました！"
    echo ""
    echo "🌐 サービスアクセス:"
    echo "  📝 Webビューアー: http://localhost:$WEB_PORT"
    echo "  🔌 MCP エンドポイント: http://127.0.0.1:8001/mcp"
    echo "  🤖 Agent MCP エンドポイント: http://127.0.0.1:$AGENT_PORT/mcp"
    echo ""
    echo "📊 プロセス情報:"
    echo "  🔧 MCPサーバー: PID $MCP_PID"
    echo "  🌐 Webビューアー: PID $WEB_PID"
    echo "  ⚙️  ジョブワーカー: PID $JOB_PID"
    echo "  🤖 Agent MCPサーバー: PID $AGENT_PID"
    echo ""
    echo "📝 ログファイル:"
    echo "  📜 MCPサーバー: $MCP_LOG"
    echo "  📜 Webビューアー: $WEB_LOG"
    echo "  📜 ジョブワーカー: $JOB_LOG"
    echo "  📜 Agent MCPサーバー: $AGENT_LOG"
    echo ""
    echo "📌 管理コマンド:"
    echo "  🛑 全停止: ./scripts/stop-all.sh"
    echo "  🔧 MCP停止: ./scripts/stop-mcp.sh"
    echo "  🌐 Web停止: ./scripts/stop-web.sh"
    echo "  ⚙️  ジョブワーカー停止: ./scripts/stop-job-worker.sh"
    echo "  🤖 Agent MCP停止: ./scripts/stop-agent-mcp.sh"
    echo "  📊 ログ確認: tail -f $MCP_LOG $WEB_LOG $JOB_LOG $AGENT_LOG"
else
    echo "❌ 一部またはすべてのサーバーの起動に失敗しました"
    echo "📝 ログファイルを確認してください:"
    if [ "$MCP_OK" = false ]; then
        echo "  📜 MCPサーバー: $MCP_LOG"
    fi
    if [ "$WEB_OK" = false ]; then
        echo "  📜 Webビューアー: $WEB_LOG"
    fi
    if [ "$JOB_OK" = false ]; then
        echo "  📜 ジョブワーカー: $JOB_LOG"
    fi
    if [ "$AGENT_OK" = false ]; then
        echo "  📜 Agent MCPサーバー: $AGENT_LOG"
    fi
    exit 1
fi