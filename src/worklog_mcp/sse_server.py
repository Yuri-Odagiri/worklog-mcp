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
        
        logger.info(f"HTTPサーバーを起動中... http://{self.host}:{self.port}")
        logger.info("エンドポイント:")
        logger.info(f"  - Streamable HTTP: http://{self.host}:{self.port}/mcp")

        # FastMCPのStreamable HTTPアプリケーションを直接使用
        app = self.mcp_server.streamable_http_app()

        # FastMCPアプリが自身でライフサイクルを管理するため、手動起動は不要
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
