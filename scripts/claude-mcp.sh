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
    
    # 既存のworklog-mcpプロセスをチェック（MCP・Web両方）
    EXISTING_MCP=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
    EXISTING_WEB=$(ps aux | grep "worklog_mcp.*web_server.py" | grep -v grep)
    
    if [ ! -z "$EXISTING_MCP" ] || [ ! -z "$EXISTING_WEB" ]; then
        if [ "$FORCE_RESTART" = false ]; then
            # 既存サーバーを使い回し（起動処理なし）
            echo "$(date): 既存worklog-mcpプロセスを使用 (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
            echo "既存worklog-mcpプロセスを使用します ($MCP_URL)"
            if [ ! -z "$EXISTING_MCP" ]; then
                echo "- MCPサーバー: 動作中"
            fi
            if [ ! -z "$EXISTING_WEB" ]; then
                echo "- Webビューアー: 動作中"
            fi
            echo "強制再起動する場合は --force オプションを使用してください"
            exit 0
        else
            # 強制再起動モード - 既存プロセスを停止
            echo "$(date): 強制再起動: 既存worklog-mcpプロセスを停止中..." >> "$LOG_FILE"
            
            # MCPサーバーを停止
            if [ ! -z "$EXISTING_MCP" ]; then
                echo "- MCPサーバーを停止中..."
                ps aux | grep "worklog_mcp.*--transport http" | grep -v grep | awk '{print $2}' | xargs -r kill
            fi
            
            # Webビューアーを停止
            if [ ! -z "$EXISTING_WEB" ]; then
                echo "- Webビューアーを停止中..."
                ps aux | grep "worklog_mcp.*web_server.py" | grep -v grep | awk '{print $2}' | xargs -r kill
            fi
            
            sleep 3
            
            # 強制終了が必要な場合
            REMAINING_MCP=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
            REMAINING_WEB=$(ps aux | grep "worklog_mcp.*web_server.py" | grep -v grep)
            if [ ! -z "$REMAINING_MCP" ] || [ ! -z "$REMAINING_WEB" ]; then
                echo "- 強制終了中..."
                ps aux | grep "worklog_mcp" | grep -v grep | awk '{print $2}' | xargs -r kill -9
                sleep 1
            fi
        fi
    fi
    
    # 統合サーバーを起動（MCP + Web）
    echo "$(date): worklog-mcp統合サーバーを起動中 (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
    exec uv run python -m worklog_mcp --project "$PROJECT_PATH" --transport http >> "$LOG_FILE" 2>&1
else
    # リモートサーバーの場合（起動処理なし）
    echo "$(date): リモートMCPサーバー指定: $MCP_URL (プロジェクト: $PROJECT_PATH)" >> "$LOG_FILE"
    echo "リモートMCPサーバーを使用します: $MCP_URL"
    echo "注意: リモートサーバーへの接続は Claude Code 側で行われます"
    exit 0
fi