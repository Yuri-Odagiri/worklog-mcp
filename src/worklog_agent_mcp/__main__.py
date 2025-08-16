"""Worklog Agent MCP Server エントリーポイント"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# モジュールパスの設定
def setup_module_path():
    """モジュールパスを適切に設定"""
    current_dir = Path(__file__).parent
    # 開発環境の場合、プロジェクトルートを追加
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

setup_module_path()

from worklog_mcp.database import Database
from worklog_mcp.project_context import ProjectContext
from worklog_mcp.logging_config import setup_logging

from .server import create_agent_server

# ログ設定
log_file_path = setup_logging()
logger = logging.getLogger(__name__)


async def run_stdio_server(project_path: str, user_id: str = None):
    """Stdio transport でサーバーを実行"""
    
    # プロジェクトコンテキスト初期化
    project_context = ProjectContext(project_path)
    
    # データベース初期化
    database = Database(project_context.get_database_path())
    await database.initialize(project_context)
    
    # サーバー作成
    server = create_agent_server(project_path, user_id)
    
    logger.info(f"Agent MCP Server (stdio) starting for project: {project_path}")
    
    # Stdio transport で実行
    await server.run_stdio_async()


async def run_http_server(project_path: str, host: str = "127.0.0.1", port: int = 8002, user_id: str = None):
    """HTTP transport でサーバーを実行"""
    
    # プロジェクトコンテキスト初期化
    project_context = ProjectContext(project_path)
    
    # データベース初期化
    database = Database(project_context.get_database_path())
    await database.initialize(project_context)
    
    # サーバー作成
    server = create_agent_server(project_path, user_id)
    
    logger.info(f"Agent MCP Server (HTTP) starting on http://{host}:{port}/mcp")
    
    # HTTPサーバー実行
    import uvicorn
    
    # FastMCPのStreamable HTTPアプリケーションを取得
    app = server.streamable_http_app()
    
    config = uvicorn.Config(
        app=app, host=host, port=port, log_level="info"
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


def main():
    """メイン関数"""
    
    parser = argparse.ArgumentParser(description="Worklog Agent MCP Server")
    parser.add_argument("--project", "-p", required=True, help="プロジェクトパス")
    parser.add_argument("--user", "-u", help="ユーザーID")
    parser.add_argument("--transport", "-t", choices=["stdio", "http"], default="stdio", 
                       help="Transport type (default: stdio)")
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport")
    parser.add_argument("--port", type=int, default=8002, help="Port for HTTP transport")
    
    args = parser.parse_args()
    
    # プロジェクトパスの検証
    project_path = Path(args.project).resolve()
    if not project_path.exists():
        print(f"エラー: プロジェクトパスが存在しません: {project_path}")
        exit(1)
    
    # Transport に応じてサーバーを実行
    try:
        if args.transport == "stdio":
            asyncio.run(run_stdio_server(str(project_path), args.user))
        elif args.transport == "http":
            asyncio.run(run_http_server(str(project_path), args.host, args.port, args.user))
    except KeyboardInterrupt:
        logger.info("Agent MCP Server stopped")
    except Exception as e:
        logger.error(f"Agent MCP Server error: {e}")
        raise
    finally:
        logger.info("Agent MCP Server shutdown complete")


if __name__ == "__main__":
    main()