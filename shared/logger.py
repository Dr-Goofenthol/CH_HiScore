"""
Logging utilities for client and bot

Provides file-based error logging while keeping console output clean.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_file: Path, level=logging.INFO) -> logging.Logger:
    """
    Set up a logger with file and console handlers

    Args:
        name: Logger name (e.g., 'client', 'bot')
        log_file: Path to log file
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Create log directory if needed
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # File handler - detailed logging
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    logger.addHandler(file_handler)

    return logger


def log_exception(logger: logging.Logger, message: str, exc: Exception):
    """
    Log an exception with full traceback to file

    Args:
        logger: Logger instance
        message: User-friendly error message
        exc: Exception object
    """
    logger.error(f"{message}: {exc}", exc_info=True)


def get_client_logger() -> logging.Logger:
    """Get logger for client application"""
    # Log to Clone Hero directory for easy access
    try:
        import os
        if sys.platform == 'win32':
            ch_docs = Path.home() / 'Documents' / 'Clone Hero'
        else:
            ch_docs = Path.home() / '.clone_hero'

        log_file = ch_docs / 'score_tracker.log'
    except Exception:
        # Fallback to current directory
        log_file = Path('client.log')

    return setup_logger('client', log_file)


def get_bot_logger() -> logging.Logger:
    """Get logger for bot application"""
    # Log to bot config directory
    try:
        import os
        if sys.platform == 'win32':
            appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            log_dir = appdata / 'CloneHeroScoreBot'
        else:
            log_dir = Path.home() / '.config' / 'CloneHeroScoreBot'

        log_file = log_dir / 'bot.log'
    except Exception:
        # Fallback to current directory
        log_file = Path('bot.log')

    return setup_logger('bot', log_file)


def rotate_log_if_needed(log_file: Path, max_size_mb: int = 10):
    """
    Rotate log file if it exceeds max size

    Args:
        log_file: Path to log file
        max_size_mb: Maximum size in megabytes before rotation
    """
    if not log_file.exists():
        return

    max_bytes = max_size_mb * 1024 * 1024
    if log_file.stat().st_size > max_bytes:
        # Rename old log
        backup_name = f"{log_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        backup_path = log_file.parent / backup_name
        log_file.rename(backup_path)

        # Keep only last 5 backups
        backups = sorted(log_file.parent.glob(f"{log_file.stem}_*.log"))
        for old_backup in backups[:-5]:
            old_backup.unlink()
