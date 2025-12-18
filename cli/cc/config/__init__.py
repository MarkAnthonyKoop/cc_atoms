"""Configuration module for settings management."""

from .settings import Settings
from .paths import (
    get_config_dir,
    get_project_dir,
    get_session_file,
    find_claude_md,
    ensure_config_dirs,
)

__all__ = [
    "Settings",
    "get_config_dir",
    "get_project_dir",
    "get_session_file",
    "find_claude_md",
    "ensure_config_dirs",
]
