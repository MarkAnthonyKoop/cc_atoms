"""Central configuration for cc_atoms project."""
from pathlib import Path
from enum import Enum
import os


class DecompositionLevel(Enum):
    """How aggressively to decompose tasks"""
    NONE = "none"          # No decomposition, single atom
    LIGHT = "light"        # Only if clearly needed (massive tasks)
    STANDARD = "standard"  # Decompose complex+ tasks
    AGGRESSIVE = "aggressive"  # Decompose everything into atomic steps (MAD-style)


# Directory structure
ATOMS_HOME = Path.home() / "cc_atoms"
BIN_DIR = ATOMS_HOME / "bin"
TOOLS_DIR = ATOMS_HOME / "tools"
PROMPTS_DIR = ATOMS_HOME / "prompts"
TESTS_DIR = ATOMS_HOME / "tests"
META_AGENTS_DIR = PROMPTS_DIR / "meta_agents"  # For critic, verifier, etc.

# Package prompts directory (bundled with the package)
PACKAGE_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Search paths for tools and prompts
# Priority: project-local → global → package → user override
TOOL_SEARCH_PATHS = [
    Path.cwd() / ".atom",                          # Project-local (highest priority)
    TOOLS_DIR,                                     # Global cc_atoms tools
    Path(os.getenv("ATOM_TOOLS_PATH", "/nonexistent"))  # User override via env var
]

PROMPT_SEARCH_PATHS = [
    Path.cwd() / ".atom" / "prompts",              # Project-local prompts
    PROMPTS_DIR,                                   # Global prompts (~/.cc_atoms/prompts)
    PACKAGE_PROMPTS_DIR,                           # Package-bundled prompts
    Path(os.getenv("ATOM_PROMPTS_PATH", "/nonexistent"))  # User override via env var
]

# Iteration settings
MAX_ITERATIONS = 25
EXIT_SIGNAL = "EXIT_LOOP_NOW"

# Retry settings
NETWORK_ERROR_KEYWORDS = ["network", "timeout", "connection", "temporary"]
NETWORK_RETRY_BASE = 5  # seconds
NETWORK_RETRY_MAX = 300  # 5 minutes
OTHER_RETRY_BASE = 10  # seconds
OTHER_RETRY_MAX = 600  # 10 minutes
SESSION_LIMIT_BUFFER = 300  # 5 minutes buffer after reset time

# Default wait times (when can't parse)
DEFAULT_SESSION_LIMIT_WAIT = 3600  # 1 hour

# Task analysis settings
DECOMPOSITION_LEVEL = DecompositionLevel.STANDARD  # Default decomposition behavior
FORCE_COMPLEX = False  # For testing: treat all tasks as complex
USE_TASK_ANALYZER = True  # Enable AI-based task analysis
MIN_ITERATIONS_FOR_REVIEW = 3  # Spawn critic if estimated >= this

# Meta-agent settings
USE_META_AGENTS = True  # Enable critic, verifier, etc.
ALWAYS_VERIFY = False  # Always run verifier before EXIT_LOOP_NOW
REQUIRE_TESTS_FOR_COMPLEX = True  # Complex tasks must have tests

# Quality gate settings
QUALITY_CHECK_ENABLED = True  # Check for red flags before accepting EXIT
RED_FLAG_PATTERNS = [
    "todo:",
    "fixme:",
    "hack:",
    "i'm not sure",
    "this might not work",
    "untested",
]
