#!/bin/bash

# Agent MCP Server ステータス確認スクリプト

set -e

PID_FILE="/tmp/worklog-agent-mcp.pid"
LOG_FILE="/tmp/worklog-agent-mcp.log"

echo "📊 Agent MCP Server ステータス確認"
echo "=================================="

# PIDファイルの確認
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    echo "PIDファイル: $PID_FILE (PID: $PID)"
    
    # プロセスの確認
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Agent MCP Server は実行中です"
        
        # プロセス情報を表示
        echo ""
        echo "プロセス情報:"
        ps -p "$PID" -o pid,ppid,cmd,etime,rss
        
        # ポート使用状況を確認
        echo ""
        echo "ポート使用状況:"
        netstat -tlnp 2>/dev/null | grep ":800" || echo "該当するポートが見つかりません"
        
    else
        echo "❌ PIDファイルは存在しますが、プロセスが実行されていません"
        echo "古いPIDファイルを削除します..."
        rm -f "$PID_FILE"
    fi
else
    echo "⚠️  PIDファイルが見つかりません"
fi

# worklog_agent_mcpプロセスを検索
echo ""
echo "関連プロセス検索:"
AGENT_PIDS=$(pgrep -f "worklog_agent_mcp" || true)
if [[ -n "$AGENT_PIDS" ]]; then
    echo "✅ worklog_agent_mcp プロセスが見つかりました:"
    echo "$AGENT_PIDS" | while read -r pid; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "  PID $pid: $(ps -p "$pid" -o cmd --no-headers)"
        fi
    done
else
    echo "❌ worklog_agent_mcp プロセスは見つかりませんでした"
fi

# ログファイルの確認
echo ""
echo "ログファイル:"
if [[ -f "$LOG_FILE" ]]; then
    echo "✅ ログファイル: $LOG_FILE"
    
    # ファイルサイズとタイムスタンプ
    FILESIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo "不明")
    TIMESTAMP=$(stat -f%Sm "$LOG_FILE" 2>/dev/null || stat -c%y "$LOG_FILE" 2>/dev/null || echo "不明")
    echo "  サイズ: $FILESIZE bytes"
    echo "  更新日時: $TIMESTAMP"
    
    # 最後の10行を表示
    echo ""
    echo "最新ログ (最後の10行):"
    echo "─────────────────────"
    tail -10 "$LOG_FILE" 2>/dev/null || echo "ログの読み取りに失敗しました"
    echo "─────────────────────"
    
else
    echo "❌ ログファイルが見つかりません: $LOG_FILE"
fi

# ネットワーク接続の確認
echo ""
echo "ネットワーク接続:"
if command -v lsof > /dev/null 2>&1; then
    CONNECTIONS=$(lsof -i :8002 2>/dev/null || true)
    if [[ -n "$CONNECTIONS" ]]; then
        echo "✅ ポート8002での接続:"
        echo "$CONNECTIONS"
    else
        echo "⚠️  ポート8002での接続が見つかりません"
    fi
else
    echo "⚠️  lsofコマンドが利用できません"
fi

# システムリソース使用状況
echo ""
echo "システムリソース:"
if [[ -n "$AGENT_PIDS" ]]; then
    echo "$AGENT_PIDS" | while read -r pid; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "PID $pid のリソース使用状況:"
            ps -p "$pid" -o pid,pcpu,pmem,rss,vsz
        fi
    done
else
    echo "対象プロセスが見つかりません"
fi

echo ""
echo "=================================="

# 推奨アクション
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Agent MCP Server は正常に動作しています"
        echo ""
        echo "利用可能なコマンド:"
        echo "  ログ監視: tail -f $LOG_FILE"
        echo "  サーバー停止: ./scripts/stop-agent-mcp.sh"
        echo "  サーバー再起動: ./scripts/stop-agent-mcp.sh && ./scripts/start-agent-mcp.sh PROJECT_PATH"
    else
        echo "❌ Agent MCP Server が停止しています"
        echo ""
        echo "推奨アクション:"
        echo "  サーバー起動: ./scripts/start-agent-mcp.sh PROJECT_PATH"
    fi
else
    echo "❌ Agent MCP Server が起動していません"
    echo ""
    echo "推奨アクション:"
    echo "  サーバー起動: ./scripts/start-agent-mcp.sh PROJECT_PATH"
fi