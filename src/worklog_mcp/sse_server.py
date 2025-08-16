"""Streamable HTTP トランスポート実装"""

import logging
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class HTTPServer:
    """Streamable HTTP トランスポートサーバー"""

    def __init__(
        self, db, project_context, event_bus, host: str = "127.0.0.1", port: int = 8000
    ):
        self.db = db
        self.project_context = project_context
        self.event_bus = event_bus
        self.host = host
        self.port = port

    async def run(self):
        """HTTPサーバーを起動"""
        import uvicorn

        logger.info(f"HTTPサーバーを起動中... http://{self.host}:{self.port}")
        logger.info("エンドポイント:")
        logger.info(f"  - Streamable HTTP: http://{self.host}:{self.port}/mcp")

        # HTTP専用のFastMCPインスタンスを作成
        from .server import create_server

        mcp_server = await create_server(self.db, self.project_context, self.event_bus)

        # FastMCPのStreamable HTTPアプリケーションを取得
        app = mcp_server.streamable_http_app()

        # FastMCPアプリが自身でライフサイクルを管理するため、手動起動は不要
        config = uvicorn.Config(
            app=app, host=self.host, port=self.port, log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


async def run_http_server(
    mcp_server: FastMCP, host: str = "127.0.0.1", port: int = 8000
):
    """HTTPサーバーを起動（レガシー関数 - 新しい形式を推奨）"""
    # この関数は後方互換性のために保持
    # 実際には新しいHTTPServerクラスを使用することを推奨
    logger.warning(
        "run_http_server関数は廃止予定です。新しいHTTPServerクラスを使用してください。"
    )

    import uvicorn

    logger.info(f"HTTPサーバーを起動中... http://{host}:{port}")
    logger.info("エンドポイント:")
    logger.info(f"  - Streamable HTTP: http://{host}:{port}/mcp")

    # FastMCPのStreamable HTTPアプリケーションを取得
    app = mcp_server.streamable_http_app()

    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_http_server_with_context(
    db, project_context, event_bus, host: str = "127.0.0.1", port: int = 8000
):
    """HTTPサーバーをコンテキストから起動"""
    http_server = HTTPServer(db, project_context, event_bus, host, port)
    await http_server.run()
