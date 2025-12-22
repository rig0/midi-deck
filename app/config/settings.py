"""
Application Settings and Configuration

Provides centralized configuration management, logging setup,
and path utilities for the MIDI Deck application.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path: Absolute path to the project root directory
    """
    # Assumes this file is at app/config/settings.py
    # So project root is two levels up
    return Path(__file__).parent.parent.parent.resolve()


def get_data_dir() -> Path:
    """
    Get the data directory path.

    Returns:
        Path: Absolute path to the data directory
    """
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_log_dir() -> Path:
    """
    Get the logs directory path.

    Returns:
        Path: Absolute path to the logs directory
    """
    log_dir = get_project_root() / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


def setup_logging(log_level=None) -> logging.Logger:
    """
    Setup the logging system with console and file handlers.

    Configures a rotating file handler and console output with
    consistent formatting across the application.

    Args:
        log_level: Optional logging level (DEBUG, INFO, WARNING, ERROR)
                  Defaults to INFO if not specified

    Returns:
        logging.Logger: Configured root logger instance
    """
    # Determine log level
    if log_level is None:
        log_level = os.environ.get("MIDI_DECK_LOG_LEVEL", "INFO")

    # Convert string to logging level constant
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler
    log_file = get_log_dir() / "midi_deck.log"
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,  # 5MB per file
        backupCount=3,  # Keep 3 backups
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized at level: {logging.getLevelName(log_level)}")
    logger.debug(f"Log file: {log_file}")

    return logger


def get_config(key: str, default=None):
    """
    Get a configuration value.

    In Phase 1, this returns default values or environment variables.
    In Phase 2, this will be updated to read from the database.

    Args:
        key: Configuration key to retrieve
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    # TODO: Phase 2 - Read from database
    # For now, check environment variables or return default
    env_key = f"MIDI_DECK_{key.upper()}"
    return os.environ.get(env_key, default)
