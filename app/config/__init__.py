"""
Configuration Management Module

Handles application settings, logging configuration, and path management.
"""

from .settings import (
    get_config,
    get_data_dir,
    get_log_dir,
    get_project_root,
    setup_logging,
)

__all__ = [
    "setup_logging",
    "get_config",
    "get_project_root",
    "get_data_dir",
    "get_log_dir",
]
