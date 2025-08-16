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


async def run_integrated_server(project_path: str, web_port: int = 8080):
    """MCPサーバーとWebビューアーを独立プロセスで統合起動"""
    import subprocess

    # プロセス管理用
    mcp_process = None
    web_process = None

    try:
        # 実行環境を検出
        env_type = detect_execution_environment()
        logger.info(f"実行環境を検出: {env_type}")

        # MCPサーバープロセス起動
        mcp_cmd = get_execution_command(
            env_type,
            "worklog_mcp.mcp_server",
            ["--project", project_path]
        )
        logger.info(f"MCPサーバープロセス起動: {' '.join(mcp_cmd)}")
        mcp_process = subprocess.Popen(
            mcp_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Webサーバープロセス起動
        web_cmd = get_execution_command(
            env_type,
            "worklog_mcp.web_server",
            ["--project", project_path, "--port", str(web_port)]
        )
        logger.info(f"Webサーバープロセス起動: {' '.join(web_cmd)}")
        web_process = subprocess.Popen(web_cmd)

        logger.info("統合サーバーが起動しました:")
        logger.info(f"  - MCPサーバー: プロセスID {mcp_process.pid}")
        logger.info(
            f"  - Webビューアー: http://localhost:{web_port} (プロセスID {web_process.pid})"
        )

        # プロセス監視
        while True:
            # MCPプロセスの状態確認
            if mcp_process.poll() is not None:
                logger.error("MCPサーバープロセスが終了しました")
                break

            # Webプロセスの状態確認
            if web_process.poll() is not None:
                logger.error("Webサーバープロセスが終了しました")
                break

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("統合サーバーを停止しています...")

    finally:
        # プロセス終了処理
        if mcp_process and mcp_process.poll() is None:
            logger.info("MCPサーバープロセスを終了中...")
            mcp_process.terminate()
            try:
                mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("MCPサーバープロセスの強制終了")
                mcp_process.kill()

        if web_process and web_process.poll() is None:
            logger.info("Webサーバープロセスを終了中...")
            web_process.terminate()
            try:
                web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Webサーバープロセスの強制終了")
                web_process.kill()

        logger.info("統合サーバーが停止されました")


def main():
    """統合起動用メインエントリーポイント"""
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

        # 統合サーバー起動（MCPとWebの両方）
        logger.info(f"統合サーバー起動（Web: http://localhost:{args.web_port}）")
        asyncio.run(run_integrated_server(project_path, args.web_port))

    except KeyboardInterrupt:
        logger.info("統合サーバーが停止されました (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"統合サーバーエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
