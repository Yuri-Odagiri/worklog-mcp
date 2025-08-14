#!/usr/bin/env python3
"""
データベース初期化スクリプト
worklog-mcpプロジェクトのデータベースを初期化します
"""

import asyncio
import logging
from pathlib import Path
import sys
import argparse

# プロジェクトルートのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from worklog_mcp.database import Database
from worklog_mcp.logging_config import setup_logging

# ログ設定
setup_logging()
logger = logging.getLogger(__name__)


async def init_database(project_name: str, force: bool = False):
    """データベースを初期化する

    Args:
        project_name: プロジェクト名
        force: 既存のデータベースを削除して再作成するかどうか
    """
    db_path = Path.home() / ".worklog" / project_name / "database" / "worklog.db"

    # 既存のデータベースがある場合の処理
    if db_path.exists():
        if force:
            logger.info(f"既存のデータベース {db_path} を削除します...")
            db_path.unlink()
        else:
            logger.info(f"データベース {db_path} は既に存在します。")
            logger.info(
                "強制的に再作成する場合は --force オプションを使用してください。"
            )
            return

    # データベースディレクトリを作成
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"データベースを初期化中: {db_path}")

    # Database クラスを使って初期化
    db_file_path = str(
        Path.home() / ".worklog" / project_name / "database" / "worklog.db"
    )
    db = Database(db_file_path)
    await db.initialize()

    logger.info("データベース初期化完了！")
    logger.info(f"場所: {db_path}")

    # テーブル情報を表示
    import aiosqlite

    async with aiosqlite.connect(db_file_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = await cursor.fetchall()
        logger.info("\n作成されたテーブル:")
        for table in tables:
            logger.info(f"  - {table[0]}")

            # 各テーブルのカラム情報を表示
            col_cursor = await conn.execute(f"PRAGMA table_info({table[0]})")
            columns = await col_cursor.fetchall()
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                not_null = "NOT NULL" if col[3] else ""
                pk = "PRIMARY KEY" if col[5] else ""
                constraints = " ".join(filter(None, [not_null, pk]))
                logger.info(f"      {col_name} {col_type} {constraints}".strip())

        # インデックス情報を表示
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        indexes = await cursor.fetchall()
        if indexes:
            logger.info("\n作成されたインデックス:")
            for index in indexes:
                logger.info(f"  - {index[0]}")


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="worklog-mcpプロジェクトのデータベースを初期化します"
    )
    parser.add_argument(
        "--project",
        "-p",
        default="worklog-mcp",
        help="プロジェクト名 (デフォルト: worklog-mcp)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="既存のデータベースを削除して再作成"
    )

    args = parser.parse_args()

    try:
        asyncio.run(init_database(args.project, args.force))
    except KeyboardInterrupt:
        logger.info("\n処理を中断しました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        logger.debug("エラー詳細", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
