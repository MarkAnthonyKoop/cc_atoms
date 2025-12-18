"""
atom_session_analyzer - Extract and analyze Claude Code sessions

Usage:
    atom-session-analyzer                    # Extract current session log
    atom-session-analyzer [args...]          # Pass args to atom with session context
"""

from .atom_session_analyzer import main

__all__ = ["main"]
