#!/bin/bash

# Agent MCP Server 停止スクリプト

set -e

PID_FILE="/tmp/worklog-agent-mcp.pid"
LOG_FILE="/tmp/worklog-agent-mcp.log"

echo "🛑 Agent MCP Server を停止中..."

# PIDファイルの確認
if [[ ! -f "$PID_FILE" ]]; then
    echo "⚠️  PIDファイルが見つかりません: $PID_FILE"
    echo "Agent MCP Server は起動していない可能性があります"
    
    # プロセスを検索して強制終了
    PIDS=$(pgrep -f "worklog_agent_mcp" || true)
    if [[ -n "$PIDS" ]]; then
        echo "実行中のAgent MCP Serverプロセスを検出しました"
        echo "プロセスを強制終了します: $PIDS"
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
        echo "✅ プロセスを強制終了しました"
    else
        echo "実行中のAgent MCP Serverプロセスは見つかりませんでした"
    fi
    
    exit 0
fi

# PIDを読み取り
PID=$(cat "$PID_FILE")

# プロセスの確認
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Agent MCP Server プロセスを停止中 (PID: $PID)..."
    
    # graceful shutdown を試行
    kill -TERM "$PID" 2>/dev/null || true
    
    # 停止を待機（最大10秒）
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Agent MCP Server が正常に停止しました"
            break
        fi
        sleep 1
        echo "待機中... ($i/10)"
    done
    
    # まだ実行中の場合は強制終了
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️  プロセスが応答しないため、強制終了します"
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "❌ プロセスの強制終了に失敗しました"
            exit 1
        else
            echo "✅ Agent MCP Server を強制終了しました"
        fi
    fi
else
    echo "⚠️  指定されたPID ($PID) のプロセスは既に停止しています"
fi

# クリーンアップ
rm -f "$PID_FILE"

# 他のworklog_agent_mcpプロセスも確認
REMAINING_PIDS=$(pgrep -f "worklog_agent_mcp" || true)
if [[ -n "$REMAINING_PIDS" ]]; then
    echo "⚠️  他のAgent MCP Serverプロセスが実行中です: $REMAINING_PIDS"
    echo "これらも停止しますか? (y/N)"
    read -r response
    if [[ "$response" == "y" || "$response" == "Y" ]]; then
        echo "$REMAINING_PIDS" | xargs kill -9 2>/dev/null || true
        echo "✅ 残りのプロセスも停止しました"
    fi
fi

echo ""
echo "Agent MCP Server の停止が完了しました"

# ログファイルの情報
if [[ -f "$LOG_FILE" ]]; then
    echo "ログファイル: $LOG_FILE"
    echo "最新のログを確認する場合: tail -f $LOG_FILE"
fi