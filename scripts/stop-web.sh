#!/bin/bash
# Webビューアーのみ停止

echo "🛑 Webビューアーを停止中..."

# Webサーバープロセスを検索（web_serverを含む）
WEB_PROCS=$(ps aux | grep "worklog_mcp.web_server" | grep -v grep | awk '{print $2}')

if [ -z "$WEB_PROCS" ]; then
    echo "✅ 停止対象のWebビューアープロセスが見つかりません"
    exit 0
fi

echo "📋 停止対象Webビューアープロセス:"
ps aux | grep "worklog_mcp.web_server" | grep -v grep | awk '{print "  PID " $2 ": " $0}'

# プロセスを停止
for PID in $WEB_PROCS; do
    echo "⏹️  Webビューアー $PID を停止中..."
    kill $PID 2>/dev/null
done

# 5秒待機後、強制終了が必要かチェック
sleep 5

REMAINING=$(ps aux | grep "worklog_mcp.web_server" | grep -v grep | awk '{print $2}')
if [ ! -z "$REMAINING" ]; then
    echo "⚠️  一部Webビューアープロセスが残存しています。強制終了中..."
    for PID in $REMAINING; do
        echo "💀 Webビューアー $PID を強制終了中..."
        kill -9 $PID 2>/dev/null
    done
    sleep 2
fi

# 最終確認
FINAL_CHECK=$(ps aux | grep "worklog_mcp.web_server" | grep -v grep)
if [ -z "$FINAL_CHECK" ]; then
    echo "✅ Webビューアーが停止されました"
else
    echo "❌ 一部Webビューアープロセスが残存している可能性があります:"
    echo "$FINAL_CHECK"
fi