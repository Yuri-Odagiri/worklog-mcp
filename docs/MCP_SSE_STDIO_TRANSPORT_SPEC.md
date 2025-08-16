# MCP トランスポート仕様書：SSE/Stdio両対応実装

## 概要

Model Context Protocol (MCP) は複数のトランスポート方式をサポートしており、現在のstdio実装にSSE（Server-Sent Events）サポートを追加する必要があります。

## 現在の実装状況

- **現在の実装**: stdio トランスポートのみ対応
- **目標**: stdio と SSE/HTTP の両方に対応

## MCPトランスポート仕様

### 1. Stdio トランスポート（現在実装済み）

#### 特徴
- クライアントがサーバーをサブプロセスとして起動
- JSON-RPCメッセージをstdin/stdoutで交換
- メッセージは改行で区切られ、埋め込み改行は不可
- サーバーはログ用にstderrを使用可能

#### シーケンス
```
Client -> Server Process: Launch subprocess
Client -> Server Process: Write to stdin
Server Process -> Client: Write to stdout  
Server Process -> Client: Optional logs on stderr
Client -> Server Process: Close stdin, terminate subprocess
```

### 2. SSE/HTTP トランスポート（実装予定）

#### 2.1 レガシーHTTP+SSE（2024-11-05プロトコル版）

**特徴:**
- サーバーは独立プロセスとして稼働
- SSEエンドポイント（クライアント接続・メッセージ受信用）
- HTTP POSTエンドポイント（クライアントからのメッセージ送信用）

**シーケンス:**
```
Client -> Server: Open SSE connection
Server -> Client: endpoint event
Loop:
  Client -> Server: HTTP POST messages
  Server -> Client: SSE message events
Client -> Server: Close SSE connection
```

#### 2.2 Streamable HTTP（推奨・最新仕様）

**特徴:**
- HTTP+SSEトランスポートを置換
- HTTP POSTとGETリクエストを使用
- オプションでSSEストリーミング対応
- 単一MCPエンドポイントで両メソッドサポート

**エンドポイント要件:**
- サーバーは単一HTTPエンドポイント（例：`https://example.com/mcp`）を提供
- POSTとGETの両メソッドをサポート必須

## セキュリティ要件

### すべてのHTTPトランスポート共通
1. **Originヘッダー検証**: DNS rebinding攻撃防止のため必須
2. **ローカルホストバインド**: ローカル実行時は127.0.0.1のみにバインド推奨
3. **認証実装**: 適切な認証機構の実装推奨

## 実装仕様詳細

### 1. Streamable HTTP通信フロー

#### クライアント→サーバー（メッセージ送信）
```
Method: HTTP POST
Endpoint: MCPエンドポイント
Headers:
  - Accept: application/json, text/event-stream
Body:
  - 単一JSON-RPCリクエスト/通知/レスポンス
  - または配列（バッチ処理）

サーバーレスポンス:
  - レスポンス/通知の場合: HTTP 202 Accepted（本文なし）
  - エラーの場合: HTTP 4xx（オプションでJSON-RPCエラー本文）
  - リクエストの場合:
    - Content-Type: text/event-stream（SSEストリーム開始）
    - Content-Type: application/json（単一JSONオブジェクト）
```

#### クライアント→サーバー（メッセージ受信）
```
Method: HTTP GET
Endpoint: MCPエンドポイント
Headers:
  - Accept: text/event-stream

サーバーレスポンス:
  - 成功: Content-Type: text/event-stream（SSEストリーム開始）
  - 失敗: HTTP 405 Method Not Allowed（SSE非対応の場合）

SSEストリーム内容:
  - JSON-RPCリクエスト・通知（バッチ化可能）
  - 同時実行中のクライアントリクエストと無関係であるべき
  - レスポンス送信まではストリームを閉じるべきではない
  - レスポンス送信後はストリームを閉じるべき
```

### 2. セッション管理

#### セッションID
```
初期化時:
  - サーバーはMcp-Session-Idヘッダーでセッション管理可能
  - セッションIDは暗号学的に安全で全体一意（UUID、JWT、ハッシュ等）
  - ASCII可視文字のみ使用（0x21〜0x7E）

クライアント処理:
  - Mcp-Session-Idが返された場合、以降のリクエストで必須
  - セッションID必須サーバーは、ヘッダーなしで HTTP 400 Bad Request
  - HTTP 404受信時は新セッション開始必須

セッション終了:
  - サーバーは任意時にセッション終了可能
  - 終了セッションIDのリクエストに HTTP 404 Not Found
  - クライアントはHTTP DELETEでセッション明示終了可能
```

### 3. 複数接続とメッセージ配信

```
クライアント:
  - 複数SSEストリーム同時維持可能

サーバー:
  - 各JSON-RPCメッセージは1つのストリームでのみ送信必須
  - 複数ストリーム間での同一メッセージブロードキャスト禁止
  - ストリーム再開可能機能でメッセージ損失リスク軽減可能
```

### 4. ストリーム再開機能

```
サーバーイベントID:
  - SSEイベントにIDフィールド付与可能（ストリーム/セッション単位で一意）

クライアント再開:
  - HTTP GETでMCPエンドポイントにアクセス
  - Last-Event-IDヘッダーで最後受信イベントID指定

サーバー再開処理:
  - Last-Event-IDを使用して切断ストリーム上の未送信メッセージ再送可能
  - 異なるストリーム配信メッセージの再送禁止
  - イベントIDは特定ストリーム内のカーソルとして機能
```

## 後方互換性

### サーバー側
- 新旧両トランスポートのエンドポイント併存ホスト
- 旧POSTエンドポイントと新MCPエンドポイント結合可能（複雑化の可能性）

### クライアント側
1. MCPサーバーURL受け入れ（新旧どちらでも対応）
2. POSTリクエスト試行（Acceptヘッダー付き）
   - 成功: 新Streamable HTTPトランスポートと判定
   - 失敗（HTTP 4xx）: GETリクエストでSSEストリーム期待
     - endpointイベント受信で旧HTTP+SSEトランスポートと判定

## Python実装参考

### SSEサーバー例（Starlette）
```python
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

mcp = FastMCP("My App")

# SSEサーバーを既存ASGIアプリにマウント
app = Starlette(
    routes=[
        Mount('/', app=mcp.sse_app()),
    ]
)
```

### Streamable HTTPサーバー例
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("StatefulServer")
# またはステートレス: FastMCP("StatelessServer", stateless_http=True)

@mcp.tool()
def greet(name: str = "World") -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### クライアント例
```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:8000/mcp") as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
```

## 実装状況

### ✅ 実装完了
1. **--transportパラメータの追加**
   - `--transport sse` : SSE/HTTPトランスポート（デフォルト）
   - `--transport stdio` : stdio トランスポート
   
2. **コマンドライン引数解析の修正**
   - `parse_args()` 関数に `--transport` オプション追加
   - choices=["sse", "stdio"], default="sse"

3. **SSEトランスポート基本実装**
   - `src/worklog_mcp/sse_server.py` に SSEサーバー実装
   - レガシーHTTP+SSE エンドポイント対応 (`/sse`, `/messages`)
   - Streamable HTTP エンドポイント対応 (`/mcp`)
   - CORS設定とセキュリティ考慮

### 使用方法

```bash
# SSEトランスポート（デフォルト）
uv run python -m worklog_mcp

# 明示的にSSE指定
uv run python -m worklog_mcp --transport sse

# stdioトランスポート
uv run python -m worklog_mcp --transport stdio

# MCPサーバーのみ起動（Webサーバーなし）
uv run python -m worklog_mcp --mcp-only --transport sse
```

### エンドポイント

SSEトランスポート使用時（デフォルト: http://127.0.0.1:8000）:
- **レガシーHTTP+SSE**: 
  - SSE: `GET /sse`
  - POST: `POST /messages`
- **Streamable HTTP**:
  - 統合エンドポイント: `GET|POST /mcp`

### 設定変更履歴

- **デフォルトトランスポート**: stdio → **sse** に変更
- **ポート設定**: 
  - 単体実行: 8000（SSE用）
  - 統合実行: 8001（SSE用）、8080（Web用）
- **後方互換性**: 不要（仕様により）

## アーキテクチャ更新

### トランスポート選択フロー
```
main()
├── parse_args() → transport パラメータ取得
├── run_mcp_only_server(transport) 
│   └── run_mcp_server(transport)
│       ├── stdio → mcp.run_stdio_async()
│       └── sse → run_sse_server(mcp)
└── run_integrated_server(transport)
    └── 同様のトランスポート分岐
```