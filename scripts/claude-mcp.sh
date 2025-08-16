#!/bin/bash
# Claude Code専用のMCPサーバー起動スクリプト
# - URLがローカルの場合：--forceで強制再起動、なしで既存使用
# - URLがリモートの場合：指定URLをそのまま使用
# - ログ出力を最小化
# - バックグラウンド実行でプロンプトブロックを回避

# オプション解析
FORCE_RESTART=false
PROJECT_PATH=""
MCP_URL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE_RESTART=true
            shift
            ;;
        --url)
            MCP_URL="$2"
            shift 2
            ;;
        *)
            if [ -z "$PROJECT_PATH" ]; then
                PROJECT_PATH="$1"
            else
                echo "エラー: 不明なオプション '$1'"
                echo "使用方法: $0 [--force] [--url <URL>] <プロジェクトパス>"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$PROJECT_PATH" ]; then
    echo "エラー: プロジェクトパスが指定されていません"
    echo "使用方法: $0 [--force] [--url <URL>] <プロジェクトパス>"
    echo "オプション:"
    echo "  --force, -f         ローカルサーバーを強制再起動"
    echo "  --url <URL>         MCPサーバーURL（デフォルト: http://localhost:8001/mcp）"
    exit 1
fi

# デフォルトURL設定
if [ -z "$MCP_URL" ]; then
    MCP_URL="http://localhost:8001/mcp"
fi

LOG_FILE="/tmp/worklog-mcp-claude.log"

# URLがローカル（localhost/127.0.0.1）かどうかを判定
if [[ "$MCP_URL" =~ ^https?://(localhost|127\.0\.0\.1)(:|/) ]]; then
    # ローカルサーバーの場合
    echo "$(date): ローカルMCPサーバー指定: $MCP_URL" >> "$LOG_FILE"
    
    # 既存のMCPサーバープロセスをチェック
    EXISTING_MCP=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
    
    if [ ! -z "$EXISTING_MCP" ]; then
        if [ "$FORCE_RESTART" = false ]; then
            # 既存サーバーを使い回し（起動処理なし）
            echo "$(date): 既存ローカルMCPサーバーを使用 (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
            echo "既存MCPサーバーを使用します ($MCP_URL)"
            echo "強制再起動する場合は --force オプションを使用してください"
            exit 0
        else
            # 強制再起動モード - 既存プロセスを停止
            echo "$(date): 強制再起動: 既存MCPサーバーを停止中..." >> "$LOG_FILE"
            ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}' | xargs -r kill
            sleep 3
            
            # 強制終了が必要な場合
            REMAINING=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
            if [ ! -z "$REMAINING" ]; then
                ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}' | xargs -r kill -9
                sleep 1
            fi
        fi
    fi
    
    # MCPサーバーを起動（単体モード）
    echo "$(date): ローカルMCPサーバーを起動中 (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
    exec uv run python -m worklog_mcp --project "$PROJECT_PATH" --transport http --mcp-only >> "$LOG_FILE" 2>&1
else
    # リモートサーバーの場合（起動処理なし）
    echo "$(date): リモートMCPサーバー指定: $MCP_URL (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
    echo "リモートMCPサーバーを使用します: $MCP_URL"
    echo "注意: リモートサーバーへの接続は Claude Code 側で行われます"
    exit 0
fi