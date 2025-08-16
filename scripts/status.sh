#!/bin/bash
# worklog-mcpプロセスの状態確認

echo "📊 worklog-mcp プロセス状態確認"
echo "=================================="

# プロセス検索
MCP_PROCS=$(ps aux | grep "worklog_mcp.*--transport http" | grep -v grep)
WEB_PROCS=$(ps aux | grep "worklog_mcp.web_server" | grep -v grep)
AGENT_PROCS=$(ps aux | grep "worklog_agent_mcp" | grep -v grep)
ALL_PROCS=$(ps aux | grep "worklog_mcp\|worklog_agent_mcp" | grep -v grep)

# ポート使用状況確認
MCP_PORT_STATUS=$(lsof -i :8001 2>/dev/null)
WEB_PORT_STATUS=$(lsof -i :8080 2>/dev/null)
AGENT_PORT_STATUS=$(lsof -i :8002 2>/dev/null)

# MCPサーバー状態
echo ""
echo "🔧 MCP サーバー (ポート 8001)"
echo "------------------------------"
if [ ! -z "$MCP_PROCS" ]; then
    echo "✅ 実行中"
    echo "$MCP_PROCS" | while read line; do
        PID=$(echo "$line" | awk '{print $2}')
        USER=$(echo "$line" | awk '{print $1}')
        CPU=$(echo "$line" | awk '{print $3}')
        MEM=$(echo "$line" | awk '{print $4}')
        START=$(echo "$line" | awk '{print $9}')
        CMD=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')
        echo "  📊 PID: $PID | CPU: $CPU% | MEM: $MEM% | 開始: $START"
        echo "  📂 コマンド: $CMD"
        
        # プロジェクトパスを抽出
        PROJECT_PATH=$(echo "$CMD" | grep -o -- "--project [^ ]*" | cut -d' ' -f2)
        if [ ! -z "$PROJECT_PATH" ]; then
            echo "  📁 プロジェクト: $PROJECT_PATH"
        fi
    done
    
    # MCP エンドポイントテスト
    echo "  🌐 エンドポイント接続テスト..."
    ENDPOINT_TEST=$(curl -s -X POST http://127.0.0.1:8001/mcp \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"status-check","version":"1.0.0"}}}' \
        --max-time 5 2>/dev/null)
    
    if echo "$ENDPOINT_TEST" | grep -q "protocolVersion"; then
        echo "  ✅ エンドポイント正常"
        VERSION=$(echo "$ENDPOINT_TEST" | grep -o '"protocolVersion":"[^"]*"' | cut -d'"' -f4)
        SERVER_NAME=$(echo "$ENDPOINT_TEST" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        echo "  📋 プロトコル: $VERSION"
        echo "  🏷️  サーバー名: $SERVER_NAME"
    else
        echo "  ❌ エンドポイント応答なし"
    fi
else
    echo "❌ 停止中"
    if [ ! -z "$MCP_PORT_STATUS" ]; then
        echo "⚠️  ポート8001は他のプロセスが使用中:"
        echo "$MCP_PORT_STATUS" | awk 'NR>1 {print "  🔒 " $1 " (PID: " $2 ")"}'
    fi
fi

# Webビューアー状態
echo ""
echo "🌐 Web ビューアー (ポート 8080)"
echo "------------------------------"
if [ ! -z "$WEB_PROCS" ]; then
    echo "✅ 実行中"
    echo "$WEB_PROCS" | while read line; do
        PID=$(echo "$line" | awk '{print $2}')
        USER=$(echo "$line" | awk '{print $1}')
        CPU=$(echo "$line" | awk '{print $3}')
        MEM=$(echo "$line" | awk '{print $4}')
        START=$(echo "$line" | awk '{print $9}')
        CMD=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')
        echo "  📊 PID: $PID | CPU: $CPU% | MEM: $MEM% | 開始: $START"
        echo "  📂 コマンド: $CMD"
        
        # ポート番号とプロジェクトパスを抽出
        PORT=$(echo "$CMD" | grep -o -- "--port [0-9]*" | cut -d' ' -f2)
        PROJECT_PATH=$(echo "$CMD" | grep -o -- "--project [^ ]*" | cut -d' ' -f2)
        if [ ! -z "$PORT" ]; then
            echo "  🌐 ポート: $PORT"
        fi
        if [ ! -z "$PROJECT_PATH" ]; then
            echo "  📁 プロジェクト: $PROJECT_PATH"
        fi
    done
    
    # Web アクセステスト
    echo "  🌐 Webアクセステスト..."
    WEB_TEST=$(curl -s -I http://localhost:8080 --max-time 5 2>/dev/null | head -1)
    if echo "$WEB_TEST" | grep -q "200 OK"; then
        echo "  ✅ Webビューアー正常"
        echo "  🔗 アクセス: http://localhost:8080"
    else
        echo "  ❌ Webビューアー応答なし"
    fi
else
    echo "❌ 停止中"
    if [ ! -z "$WEB_PORT_STATUS" ]; then
        echo "⚠️  ポート8080は他のプロセスが使用中:"
        echo "$WEB_PORT_STATUS" | awk 'NR>1 {print "  🔒 " $1 " (PID: " $2 ")"}'
    fi
fi

# Agent MCPサーバー状態
echo ""
echo "🤖 Agent MCP サーバー (ポート 8002)"
echo "--------------------------------"
if [ ! -z "$AGENT_PROCS" ]; then
    echo "✅ 実行中"
    echo "$AGENT_PROCS" | while read line; do
        PID=$(echo "$line" | awk '{print $2}')
        USER=$(echo "$line" | awk '{print $1}')
        CPU=$(echo "$line" | awk '{print $3}')
        MEM=$(echo "$line" | awk '{print $4}')
        START=$(echo "$line" | awk '{print $9}')
        CMD=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')
        echo "  📊 PID: $PID | CPU: $CPU% | MEM: $MEM% | 開始: $START"
        echo "  📂 コマンド: $CMD"
        
        # プロジェクトパスを抽出
        PROJECT_PATH=$(echo "$CMD" | grep -o -- "--project [^ ]*" | cut -d' ' -f2)
        if [ ! -z "$PROJECT_PATH" ]; then
            echo "  📁 プロジェクト: $PROJECT_PATH"
        fi
        
        # ポート番号を抽出
        PORT_NUM=$(echo "$CMD" | grep -o -- "--port [^ ]*" | cut -d' ' -f2)
        if [ ! -z "$PORT_NUM" ]; then
            echo "  🔌 ポート: $PORT_NUM"
        fi
    done
    
    # Agent MCP エンドポイントテスト
    echo "  🌐 エンドポイント接続テスト..."
    AGENT_ENDPOINT_TEST=$(curl -s -X POST http://127.0.0.1:8002/mcp \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"status-check","version":"1.0.0"}}}' \
        --max-time 5 2>/dev/null)
    
    if echo "$AGENT_ENDPOINT_TEST" | grep -q "protocolVersion"; then
        echo "  ✅ Agent MCPエンドポイント正常"
        AGENT_VERSION=$(echo "$AGENT_ENDPOINT_TEST" | grep -o '"protocolVersion":"[^"]*"' | cut -d'"' -f4)
        AGENT_SERVER_NAME=$(echo "$AGENT_ENDPOINT_TEST" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        echo "  📋 サーバー名: $AGENT_SERVER_NAME"
        echo "  🔖 プロトコル版: $AGENT_VERSION"
    else
        echo "  ❌ Agent MCPエンドポイント応答なし"
    fi
else
    echo "❌ 停止中"
    if [ ! -z "$AGENT_PORT_STATUS" ]; then
        echo "⚠️  ポート8002は他のプロセスが使用中:"
        echo "$AGENT_PORT_STATUS" | awk 'NR>1 {print "  🔒 " $1 " (PID: " $2 ")"}'
    fi
fi

# 全体サマリー
echo ""
echo "📋 サマリー"
echo "----------"
if [ ! -z "$ALL_PROCS" ]; then
    PROC_COUNT=$(echo "$ALL_PROCS" | wc -l)
    echo "📊 worklog-mcp プロセス数: $PROC_COUNT"
    
    # メモリ使用量計算
    TOTAL_MEM=$(echo "$ALL_PROCS" | awk '{sum += $6} END {printf "%.1f", sum/1024}')
    echo "💾 総メモリ使用量: ${TOTAL_MEM}MB"
    
    # CPU使用量計算  
    TOTAL_CPU=$(echo "$ALL_PROCS" | awk '{sum += $3} END {printf "%.1f", sum}')
    echo "⚡ 総CPU使用量: ${TOTAL_CPU}%"
else
    echo "📊 worklog-mcp プロセス数: 0"
fi

# ログファイル状態
echo ""
echo "📝 ログファイル状態"
echo "------------------"
LOG_FILES=("/tmp/worklog-mcp-server.log" "/tmp/worklog-web-viewer.log" "/tmp/worklog-agent-mcp.log" "/tmp/worklog-mcp-claude.log")
for LOG_FILE in "${LOG_FILES[@]}"; do
    if [ -f "$LOG_FILE" ]; then
        SIZE=$(du -h "$LOG_FILE" | cut -f1)
        MODIFIED=$(stat -c %y "$LOG_FILE" | cut -d' ' -f1-2 | cut -d'.' -f1)
        echo "📄 $(basename "$LOG_FILE"): $SIZE (更新: $MODIFIED)"
    else
        echo "📄 $(basename "$LOG_FILE"): 未作成"
    fi
done

# データベース状態（プロジェクトパスが判明している場合）
if [ ! -z "$MCP_PROCS" ]; then
    PROJECT_PATH=$(echo "$MCP_PROCS" | head -1 | grep -o -- "--project [^ ]*" | cut -d' ' -f2)
    if [ ! -z "$PROJECT_PATH" ]; then
        echo ""
        echo "🗄️  データベース状態 ($PROJECT_PATH)"
        echo "-----------------------------------"
        
        DB_BASE_DIR="$HOME/.worklog/$(basename "$PROJECT_PATH")"
        
        if [ -d "$DB_BASE_DIR" ]; then
            # worklog.db
            if [ -f "$DB_BASE_DIR/worklog.db" ]; then
                DB_SIZE=$(du -h "$DB_BASE_DIR/worklog.db" | cut -f1)
                echo "📊 worklog.db: $DB_SIZE"
                
                # SQLiteでレコード数取得（可能な場合）
                if command -v sqlite3 >/dev/null 2>&1; then
                    ENTRY_COUNT=$(sqlite3 "$DB_BASE_DIR/worklog.db" "SELECT COUNT(*) FROM worklog_entries;" 2>/dev/null || echo "不明")
                    USER_COUNT=$(sqlite3 "$DB_BASE_DIR/worklog.db" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "不明")
                    echo "📝 分報エントリー数: $ENTRY_COUNT"
                    echo "👥 ユーザー数: $USER_COUNT"
                fi
            else
                echo "📊 worklog.db: 未作成"
            fi
            
            # eventbus.db
            if [ -f "$DB_BASE_DIR/eventbus.db" ]; then
                EVENTBUS_SIZE=$(du -h "$DB_BASE_DIR/eventbus.db" | cut -f1)
                echo "📡 eventbus.db: $EVENTBUS_SIZE"
            else
                echo "📡 eventbus.db: 未作成"
            fi
            
            # avatar フォルダ
            if [ -d "$DB_BASE_DIR/avatar" ]; then
                AVATAR_COUNT=$(find "$DB_BASE_DIR/avatar" -type f | wc -l)
                AVATAR_SIZE=$(du -sh "$DB_BASE_DIR/avatar" | cut -f1)
                echo "🖼️  アバター: $AVATAR_COUNT ファイル ($AVATAR_SIZE)"
            else
                echo "🖼️  アバター: フォルダ未作成"
            fi
        else
            echo "❌ データベースディレクトリが存在しません"
        fi
    fi
fi

# 管理コマンド
echo ""
echo "🔧 管理コマンド"
echo "--------------"
echo "🚀 起動: ./scripts/start-all.sh <プロジェクトパス>"
echo "🛑 停止: ./scripts/stop-all.sh"
echo "📊 状態: ./scripts/status.sh"
echo "📝 ログ: tail -f /tmp/worklog-mcp-*.log"