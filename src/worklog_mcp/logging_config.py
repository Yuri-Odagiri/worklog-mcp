"""ログ設定の共通モジュール"""

import sys
import logging
from pathlib import Path
from typing import Optional


_setup_done = False
_log_file_path: Optional[Path] = None


def setup_logging() -> Path:
    """ログ設定を初期化

    Returns:
        ログファイルのパス
    """
    global _setup_done, _log_file_path

    if _setup_done:
        return _log_file_path

    # ログディレクトリを作成
    log_dir = Path.home() / ".worklog"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "logfile.log"
    _log_file_path = log_file

    # ログフォーマット
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # コンソールハンドラー（DEBUG以上）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ファイルハンドラー（DEBUG以上）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    _setup_done = True

    # aiosqliteのDEBUGログを非表示にする
    aiosqlite_logger = logging.getLogger("aiosqlite")
    aiosqlite_logger.setLevel(logging.INFO)

    # 初期化完了のログ
    logger = logging.getLogger(__name__)
    logger.info(f"ログ設定初期化完了: {log_file}")

    return log_file


def get_log_file_path() -> Optional[Path]:
    """現在のログファイルパスを取得

    Returns:
        ログファイルのパス（未初期化の場合はNone）
    """
    return _log_file_path
