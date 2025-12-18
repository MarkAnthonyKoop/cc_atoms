# CC_ATOMS - Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Library: atom_core](#core-library-atom_core)
4. [CLI Interface: atom.py](#cli-interface-atompy)
5. [Configuration: config.py](#configuration-configpy)
6. [Tools Ecosystem](#tools-ecosystem)
7. [Prompt System](#prompt-system)
8. [Directory Structure](#directory-structure)
9. [Workflows](#workflows)
10. [Development Guide](#development-guide)

---

## Overview

**cc_atoms** is an autonomous orchestration system for Claude Code sessions. It enables AI-powered iterative problem solving through decomposition, specialized tools, and context accumulation.

### Key Concepts

- **Atom**: An autonomous Claude Code session that runs in iterations until task completion
- **Decomposition**: Breaking complex tasks into sub-atoms (subdirectories with their own sessions)
- **Tools**: Reusable Python scripts that extend atom capabilities
- **Prompts**: Specialized system prompts that configure atom behavior
- **Context Accumulation**: Each iteration builds on previous work via `claude -c`

### Design Philosophy

1. **Iteration over Perfection**: Make progress in small steps, refine iteratively
2. **Decomposition**: Break down complexity into manageable sub-problems
3. **Embeddable Core**: `atom_core` library can be used in any project
4. **Tool Reuse**: Build reusable capabilities that work across projects
5. **Fail-Safe**: Retry logic handles network errors and session limits

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Request                                    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   atom CLI      │     │   gui_control   │     │  Custom Tool    │
│   (atom.py)     │     │   (embedded)    │     │  (embedded)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            atom_core Library                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AtomRuntime                                  │   │
│  │  • Iteration loop (1 to max_iterations)                             │   │
│  │  • Completion detection (EXIT_LOOP_NOW)                             │   │
│  │  • Error handling with structured results                           │   │
│  │  • create_ephemeral() for temporary sessions                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│         ┌───────────────────────┼───────────────────────┐                  │
│         ▼                       ▼                       ▼                  │
│  ┌─────────────┐       ┌──────────────┐       ┌──────────────┐            │
│  │PromptLoader │       │ RetryManager │       │ ClaudeRunner │            │
│  │             │       │              │       │              │            │
│  │• Search     │       │• Exponential │       │• Subprocess  │            │
│  │  paths      │       │  backoff     │       │  execution   │            │
│  │• Compose    │       │• Session     │       │• claude -c   │            │
│  │  prompts    │       │  limits      │       │  -p prompt   │            │
│  └─────────────┘       │• Callbacks   │       └──────────────┘            │
│         │              └──────────────┘              │                     │
│         ▼                                            ▼                     │
│  ┌─────────────┐                            ┌──────────────┐               │
│  │IterationHist│                            │ Claude Code  │               │
│  │             │                            │  (external)  │               │
│  │• Track      │                            └──────────────┘               │
│  │  iterations │                                                           │
│  │• Timestamps │                                                           │
│  └─────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input**: USER_PROMPT.md specifies task (or inline prompt)
2. **Processing**: AtomRuntime runs iterations, calling Claude Code with context
3. **State**: Each iteration accumulates via `claude -c` flag
4. **Output**: Files created, task completion signaled with EXIT_LOOP_NOW
5. **Result**: Structured dict with success, iterations, output, duration

---

## Core Library: atom_core

The `atom_core` package provides embeddable orchestration for any Python project.

### Module: runtime.py (AtomRuntime)

**Purpose**: Main orchestration engine

**Class: AtomRuntime**
```python
class AtomRuntime:
    def __init__(
        self,
        system_prompt: str,
        conversation_dir: Path,       # Critical: determines conversation identity
        max_iterations: int = 25,
        exit_signal: str = "EXIT_LOOP_NOW",
        verbose: Optional[bool] = None,  # None = auto-detect (tty)
        cleanup: bool = False         # Delete USER_PROMPT.md after completion
    )

    @classmethod
    def create_ephemeral(cls, system_prompt: str, **kwargs) -> 'AtomRuntime':
        """Create runtime with temporary conversation directory"""

    def run(self, user_prompt: str) -> Dict[str, Any]:
        """
        Execute iterations until completion or max_iterations.

        Returns:
            {
                "success": bool,
                "iterations": int,
                "output": str,
                "duration": float,
                "context": List[dict],
                "reason": str,          # If failed
                "error": Optional[str]  # If exception
            }
        """
```

**Key Features**:
- Smart verbose detection (auto-detect terminal)
- Comprehensive error handling (FileNotFoundError, PermissionError, etc.)
- Cleanup option for ephemeral sessions
- Duration tracking

### Module: retry.py (RetryManager)

**Purpose**: Handle transient failures with exponential backoff

```python
class RetryManager:
    def __init__(self, on_retry_message: Optional[Callable] = None):
        """
        Args:
            on_retry_message: Callback for retry messages (default: print)
                             Set to lambda msg, sec: None for silent
        """

    def check(self, stdout: str, returncode: int, attempt: int) -> Tuple[bool, int]:
        """
        Check if should retry.

        Returns:
            (should_retry: bool, wait_seconds: int)
        """
```

**Retry Logic**:
- **Success (returncode=0)**: No retry
- **Session limit**: Parse reset time, wait until then + buffer
- **Network errors**: Exponential backoff (5, 10, 20... max 300s)
- **Other errors**: Exponential backoff (10, 20, 40... max 600s)

### Module: context.py (IterationHistory)

**Purpose**: Track iteration results for inspection/debugging

```python
class IterationHistory:
    def add_iteration(self, iteration: int, result: Dict[str, Any]):
        """Add iteration with timestamp"""

    def get_all_iterations(self) -> List[Dict[str, Any]]:
        """Get full history"""

    def get_summary(self) -> str:
        """Get summary string"""
```

**Note**: Claude Code's `-c` flag handles actual context accumulation. This is for inspection only.

### Module: prompt_loader.py (PromptLoader)

**Purpose**: Load and compose prompts with search path support

```python
class PromptLoader:
    def load(self, toolname: Optional[str] = None) -> str:
        """
        Load system prompt(s) based on toolname.

        Rules:
        - toolname=None → ATOM.md
        - toolname='atom_foo' → ATOM.md + FOO.md
        - toolname='foo' → FOO.md only

        Search paths (priority order):
        1. .atom/prompts/ (project-local)
        2. ~/cc_atoms/prompts/ (global)
        3. $ATOM_PROMPTS_PATH (env override)
        """
```

### Module: claude_runner.py (ClaudeRunner)

**Purpose**: Execute Claude Code subprocess

```python
class ClaudeRunner:
    def run(
        self,
        prompt: str,
        conversation_dir: Path,
        use_context: bool = True,      # -c flag
        dangerous_skip: bool = True    # --dangerously-skip-permissions
    ) -> Tuple[str, int]:
        """
        Run Claude Code.

        Returns:
            (stdout, returncode)
        """
```

---

## CLI Interface: atom.py

**Location**: `~/cc_atoms/atom.py`
**Lines**: ~107

**Purpose**: Command-line interface for atom orchestration

**Functions**:
```python
parse_arguments() -> argparse.Namespace
    # Parse --toolname and prompt arguments

handle_command_line_prompt(prompt_args: List[str])
    # Create USER_PROMPT.md from CLI args

validate_user_prompt()
    # Ensure USER_PROMPT.md exists, exit if not

setup_atoms_environment()
    # Create ~/cc_atoms directories, add bin to PATH

main()
    # Orchestrate: parse args → load prompt → create runtime → run
```

**Usage**:
```bash
atom "Task description"           # Create USER_PROMPT.md and run
atom                              # Use existing USER_PROMPT.md
atom --toolname atom_test "Run"   # Use specialized prompt
```

---

## Configuration: config.py

**Location**: `~/cc_atoms/config.py`
**Lines**: ~40

All settings centralized:

```python
# Directory structure
ATOMS_HOME = Path.home() / "cc_atoms"
BIN_DIR = ATOMS_HOME / "bin"
TOOLS_DIR = ATOMS_HOME / "tools"
PROMPTS_DIR = ATOMS_HOME / "prompts"
TESTS_DIR = ATOMS_HOME / "tests"

# Search paths (priority: local → global → env)
TOOL_SEARCH_PATHS = [
    Path.cwd() / ".atom",
    TOOLS_DIR,
    Path(os.getenv("ATOM_TOOLS_PATH", "/nonexistent"))
]

PROMPT_SEARCH_PATHS = [
    Path.cwd() / ".atom" / "prompts",
    PROMPTS_DIR,
    Path(os.getenv("ATOM_PROMPTS_PATH", "/nonexistent"))
]

# Iteration settings
MAX_ITERATIONS = 25
EXIT_SIGNAL = "EXIT_LOOP_NOW"

# Retry settings
NETWORK_ERROR_KEYWORDS = ["network", "timeout", "connection", "temporary"]
NETWORK_RETRY_BASE = 5      # seconds
NETWORK_RETRY_MAX = 300     # 5 minutes
OTHER_RETRY_BASE = 10       # seconds
OTHER_RETRY_MAX = 600       # 10 minutes
SESSION_LIMIT_BUFFER = 300  # 5 minutes buffer after reset
DEFAULT_SESSION_LIMIT_WAIT = 3600  # 1 hour fallback
```

---

## Tools Ecosystem

### Tool: atom_gui (Modular)

**Location**: `~/cc_atoms/tools/atom_gui/`

**Purpose**: Real-time GUI monitor for atom sessions

**Architecture** (post-refactor):
```
tools/atom_gui/
├── atom_gui.py              # Entry point (~35 lines)
├── core/                    # Business logic
│   ├── __init__.py
│   ├── parser.py            # PromptParser (~97 lines)
│   ├── history.py           # EditHistory (~82 lines)
│   ├── saver.py             # SessionSaver (~209 lines)
│   └── session.py           # SessionInfo, SessionScanner (~175 lines)
└── gui/                     # UI layer
    ├── __init__.py
    └── main_window.py       # MainWindow (~745 lines)
```

**Features**:
- Hierarchical tree view of sessions
- Individual prompt navigation (user/assistant)
- Editable prompts with save to JSONL
- Undo/redo with arbitrary depth
- Auto-refresh every 2 seconds
- Color-coded status

**Usage**:
```bash
atom_gui /path/to/project
```

### Tool: atom_create_tool

**Location**: `~/cc_atoms/tools/atom_create_tool/`
**Lines**: ~392

**Purpose**: Scaffold new tools

**Modes**:
1. **Interactive**: Prompts for details
2. **AI**: Takes description, spawns atom

**Usage**:
```bash
atom_create_tool                           # Interactive
atom_create_tool "create a code reviewer"  # AI-assisted
```

### Tool: atom_session_analyzer

**Location**: `~/cc_atoms/tools/atom_session_analyzer/`
**Lines**: ~85

**Purpose**: Extract and analyze Claude Code sessions

**Usage**:
```bash
atom_session_analyzer              # Extract only
atom_session_analyzer "summarize"  # Extract and analyze
```

### Tool: gui_control (Example Embedded Usage)

**Location**: `~/cc_atoms/tools/gui_control/`
**Lines**: ~480

**Purpose**: Demonstrate embedded atom usage for GUI automation

**Architecture**:
```python
from atom_core import AtomRuntime

def control_gui(task: str, max_iterations: int = 10) -> Dict[str, Any]:
    """Control macOS GUI using natural language."""
    runtime = AtomRuntime.create_ephemeral(
        system_prompt=SYSTEM_PROMPT.replace('{user_task}', task),
        max_iterations=max_iterations,
        verbose=False
    )
    return runtime.run("Begin working on the task.")
```

**Usage**:
```python
from gui_control import control_gui
result = control_gui("Click submit in Safari")
```

---

## Prompt System

### ATOM.md (Base Prompt)

**Location**: `~/cc_atoms/prompts/ATOM.md`
**Lines**: ~538

**Sections**:
1. Architecture Overview
2. Capabilities (full Claude Code access)
3. Critical Files (USER_PROMPT.md, README.md)
4. Workflow (5-step iteration pattern)
5. Decomposition (spawning sub-atoms)
6. Specialized Atom Prompts (--toolname)
7. Tool Creation
8. Signaling Completion (EXIT_LOOP_NOW)
9. Error Handling
10. Best Practices

**Variables**: `{max_iterations}` replaced by runtime

### Specialized Prompts

| Prompt | Purpose |
|--------|---------|
| `ATOM_CREATE_TOOL.md` | Tool creation guidance |
| `ATOM_SESSION_ANALYZER.md` | Session analysis |
| `GUI_CONTROL.md` | GUI automation |

### Prompt Composition

```
--toolname atom_test
    ↓
ATOM.md + TEST.md (combined with \n\n)

--toolname test
    ↓
TEST.md only (standalone)
```

---

## Directory Structure

```
~/cc_atoms/
├── atom.py                     # CLI interface (~107 lines)
├── config.py                   # Central configuration (~40 lines)
│
├── atom_core/                  # Embeddable library
│   ├── __init__.py             # Exports: AtomRuntime, PromptLoader, etc.
│   ├── runtime.py              # AtomRuntime (~250 lines)
│   ├── retry.py                # RetryManager (~100 lines)
│   ├── context.py              # IterationHistory (~50 lines)
│   ├── prompt_loader.py        # PromptLoader (~80 lines)
│   └── claude_runner.py        # ClaudeRunner (~60 lines)
│
├── bin/                        # Launchers (in PATH)
│   ├── atom
│   ├── atom_gui
│   ├── atom_create_tool
│   └── atom_session_analyzer
│
├── prompts/                    # System prompts
│   ├── ATOM.md                 # Base prompt
│   ├── ATOM_CREATE_TOOL.md
│   ├── ATOM_SESSION_ANALYZER.md
│   └── GUI_CONTROL.md
│
├── tools/
│   ├── atom_gui/               # Modular GUI monitor
│   │   ├── atom_gui.py         # Entry point
│   │   ├── core/               # Business logic
│   │   └── gui/                # UI layer
│   ├── atom_create_tool/
│   ├── atom_session_analyzer/
│   └── gui_control/            # Embedded atom example
│
├── tests/
│   ├── test_atom.py            # CLI tests
│   └── test_atom_core.py       # Core library tests
│
├── archive/                    # Archived experiments
│   ├── timeout_analysis_experiment/
│   ├── timeout_analysis_deep_research/
│   ├── terminal_stability_experiment/
│   └── deep2/
│
└── docs/
    ├── README.md               # Project overview
    ├── ARCHITECTURE.md         # This file
    ├── USER_GUIDE.md           # Comprehensive usage guide
    └── CC_ATOMS_REFACTOR_SPEC.md  # Embeddable atom spec
```

---

## Workflows

### Basic Workflow

```bash
# 1. Navigate to project
cd ~/my-project

# 2. Create task or run with inline prompt
atom "Build a REST API with authentication"

# 3. Atom iterates
# - Iteration 1: Setup structure
# - Iteration 2: Implement endpoints
# - Iteration 3: Add tests
# - Iteration 4: Document
# Output: EXIT_LOOP_NOW

# 4. Review results
cat README.md
```

### Embedded Tool Workflow

```python
from atom_core import AtomRuntime

# Create specialized tool
runtime = AtomRuntime.create_ephemeral(
    system_prompt="You are a code reviewer...",
    max_iterations=5
)

# Run task
result = runtime.run("Review authentication.py for security issues")

if result["success"]:
    print(result["output"])
```

### Project-Local Tools

```bash
# Create project-local prompt
mkdir -p .atom/prompts
cat > .atom/prompts/MYPROJ.md << 'EOF'
# MyProject Tool
You are specialized for this project...
EOF

# Use it
atom --toolname myproj "Run specialized task"
```

---

## Development Guide

### Creating New Tools

**Method 1: AI-Assisted**
```bash
atom_create_tool "create a tool that analyzes test coverage"
```

**Method 2: Manual**

1. Create directory structure:
```bash
mkdir -p ~/cc_atoms/tools/my_tool
```

2. Create Python script (`my_tool.py`):
```python
#!/usr/bin/env python3
from atom_core import AtomRuntime

def main():
    runtime = AtomRuntime.create_ephemeral(
        system_prompt=open("MY_TOOL_PROMPT.md").read(),
        max_iterations=10
    )
    result = runtime.run(sys.argv[1] if len(sys.argv) > 1 else "")
    return 0 if result["success"] else 1

if __name__ == "__main__":
    sys.exit(main())
```

3. Create launcher in `~/cc_atoms/bin/my_tool`
4. Create prompt in `~/cc_atoms/prompts/MY_TOOL.md`

### Testing

```bash
# Run all tests
python3 tests/test_atom.py
python3 tests/test_atom_core.py

# Test coverage:
# - CLI functions (parse_arguments, etc.)
# - PromptLoader (search paths, composition)
# - RetryManager (backoff, session limits)
# - IterationHistory (tracking)
# - AtomRuntime (orchestration, errors)
# - ClaudeRunner (command building)
```

### Debugging

```bash
# Check imports
python3 -c "from atom_core import AtomRuntime; print('OK')"

# Check prompt loading
python3 -c "
from atom_core import PromptLoader
loader = PromptLoader()
print(loader.load('atom_test')[:100])
"

# Verbose mode for debugging
runtime = AtomRuntime(..., verbose=True)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-11 | Major refactor: `atom_core` library, modular `atom_gui` |
| 1.0 | 2025-10 | Initial release |

---

**Last Updated:** 2025-11-29
**Status:** PRODUCTION
