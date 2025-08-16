"""メインエントリーポイント"""

import sys
import logging
import argparse
import os
import asyncio
import shutil
from pathlib import Path
# 統合起動のため、個別インポートは不要


# ログ設定
from .logging_config import setup_logging

# ログ設定を実行
log_file_path = setup_logging()

logger = logging.getLogger(__name__)


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="分報MCPサーバー（統合起動：MCPとWebビューアーの両方）"
    )
    parser.add_argument(
        "--project",
        type=str,
        help="プロジェクトディレクトリのパス（指定されない場合は現在のディレクトリを使用）",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8080,
        help="Webサーバーポート（デフォルト: 8080）",
    )
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="MCPサーバーのみを起動（Webサーバーなし）",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser.parse_args()


def detect_execution_environment():
    """実行環境を検出する (uvx, uv run, 通常のPython)"""
    # uvx環境の検出
    if "uv" in sys.executable and "archive-v0" in sys.executable:
        return "uvx"
    
    # uv run環境の検出
    if "UV_PROJECT_ENVIRONMENT" in os.environ or ".venv" in sys.executable:
        return "uv_run"
    
    return "python"


def get_execution_command(env_type: str, module: str, args: list):
    """環境に応じた実行コマンドを生成"""
    if env_type == "uvx":
        # uvx環境では現在のPython実行可能ファイルを使用
        return [sys.executable, "-m", module] + args
    elif env_type == "uv_run":
        # uv run環境
        return ["uv", "run", "python", "-m", module] + args
    else:
        # 通常のPython環境
        return [sys.executable, "-m", module] + args


async def run_mcp_only_server(project_path: str):
    """MCPサーバー単体を起動"""
    from .mcp_server import run_mcp_server
    
    logger.info("MCPサーバー単体モードで起動")
    await run_mcp_server(project_path)


async def run_integrated_server(project_path: str, web_port: int = 8080):
    """MCPサーバー（メインプロセス）+ Webサーバー（別プロセス）の統合起動"""
    import subprocess
    from .database import Database
    from .event_bus import EventBus
    from .project_context import ProjectContext
    from .server import create_server

    web_process = None

    try:
        # 実行環境を検出
        env_type = detect_execution_environment()
        logger.info(f"実行環境を検出: {env_type}")

        # プロジェクトコンテキストの初期化
        project_context = ProjectContext(project_path)
        project_context.initialize_project_directories()

        # データベースの初期化
        db_path = project_context.get_database_path()
        db = Database(db_path)
        await db.initialize()

        # 初回起動チェック
        if await db.is_first_run():
            project_info = project_context.get_project_info()
            logger.info(
                f"プロジェクト '{project_info['project_name']}' の初回起動を検出しました。ユーザー登録が必要です。"
            )

        # イベントバスの初期化
        event_bus_path = project_context.get_eventbus_database_path()
        event_bus = EventBus(event_bus_path)
        await event_bus.initialize()

        # Webサーバープロセス起動
        web_cmd = get_execution_command(
            env_type,
            "worklog_mcp.web_server",
            ["--project", project_path, "--port", str(web_port)]
        )
        logger.info(f"Webサーバープロセス起動: {' '.join(web_cmd)}")
        web_process = subprocess.Popen(web_cmd)

        logger.info("統合サーバーが起動しました:")
        logger.info("  - MCPサーバー: メインプロセス (stdio通信)")
        logger.info(f"  - Webビューアー: http://localhost:{web_port} (プロセスID {web_process.pid})")

        # MCPサーバーをメインプロセスで実行
        mcp = await create_server(db, project_context, event_bus)
        logger.info(f"MCPサーバー起動 (プロジェクト: {project_context.get_project_name()})")
        
        # stdio通信でMCPサーバー実行
        await mcp.run_stdio_async()

    except KeyboardInterrupt:
        logger.info("統合サーバーを停止しています...")
    except Exception as e:
        logger.error(f"統合サーバーエラー: {e}")
        raise
    finally:
        # Webプロセス終了処理
        if web_process and web_process.poll() is None:
            logger.info("Webサーバープロセスを終了中...")
            web_process.terminate()
            try:
                web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Webサーバープロセスの強制終了")
                web_process.kill()

        # クリーンアップ
        if "event_bus" in locals():
            await event_bus.close()
        if "db" in locals():
            await db.close()

        logger.info("統合サーバーが停止されました")


def main():
    """メインエントリーポイント"""
    try:
        args = parse_args()

        # プロジェクトパスの設定
        project_path = args.project if args.project else os.getcwd()

        if args.project:
            logger.info(f"プロジェクトモードで開始: {args.project}")
        else:
            logger.info(
                f"プロジェクトモードで開始（現在のディレクトリ）: {project_path}"
            )

        if args.mcp_only:
            # MCPサーバー単体モード
            logger.info("MCPサーバー単体モード")
            asyncio.run(run_mcp_only_server(project_path))
        else:
            # 統合サーバーモード（MCP + Web）
            logger.info(f"統合サーバー起動（Web: http://localhost:{args.web_port}）")
            asyncio.run(run_integrated_server(project_path, args.web_port))

    except KeyboardInterrupt:
        logger.info("サーバーが停止されました (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"サーバーエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
