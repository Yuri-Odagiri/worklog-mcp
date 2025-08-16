#!/bin/bash

set -euo pipefail

echo "🛑 worklog-mcpジョブワーカーを停止中..."

# ジョブワーカープロセスを検索
JOB_WORKER_PIDS=$(pgrep -f "job_worker_daemon" || true)

if [ -z "$JOB_WORKER_PIDS" ]; then
    echo "ℹ️  実行中のジョブワーカープロセスが見つかりません"
    exit 0
fi

echo "📋 停止対象プロセス:"
echo "$JOB_WORKER_PIDS" | while read pid; do
    if [ -n "$pid" ]; then
        echo "  PID $pid: $(ps -p $pid -o user,pid,pcpu,pmem,args --no-headers 2>/dev/null || echo 'プロセス情報取得不可')"
    fi
done

# SIGTERM で停止を試行
echo "$JOB_WORKER_PIDS" | while read pid; do
    if [ -n "$pid" ]; then
        echo "⏹️  プロセス $pid を停止中..."
        kill -TERM "$pid" 2>/dev/null || true
    fi
done

# 停止を待機 (最大10秒)
echo "⏳ プロセスの停止を待機中..."
sleep 3

# まだ実行中のプロセスがあるかチェック
REMAINING_PIDS=$(pgrep -f "job_worker_daemon" || true)

if [ -n "$REMAINING_PIDS" ]; then
    echo "⚠️  一部プロセスが残存しています。強制終了中..."
    echo "$REMAINING_PIDS" | while read pid; do
        if [ -n "$pid" ]; then
            echo "💀 プロセス $pid を強制終了中..."
            kill -KILL "$pid" 2>/dev/null || true
        fi
    done
    sleep 2
fi

# 最終確認
FINAL_CHECK=$(pgrep -f "job_worker_daemon" || true)
if [ -z "$FINAL_CHECK" ]; then
    echo "✅ 全てのジョブワーカープロセスが停止されました"
else
    echo "❌ 一部のプロセスが停止されませんでした:"
    echo "$FINAL_CHECK" | while read pid; do
        if [ -n "$pid" ]; then
            echo "  PID $pid: $(ps -p $pid -o args --no-headers 2>/dev/null || echo 'プロセス情報取得不可')"
        fi
    done
    exit 1
fi