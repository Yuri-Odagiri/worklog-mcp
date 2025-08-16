#!/bin/bash
# worklog-mcpの全プロセスを停止

echo "🛑 worklog-mcpプロセスを停止中..."

# worklog-mcp、Agent MCP、ジョブワーカープロセスを検索
PROCS=$(ps aux | grep -E "(worklog_mcp|worklog_agent_mcp|job_worker_daemon)" | grep -v grep | awk '{print $2}')

if [ -z "$PROCS" ]; then
    echo "✅ 停止対象のプロセスが見つかりません"
    exit 0
fi

echo "📋 停止対象プロセス:"
ps aux | grep -E "(worklog_mcp|worklog_agent_mcp|job_worker_daemon)" | grep -v grep | awk '{print "  PID " $2 ": " $0}'

# プロセスを停止
for PID in $PROCS; do
    echo "⏹️  プロセス $PID を停止中..."
    kill $PID 2>/dev/null
done

# 5秒待機後、強制終了が必要かチェック
sleep 5

REMAINING=$(ps aux | grep -E "(worklog_mcp|worklog_agent_mcp|job_worker_daemon)" | grep -v grep | awk '{print $2}')
if [ ! -z "$REMAINING" ]; then
    echo "⚠️  一部プロセスが残存しています。強制終了中..."
    for PID in $REMAINING; do
        echo "💀 プロセス $PID を強制終了中..."
        kill -9 $PID 2>/dev/null
    done
    sleep 2
fi

# 最終確認
FINAL_CHECK=$(ps aux | grep -E "(worklog_mcp|job_worker_daemon)" | grep -v grep)
if [ -z "$FINAL_CHECK" ]; then
    echo "✅ 全てのworklog-mcpプロセスが停止されました"
else
    echo "❌ 一部プロセスが残存している可能性があります:"
    echo "$FINAL_CHECK"
fi