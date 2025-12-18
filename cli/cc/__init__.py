"""CC CLI - A Claude Code CLI clone.

A Python-based clone of the Claude Code CLI that provides interactive
conversation with Claude, tool execution, and session management.
"""

__version__ = "0.1.0"
__author__ = "CC CLI Project"

from .main import main
from .app import Application, AppConfig, create_app_from_args
from .conversation import Conversation
from .repl import REPL
from .config.settings import Settings
from .session.manager import SessionManager
from .hooks.hooks import HooksManager, HookEvent
from .tools import ToolExecutor, ToolRegistry, PermissionChecker
from .api import APIClient

__all__ = [
    "main",
    "__version__",
    "Application",
    "AppConfig",
    "create_app_from_args",
    "Conversation",
    "REPL",
    "Settings",
    "SessionManager",
    "HooksManager",
    "HookEvent",
    "ToolExecutor",
    "ToolRegistry",
    "PermissionChecker",
    "APIClient",
]
