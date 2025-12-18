# cc_atoms - Multi-Step Agentic AI Coding Orchestrator for Claude Code

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude-Code-orange.svg)](https://claude.ai)

> **Turn impossible one-shot coding tasks into achievable multi-step workflows**

cc_atoms is an autonomous orchestration layer for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that enables complex, multi-step AI coding through intelligent task decomposition, persistent context, and quality gates.

## Why cc_atoms?

Modern AI coding assistants excel at single-turn tasks but struggle with complex, multi-step implementations. cc_atoms solves this by:

| Challenge | cc_atoms Solution |
|-----------|-------------------|
| Context gets lost between iterations | **Persistent conversation** via `claude -c` |
| Complex tasks overwhelm single prompts | **AI-powered task decomposition** into sub-atoms |
| No verification of outputs | **Meta-agents** (critic, verifier) review work |
| Incomplete or broken code ships | **Quality gates** detect issues and continue |
| One-size-fits-all approach | **Complexity analysis** adapts strategy to task |

## Quick Start

```bash
# Install
pip install cc_atoms

# Or clone and install
git clone https://github.com/MarkAnthonyKoop/cc_atoms.git
cd cc_atoms
pip install -e .

# Run with inline prompt
atom "Create a REST API with user authentication and tests"

# Run with task file
echo "Build a CLI calculator" > USER_PROMPT.md
atom
```

## Features

### Intelligent Task Analysis
```bash
atom "Build a complex web scraper with pagination"
# Output:
# Complexity: complex
# Estimated iterations: 8
# Meta-agents: ['critic', 'verifier']
# Decomposing into 5 sub-atoms...
```

### Task Decomposition
Complex tasks are automatically broken into manageable steps:
```
Step 1: Analyze - Read and understand requirements
Step 2: Design - Plan implementation approach
Step 3: Implement - Write the core code
Step 4: Test - Verify implementation works
Step 5: Document - Update README and docs
```

### Persistent Context
Unlike other tools that start fresh each iteration, cc_atoms maintains full conversation history:
```python
# Each iteration sees ALL previous context
claude -c -p "system_prompt" --dangerously-skip-permissions
#      ^^ This flag is the secret sauce
```

### Meta-Agents
Built-in review agents catch issues before completion:
- **Critic**: Reviews code against requirements, flags issues
- **Verifier**: Actually RUNS the code, captures real errors

### Quality Gates
Pattern-based detection prevents incomplete work:
```python
RED_FLAG_PATTERNS = ["todo:", "fixme:", "untested", "i'm not sure"]
# If found → continue iterating
```

## Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────┐
│  Phase 1: Task Analysis (AI-based)      │
│  - Complexity detection (simple→massive)│
│  - Memory query generation              │
│  - Meta-agent recommendation            │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Phase 2: Memory Lookup (optional)      │
│  - Semantic search of past knowledge    │
│  - Context injection into system prompt │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Phase 3: Task Decomposition            │
│  - Task-specific step generation        │
│  - Sub-atom spawning per step           │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Phase 4: Main Execution Loop           │
│  - Persistent conversation (claude -c)  │
│  - Iterative refinement (up to 25 iter) │
│  - EXIT_LOOP_NOW termination            │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Phase 5: Meta-Agents + Quality Gates   │
│  - Critic/verifier review               │
│  - Red flag detection                   │
│  - Continue if issues found             │
└─────────────────────────────────────────┘
```

## Comparison to Other Tools

| Feature | cc_atoms | gpt-engineer | Aider | Cursor |
|---------|----------|--------------|-------|--------|
| Multi-step decomposition | ✅ AI-powered | ❌ Manual | ❌ | ❌ |
| Persistent context | ✅ Full history | ❌ Fresh each time | ✅ | ✅ |
| Task complexity analysis | ✅ | ❌ | ❌ | ❌ |
| Meta-agent review | ✅ Critic + Verifier | ❌ | ❌ | ❌ |
| Quality gates | ✅ | ❌ | ❌ | ❌ |
| Memory/knowledge base | ✅ Semantic search | ❌ | ❌ | ❌ |
| Model | Claude | GPT-4/Claude | Any | Any |
| Interface | CLI | CLI | CLI | IDE |

## Use Cases

### Complex Feature Implementation
```bash
atom "Add user authentication with OAuth2, JWT tokens, role-based access control, and comprehensive tests"
```

### Multi-File Refactoring
```bash
atom "Refactor the data layer to use repository pattern, update all services, and ensure tests pass"
```

### Full Application Generation
```bash
atom "Create a browser-based 3D game with Three.js, physics, controls, and scoring"
# Actually works - see our head-to-head test results
```

### Automated Code Review
```bash
atom --toolname critic "Review the authentication module for security issues"
```

## Embeddable Library

Use `atom_core` in your own Python projects:

```python
from cc_atoms.atom_core import AtomRuntime

# Standard runtime with persistent conversation
runtime = AtomRuntime(
    system_prompt="You are a coding assistant",
    conversation_dir=Path("./my-project"),
    max_iterations=25,
    use_task_analyzer=True,  # Enable AI complexity analysis
    use_meta_agents=True,    # Enable critic/verifier
)
result = runtime.run("Build a REST API")

# Ephemeral runtime (auto-cleanup)
runtime = AtomRuntime.create_ephemeral(
    system_prompt="You are a GUI automation agent",
    max_iterations=10
)
result = runtime.run("Click the submit button")

# Result structure
{
    "success": bool,
    "iterations": int,
    "output": str,
    "duration": float,
    "complexity": str,      # "simple", "moderate", "complex", "massive"
    "decomposition": dict,  # Sub-atom results if decomposed
}
```

## Configuration

```python
# config.py - All settings centralized
MAX_ITERATIONS = 25
EXIT_SIGNAL = "EXIT_LOOP_NOW"

# Complexity thresholds
class ComplexityLevel(Enum):
    SIMPLE = "simple"       # 1 iteration
    MODERATE = "moderate"   # 4 iterations
    COMPLEX = "complex"     # 8 iterations
    MASSIVE = "massive"     # 10+ iterations, forced decomposition

# Decomposition levels
class DecompositionLevel(Enum):
    NONE = "none"           # Never decompose
    LIGHT = "light"         # Only massive tasks
    STANDARD = "standard"   # Complex+ tasks (default)
    AGGRESSIVE = "aggressive"  # Everything decomposes
```

## CLI Options

```bash
atom [OPTIONS] [PROMPT]

Options:
  --toolname NAME       Load specialized prompt (e.g., atom_test, critic)
  --max-iterations N    Override max iterations (default: 25)
  --no-analyze          Skip AI task analysis
  --force-complex       Force complex task handling
  --decomposition LEVEL Set decomposition level (none/light/standard/aggressive)
  --verbose             Show detailed progress
  --quiet               Minimal output
```

## Directory Structure

```
cc_atoms/
├── src/cc_atoms/
│   ├── cli.py              # Main CLI entry point
│   ├── config.py           # Centralized configuration
│   ├── atom_core/          # Embeddable orchestration library
│   │   ├── runtime.py      # AtomRuntime - main engine
│   │   ├── task_analyzer.py # AI complexity analysis
│   │   ├── memory.py       # Semantic memory lookup
│   │   ├── retry.py        # Error handling & backoff
│   │   └── claude_runner.py # Subprocess execution
│   ├── prompts/            # System prompts
│   │   ├── ATOM.md         # Base orchestration prompt
│   │   └── meta_agents/    # Critic, verifier prompts
│   └── tools/              # Built-in tools
├── docs/
│   ├── USER_GUIDE.md
│   └── ARCHITECTURE.md
└── tests/
```

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- `ANTHROPIC_API_KEY` environment variable (for Claude Code)

## Installation

```bash
# From PyPI (coming soon)
pip install cc_atoms

# From source
git clone https://github.com/MarkAnthonyKoop/cc_atoms.git
cd cc_atoms
pip install -e .

# Verify installation
atom --help
```

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Comprehensive usage examples
- [Architecture](docs/ARCHITECTURE.md) - System design and internals
- [API Reference](docs/API.md) - Library documentation

## Related Projects

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) - The underlying CLI this orchestrates
- [Aider](https://github.com/paul-gauthier/aider) - AI pair programming in terminal
- [gpt-engineer](https://github.com/gpt-engineer-org/gpt-engineer) - Generate codebases from prompts
- [Cursor](https://cursor.sh) - AI-first code editor
- [Cline](https://github.com/cline/cline) - VS Code AI coding agent

## Keywords

AI coding assistant, Claude Code orchestration, multi-step AI coding, agentic coding, autonomous code generation, task decomposition, AI code review, persistent context AI, iterative code generation, Claude API, Anthropic, AI software engineering, code automation, AI pair programming, vibe coding, AI developer tools

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

**Built with Claude Code** | **Orchestrated by cc_atoms**
