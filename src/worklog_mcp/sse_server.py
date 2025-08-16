"""Streamable HTTP トランスポート実装"""

import asyncio
import json
import logging
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route
from starlette.requests import Request

logger = logging.getLogger(__name__)


class HTTPServer:
    """Streamable HTTP トランスポートサーバー"""

    def __init__(self, mcp_server: FastMCP, host: str = "127.0.0.1", port: int = 8000):
        self.mcp_server = mcp_server
        self.host = host
        self.port = port
        self.app = self._create_app()

    def _create_app(self) -> Starlette:
        """Starletteアプリケーションを作成"""
        routes = [
            Route(
                "/mcp", self._handle_mcp_endpoint, methods=["GET", "POST"]
            ),  # Streamable HTTP endpoint
        ]

        app = Starlette(routes=routes)

        # CORS設定
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 本番環境では適切に制限する
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app

    async def _handle_mcp_endpoint(self, request: Request) -> Response:
        """Streamable HTTPエンドポイント"""
        if request.method == "GET":
            return await self._handle_streamable_get(request)
        elif request.method == "POST":
            return await self._handle_streamable_post(request)
        else:
            return Response(status_code=405)

    async def _handle_streamable_get(self, request: Request) -> StreamingResponse:
        """Streamable HTTP GETハンドラー（SSEストリーム）"""
        accept_header = request.headers.get("accept", "")

        if "text/event-stream" not in accept_header:
            return Response(status_code=405)  # Method Not Allowed

        logger.info("Streamable HTTP SSE stream established")

        async def streamable_event_stream():
            try:
                # 継続的にサーバーからのメッセージを送信
                while True:
                    # TODO: 実際のMCPメッセージ処理を実装
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Streamable SSE stream error: {e}")
            finally:
                logger.info("Streamable SSE connection closed")

        return StreamingResponse(
            streamable_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    async def _handle_streamable_post(self, request: Request) -> Response:
        """Streamable HTTP POSTハンドラー"""
        try:
            accept_header = request.headers.get("accept", "")
            data = await request.json()

            logger.debug(f"Received Streamable POST: {data}")

            # JSON-RPCメッセージの種類に応じて処理
            if "method" in data:
                # リクエストの場合
                if "text/event-stream" in accept_header:
                    # SSEストリームでレスポンス
                    return await self._handle_request_with_sse(data)
                else:
                    # 単一JSONレスポンス
                    return await self._handle_request_with_json(data)
            else:
                # 通知またはレスポンスの場合
                # TODO: 実際の処理を実装
                return Response(status_code=202)  # Accepted

        except Exception as e:
            logger.error(f"Streamable POST error: {e}")
            return Response(status_code=400, content=str(e))

    async def _handle_request_with_sse(
        self, request_data: Dict[str, Any]
    ) -> StreamingResponse:
        """リクエストをSSEストリームで処理"""

        async def request_stream():
            try:
                # TODO: 実際のMCPリクエスト処理とレスポンス送信
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "result": {},
                }
                yield f"data: {json.dumps(response_data)}\n\n"
            except Exception as e:
                logger.error(f"Request stream error: {e}")

        return StreamingResponse(
            request_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    async def _handle_request_with_json(self, request_data: Dict[str, Any]) -> Response:
        """リクエストを単一JSONレスポンスで処理"""
        try:
            # TODO: 実際のMCPリクエスト処理
            response_data = {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {},
            }
            return Response(
                content=json.dumps(response_data), media_type="application/json"
            )
        except Exception as e:
            logger.error(f"JSON request error: {e}")
            return Response(status_code=500, content=str(e))

    async def run(self):
        """HTTPサーバーを起動"""
        import uvicorn

        logger.info(f"HTTPサーバーを起動中... http://{self.host}:{self.port}")
        logger.info("エンドポイント:")
        logger.info(f"  - Streamable HTTP: http://{self.host}:{self.port}/mcp")

        config = uvicorn.Config(
            app=self.app, host=self.host, port=self.port, log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


async def run_http_server(
    mcp_server: FastMCP, host: str = "127.0.0.1", port: int = 8000
):
    """HTTPサーバーを起動"""
    http_server = HTTPServer(mcp_server, host, port)
    await http_server.run()