"""Agent MCP Server - Claude Code Agent管理専用サーバー"""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from worklog_mcp.database import Database
from worklog_mcp.project_context import ProjectContext
from worklog_mcp.logging_config import setup_logging

from .tools.agent_management import register_agent_tools

# ログ設定
setup_logging()
logger = logging.getLogger(__name__)


def create_agent_server(project_path: str, user_id: Optional[str] = None) -> FastMCP:
    """Agent MCP サーバーを作成"""
    
    # プロジェクトコンテキスト初期化
    project_context = ProjectContext(project_path)
    
    # データベース初期化
    database = Database(project_context.get_database_path())
    
    # FastMCPサーバー作成
    server = FastMCP("Worklog Agent MCP Server")
    
    # エージェント管理ツールを登録
    register_agent_tools(server, database, project_context, user_id)
    
    logger.info(f"Agent MCP Server initialized for project: {project_path}")
    
    return server


async def initialize_agent_server(project_path: str, user_id: Optional[str] = None) -> FastMCP:
    """Agent MCP サーバーを初期化"""
    
    # プロジェクトコンテキスト初期化
    project_context = ProjectContext(project_path)
    
    # データベース初期化
    database = Database(project_context.get_database_path())
    await database.initialize(project_context)
    
    # サーバー作成
    server = create_agent_server(project_path, user_id)
    
    logger.info(f"Agent MCP Server fully initialized for project: {project_path}")
    
    return server