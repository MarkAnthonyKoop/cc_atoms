"""
cc_atoms - Autonomous Claude Code Orchestration System

This package provides tools for running iterative AI sessions with
automatic context accumulation, retry logic, and task decomposition.

Main components:
- atom_core: Embeddable orchestration library
- cli: Command-line interface (atom command)
- tools: Specialized tools (atom_gui, gui_control, etc.)
"""

from cc_atoms.atom_core import (
    AtomRuntime,
    PromptLoader,
    RetryManager,
    IterationHistory,
    ClaudeRunner,
)

__version__ = "2.0.0"

__all__ = [
    "AtomRuntime",
    "PromptLoader",
    "RetryManager",
    "IterationHistory",
    "ClaudeRunner",
    "__version__",
]
