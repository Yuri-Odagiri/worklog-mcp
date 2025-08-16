#!/bin/bash
# StreamableHTTP MCPサーバーのみ停止

echo "🛑 Streamable HTTP MCPサーバーを停止中..."

# MCPサーバープロセスを検索（--transport httpを含む）
MCP_PROCS=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}')

if [ -z "$MCP_PROCS" ]; then
    echo "✅ 停止対象のMCPサーバープロセスが見つかりません"
    exit 0
fi

echo "📋 停止対象MCPサーバープロセス:"
ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print "  PID " $2 ": " $0}'

# プロセスを停止
for PID in $MCP_PROCS; do
    echo "⏹️  MCPサーバー $PID を停止中..."
    kill $PID 2>/dev/null
done

# 5秒待機後、強制終了が必要かチェック
sleep 5

REMAINING=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}')
if [ ! -z "$REMAINING" ]; then
    echo "⚠️  一部MCPサーバープロセスが残存しています。強制終了中..."
    for PID in $REMAINING; do
        echo "💀 MCPサーバー $PID を強制終了中..."
        kill -9 $PID 2>/dev/null
    done
    sleep 2
fi

# 最終確認
FINAL_CHECK=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
if [ -z "$FINAL_CHECK" ]; then
    echo "✅ MCPサーバーが停止されました"
else
    echo "❌ 一部MCPサーバープロセスが残存している可能性があります:"
    echo "$FINAL_CHECK"
fi