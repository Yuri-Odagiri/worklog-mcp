#!/bin/bash
# Webビューアーのみ起動

if [ -z "$1" ]; then
    echo "エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 <プロジェクトパス> [ポート番号]"
    exit 1
fi

PROJECT_PATH="$1"
WEB_PORT=${2:-8080}
LOG_DIR="/tmp"
LOG_FILE="$LOG_DIR/worklog-web-viewer.log"

echo "🚀 Webビューアーを起動中..."
echo "📁 プロジェクトパス: $PROJECT_PATH"
echo "🌐 ポート: $WEB_PORT"
echo "📝 ログファイル: $LOG_FILE"

# 既存のWebビューアープロセスをチェック
if ps aux | grep "worklog_mcp.web_server" | grep -v grep > /dev/null; then
    echo "⚠️  Webビューアーが既に起動中です:"
    ps aux | grep "worklog_mcp.web_server" | grep -v grep | awk '{print "  PID " $2 ": " $0}'
    echo "📌 停止するには: ./scripts/stop-web.sh"
    exit 1
fi

# ポート使用状況をチェック
if lsof -i :$WEB_PORT > /dev/null 2>&1; then
    echo "❌ ポート $WEB_PORT は既に使用中です"
    echo "📋 使用中のプロセス:"
    lsof -i :$WEB_PORT
    exit 1
fi

# Webビューアーを起動
echo "🔄 Webビューアーを起動中..."
uv run python -m worklog_mcp.web_server --project "$PROJECT_PATH" --port $WEB_PORT > "$LOG_FILE" 2>&1 &
WEB_PID=$!

echo "⏳ サーバーの起動を待機中..."
sleep 5

# プロセスが正常に起動したかチェック
if ps -p $WEB_PID > /dev/null; then
    echo "✅ Webビューアーが起動されました"
    echo "🌐 アクセスURL: http://localhost:$WEB_PORT"
    echo "📊 プロセスID: $WEB_PID"
    echo "📝 ログファイル: $LOG_FILE"
    echo ""
    echo "📌 停止するには: ./scripts/stop-web.sh"
    echo "📌 ログ確認: tail -f $LOG_FILE"
else
    echo "❌ Webビューアーの起動に失敗しました"
    echo "📝 ログファイルを確認してください: $LOG_FILE"
    exit 1
fi