"""
atom_create_tool - Generate new atom-based tools

Usage:
    atom-create-tool                    # Interactive mode
    atom-create-tool "description"      # AI-assisted mode
"""

from .atom_create_tool import main

__all__ = ["main"]
