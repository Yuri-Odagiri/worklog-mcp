"""Streamable HTTP トランスポート実装"""

import logging

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.routing import Route
from starlette.requests import Request

logger = logging.getLogger(__name__)


class HTTPServer:
    """Streamable HTTP トランスポートサーバー"""

    def __init__(self, mcp_server: FastMCP, host: str = "127.0.0.1", port: int = 8000):
        self.mcp_server = mcp_server
        self.host = host
        self.port = port

    async def run(self):
        """HTTPサーバーを起動"""
        import uvicorn
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        from starlette.routing import Mount
        
        logger.info(f"HTTPサーバーを起動中... http://{self.host}:{self.port}")
        logger.info("エンドポイント:")
        logger.info(f"  - Streamable HTTP: http://{self.host}:{self.port}/mcp")

        # FastMCPのStreamable HTTPアプリケーションを取得
        mcp_app = self.mcp_server.streamable_http_app()
        
        # Starletteアプリケーションを作成してMCPアプリをマウント
        app = Starlette(
            routes=[
                Mount("/mcp", app=mcp_app),
            ]
        )

        # CORS設定
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 本番環境では適切に制限する
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # FastMCPセッションマネージャーのlifespanと共にサーバー実行
        async with self.mcp_server.session_manager.run():
            config = uvicorn.Config(
                app=app, host=self.host, port=self.port, log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()


async def run_http_server(
    mcp_server: FastMCP, host: str = "127.0.0.1", port: int = 8000
):
    """HTTPサーバーを起動"""
    http_server = HTTPServer(mcp_server, host, port)
    await http_server.run()
