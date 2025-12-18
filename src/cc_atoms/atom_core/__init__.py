"""
atom_core - Embeddable atom orchestration

Provides iteration, retry, and context management for Claude Code sessions
that can be embedded in any tool or project.

v3 additions:
- TaskAnalyzer for complexity evaluation
- Smart memory queries based on task semantics
- Meta-agent support (critic, verifier, planner)
- Quality gates before accepting completion
"""

from .runtime import AtomRuntime
from .retry import RetryManager
from .context import IterationHistory
from .prompt_loader import PromptLoader
from .claude_runner import ClaudeRunner
from .memory import MemoryProvider, check_memory_available, get_memory_provider
from .task_analyzer import (
    TaskAnalyzer,
    TaskAnalysis,
    AnalyzerConfig,
    ComplexityLevel,
)
# DecompositionLevel is defined in config to avoid circular imports
from cc_atoms.config import DecompositionLevel

__version__ = "3.0.0"

__all__ = [
    # Core
    "AtomRuntime",
    "RetryManager",
    "IterationHistory",
    "PromptLoader",
    "ClaudeRunner",
    # Memory
    "MemoryProvider",
    "check_memory_available",
    "get_memory_provider",
    # v3: Task Analysis
    "TaskAnalyzer",
    "TaskAnalysis",
    "AnalyzerConfig",
    "ComplexityLevel",
    "DecompositionLevel",
]
