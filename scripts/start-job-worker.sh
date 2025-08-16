#!/bin/bash

set -euo pipefail

# スクリプトの絶対パス取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ログファイルパス
LOG_FILE="/tmp/worklog-job-worker.log"

# プロセス名
PROCESS_NAME="worklog-job-worker"

# 引数チェック
if [ $# -eq 0 ]; then
    echo "❌ エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 <プロジェクトパス> [オプション]"
    echo "例: $0 /path/to/project"
    echo "例: $0 /path/to/project --poll-interval 2.0"
    exit 1
fi

PROJECT_PATH="$1"
shift  # 最初の引数を削除

# オプション引数を処理
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --poll-interval)
            EXTRA_ARGS+=("$1" "$2")
            shift 2
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

# プロジェクトディレクトリの存在確認
if [ ! -d "$PROJECT_PATH" ]; then
    echo "❌ エラー: プロジェクトディレクトリが存在しません: $PROJECT_PATH"
    exit 1
fi

echo "🔧 worklog-mcpジョブワーカーを起動中..."
echo "📁 プロジェクト: $PROJECT_PATH"
echo "📝 ログファイル: $LOG_FILE"

# 既存のジョブワーカープロセスをチェック
if pgrep -f "job_worker_daemon" > /dev/null; then
    echo "⚠️  既存のジョブワーカープロセスが実行中です"
    echo "📋 実行中のプロセス:"
    pgrep -f "job_worker_daemon" | while read pid; do
        echo "  PID $pid: $(ps -p $pid -o args --no-headers 2>/dev/null || echo 'プロセス情報取得不可')"
    done
    echo ""
    read -p "既存のプロセスを停止して新しく起動しますか? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🛑 既存のジョブワーカープロセスを停止中..."
        pkill -f "job_worker_daemon" || true
        sleep 2
    else
        echo "❌ 起動をキャンセルしました"
        exit 1
    fi
fi

# プロジェクトディレクトリに移動
cd "$PROJECT_ROOT"

# ジョブワーカープロセスを起動
echo "🚀 ジョブワーカーデーモンを起動中..."
nohup uv run python -m worklog_mcp.job_worker_daemon --project "$PROJECT_PATH" "${EXTRA_ARGS[@]}" > "$LOG_FILE" 2>&1 &
JOB_WORKER_PID=$!

# プロセス起動の確認
sleep 2
if kill -0 $JOB_WORKER_PID 2>/dev/null; then
    echo "✅ ジョブワーカーデーモンが起動しました"
    echo "🔧 プロセスID: $JOB_WORKER_PID"
    echo "📝 ログファイル: $LOG_FILE"
    echo ""
    echo "🔍 状態確認コマンド:"
    echo "  tail -f $LOG_FILE"
    echo "  ps aux | grep job_worker_daemon"
    echo ""
    echo "🛑 停止コマンド:"
    echo "  ./scripts/stop-job-worker.sh"
    echo "  または pkill -f job_worker_daemon"
else
    echo "❌ ジョブワーカーデーモンの起動に失敗しました"
    echo "📝 ログを確認してください: $LOG_FILE"
    exit 1
fi