# CC CLI Architecture Document

## Overview

This document defines the architecture for `cc`, a Python-based clone of the Claude Code CLI. The design prioritizes modularity, extensibility, and feature parity with the original `claude` command.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI Entry Point                                 │
│                                  (main.py)                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌─────────────────┐         ┌─────────────────┐
          │   REPL Engine   │         │   Print Mode    │
          │   (repl.py)     │         │   (print.py)    │
          └────────┬────────┘         └────────┬────────┘
                   │                           │
                   └─────────────┬─────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │    Conversation Core    │
                    │    (conversation.py)    │
                    └───────────┬─────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │   API    │ │  Tools   │ │ Commands │ │  Config  │ │ Session  │
  │ (api.py) │ │ (tools/) │ │(commands)│ │(config/) │ │(session/)│
  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Directory Structure

```
cli/
├── cc/                          # Main package
│   ├── __init__.py              # Package exports and version
│   ├── main.py                  # CLI entry point (argparse)
│   ├── repl.py                  # Interactive REPL engine
│   ├── print_mode.py            # Non-interactive print mode
│   ├── conversation.py          # Core conversation management
│   ├── api/                     # Anthropic API integration
│   │   ├── __init__.py
│   │   ├── client.py            # API client wrapper
│   │   ├── streaming.py         # Streaming response handler
│   │   └── models.py            # Model aliases and validation
│   ├── tools/                   # Tool implementations
│   │   ├── __init__.py          # Tool registry
│   │   ├── base.py              # Base tool class
│   │   ├── bash.py              # Bash command execution
│   │   ├── read.py              # File reading
│   │   ├── write.py             # File writing
│   │   ├── edit.py              # File editing
│   │   ├── glob_tool.py         # File globbing
│   │   ├── grep.py              # Content search
│   │   └── executor.py          # Tool execution engine
│   ├── commands/                # Slash command implementations
│   │   ├── __init__.py          # Command registry
│   │   ├── base.py              # Base command class
│   │   ├── help.py              # /help
│   │   ├── clear.py             # /clear
│   │   ├── compact.py           # /compact
│   │   ├── config.py            # /config
│   │   ├── cost.py              # /cost
│   │   ├── model.py             # /model
│   │   ├── permissions.py       # /permissions
│   │   ├── status.py            # /status
│   │   ├── init.py              # /init
│   │   ├── memory.py            # /memory
│   │   └── custom.py            # Custom command loader
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py          # Settings file handling
│   │   ├── permissions.py       # Permission system
│   │   ├── paths.py             # Path constants and utilities
│   │   └── claude_md.py         # CLAUDE.md file loading
│   ├── session/                 # Session management
│   │   ├── __init__.py
│   │   ├── manager.py           # Session lifecycle management
│   │   ├── storage.py           # JSONL session storage
│   │   ├── history.py           # Command history (history.jsonl)
│   │   └── file_history.py      # File backup/restore
│   ├── hooks/                   # Hooks system
│   │   ├── __init__.py
│   │   ├── manager.py           # Hook registration and dispatch
│   │   └── types.py             # Hook type definitions
│   ├── ui/                      # User interface components
│   │   ├── __init__.py
│   │   ├── renderer.py          # Output rendering (markdown)
│   │   ├── prompt.py            # Input prompt handling
│   │   ├── spinner.py           # Loading spinners
│   │   └── colors.py            # Terminal colors
│   └── utils/                   # Shared utilities
│       ├── __init__.py
│       ├── logging.py           # Debug logging
│       ├── git.py               # Git operations
│       └── validation.py        # Input validation
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_api/
│   ├── test_tools/
│   ├── test_commands/
│   ├── test_config/
│   ├── test_session/
│   └── test_integration/
├── setup.py                     # Package installation
├── pyproject.toml               # Modern Python packaging
├── requirements.txt             # Dependencies
└── README.md                    # Documentation
```

---

## Module Interfaces

### 1. Main Entry Point (`main.py`)

```python
"""CLI entry point and argument parsing."""

from typing import Optional, List
import argparse

def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all options."""
    ...

def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the cc command.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    ...

# Subcommands
def cmd_mcp(args: argparse.Namespace) -> int:
    """Handle 'cc mcp' subcommand."""
    ...

def cmd_plugin(args: argparse.Namespace) -> int:
    """Handle 'cc plugin' subcommand."""
    ...
```

### 2. REPL Engine (`repl.py`)

```python
"""Interactive REPL for conversation mode."""

from typing import Optional
from .conversation import Conversation
from .config import Settings
from .session import SessionManager

class REPL:
    """Interactive Read-Eval-Print Loop."""

    def __init__(
        self,
        conversation: Conversation,
        settings: Settings,
        session_manager: SessionManager
    ) -> None:
        """Initialize REPL with dependencies."""
        ...

    async def run(self) -> int:
        """Run the interactive REPL loop.

        Returns:
            Exit code
        """
        ...

    async def process_input(self, user_input: str) -> bool:
        """Process a single user input.

        Args:
            user_input: Raw user input string

        Returns:
            True to continue, False to exit
        """
        ...

    def handle_slash_command(self, command: str) -> bool:
        """Handle slash command input.

        Args:
            command: Command string (without leading /)

        Returns:
            True if command was handled
        """
        ...
```

### 3. Print Mode (`print_mode.py`)

```python
"""Non-interactive print mode for piping and scripting."""

from typing import Optional, Literal
from .conversation import Conversation

OutputFormat = Literal["text", "json", "stream-json"]
InputFormat = Literal["text", "stream-json"]

class PrintMode:
    """Non-interactive single-shot mode."""

    def __init__(
        self,
        conversation: Conversation,
        output_format: OutputFormat = "text",
        input_format: InputFormat = "text"
    ) -> None:
        ...

    async def run(self, prompt: str) -> int:
        """Execute a single prompt and print result.

        Args:
            prompt: User prompt to process

        Returns:
            Exit code
        """
        ...

    async def stream_output(self) -> None:
        """Stream output in the configured format."""
        ...
```

### 4. Conversation Core (`conversation.py`)

```python
"""Core conversation management."""

from typing import List, Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass
from .api import APIClient
from .tools import ToolExecutor
from .session import SessionManager

@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user" | "assistant"
    content: Any  # str or List[ContentBlock]
    uuid: str
    timestamp: str
    metadata: Dict[str, Any]

class Conversation:
    """Manages a multi-turn conversation with Claude."""

    def __init__(
        self,
        api_client: APIClient,
        tool_executor: ToolExecutor,
        session_manager: SessionManager,
        system_prompt: Optional[str] = None
    ) -> None:
        ...

    async def send_message(
        self,
        content: str,
        stream: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a message and yield streaming response chunks.

        Args:
            content: User message content
            stream: Whether to stream the response

        Yields:
            Response chunks with type, content, etc.
        """
        ...

    async def handle_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a tool use request from the model.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters

        Returns:
            Tool result to send back to model
        """
        ...

    def get_messages(self) -> List[Message]:
        """Get all messages in the conversation."""
        ...

    def clear(self) -> None:
        """Clear the conversation history."""
        ...

    def compact(self) -> None:
        """Compact the conversation to reduce tokens."""
        ...
```

---

### 5. API Module (`api/`)

#### `api/client.py`

```python
"""Anthropic API client wrapper."""

from typing import Optional, Dict, Any, List, AsyncIterator
import anthropic

class APIClient:
    """Wrapper around Anthropic SDK with streaming support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929"
    ) -> None:
        """Initialize client.

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model to use
        """
        ...

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """Create a message with streaming.

        Args:
            messages: Conversation messages
            system: System prompt
            tools: Tool definitions
            stream: Whether to stream

        Yields:
            Response events
        """
        ...

    def set_model(self, model: str) -> None:
        """Change the active model."""
        ...

    @property
    def usage(self) -> Dict[str, int]:
        """Get cumulative token usage."""
        ...
```

#### `api/models.py`

```python
"""Model aliases and validation."""

MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101",
    "haiku": "claude-haiku-3-5-20241022"
}

def resolve_model(model_name: str) -> str:
    """Resolve model alias to full name."""
    ...

def validate_model(model_name: str) -> bool:
    """Check if model name is valid."""
    ...
```

---

### 6. Tools Module (`tools/`)

#### `tools/base.py`

```python
"""Base class for tool implementations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class Tool(ABC):
    """Abstract base class for all tools."""

    name: str
    description: str

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool's parameters."""
        ...

    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: "ToolContext"
    ) -> Dict[str, Any]:
        """Execute the tool with given parameters.

        Args:
            params: Tool input parameters
            context: Execution context

        Returns:
            Tool result
        """
        ...

@dataclass
class ToolContext:
    """Context for tool execution."""
    cwd: str
    session_id: str
    permissions: "PermissionManager"
    file_history: "FileHistory"
```

#### `tools/executor.py`

```python
"""Tool execution engine."""

from typing import Dict, Any, List, Optional
from .base import Tool, ToolContext

class ToolExecutor:
    """Manages tool registration and execution."""

    def __init__(self, context: ToolContext) -> None:
        ...

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        ...

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for API."""
        ...

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            params: Tool parameters

        Returns:
            Tool result
        """
        ...

    def check_permission(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check if tool execution is permitted.

        Returns:
            (allowed, reason)
        """
        ...
```

#### `tools/bash.py`

```python
"""Bash command execution tool."""

from .base import Tool, ToolContext
from typing import Dict, Any

class BashTool(Tool):
    """Execute bash commands."""

    name = "Bash"
    description = "Execute bash commands in a persistent shell"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in milliseconds"
                },
                "run_in_background": {
                    "type": "boolean",
                    "description": "Run in background"
                }
            },
            "required": ["command"]
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext
    ) -> Dict[str, Any]:
        """Execute a bash command."""
        ...
```

---

### 7. Commands Module (`commands/`)

#### `commands/base.py`

```python
"""Base class for slash commands."""

from abc import ABC, abstractmethod
from typing import List, Optional, Any
from dataclasses import dataclass

@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None

class Command(ABC):
    """Abstract base class for slash commands."""

    name: str
    description: str
    aliases: List[str] = []

    @abstractmethod
    async def execute(
        self,
        args: List[str],
        context: "CommandContext"
    ) -> CommandResult:
        """Execute the command.

        Args:
            args: Command arguments
            context: Execution context

        Returns:
            Command result
        """
        ...

@dataclass
class CommandContext:
    """Context for command execution."""
    conversation: "Conversation"
    settings: "Settings"
    session_manager: "SessionManager"
    repl: "REPL"
```

#### `commands/__init__.py`

```python
"""Command registry and dispatcher."""

from typing import Dict, Optional
from .base import Command, CommandContext, CommandResult

class CommandRegistry:
    """Registry for slash commands."""

    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """Register a command."""
        ...

    def get(self, name: str) -> Optional[Command]:
        """Get command by name or alias."""
        ...

    async def execute(
        self,
        name: str,
        args: List[str],
        context: CommandContext
    ) -> CommandResult:
        """Execute a command by name."""
        ...

    def load_custom_commands(self, path: str) -> None:
        """Load custom commands from .claude/commands/."""
        ...
```

---

### 8. Config Module (`config/`)

#### `config/settings.py`

```python
"""Settings file management."""

from typing import Dict, Any, Optional
from pathlib import Path
import json

class Settings:
    """Manage settings from multiple sources."""

    def __init__(
        self,
        user_settings: Optional[Path] = None,
        project_settings: Optional[Path] = None,
        local_settings: Optional[Path] = None
    ) -> None:
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value with fallback chain."""
        ...

    def set(self, key: str, value: Any, scope: str = "user") -> None:
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            scope: "user", "project", or "local"
        """
        ...

    def load(self) -> None:
        """Load settings from all sources."""
        ...

    def save(self, scope: str = "user") -> None:
        """Save settings to specified scope."""
        ...

    @property
    def permission_mode(self) -> str:
        """Get current permission mode."""
        ...
```

#### `config/permissions.py`

```python
"""Permission system for tool access."""

from typing import List, Tuple, Optional
from dataclasses import dataclass
import re

@dataclass
class PermissionRule:
    """A single permission rule."""
    pattern: str
    action: str  # "allow", "deny", "ask"

    def matches(self, tool_name: str, command: str) -> bool:
        """Check if rule matches tool/command."""
        ...

class PermissionManager:
    """Manages tool permissions."""

    def __init__(self, settings: "Settings") -> None:
        ...

    def check(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Tuple[str, Optional[str]]:
        """Check permission for tool use.

        Returns:
            (action, reason) where action is "allow", "deny", or "ask"
        """
        ...

    def add_rule(
        self,
        pattern: str,
        action: str,
        scope: str = "session"
    ) -> None:
        """Add a permission rule."""
        ...

    def parse_pattern(self, pattern: str) -> re.Pattern:
        """Parse tool permission pattern like 'Bash(git:*)'."""
        ...
```

#### `config/paths.py`

```python
"""Path constants and utilities."""

from pathlib import Path
from typing import Optional

def get_config_dir() -> Path:
    """Get ~/.cc/ config directory."""
    ...

def get_project_dir(project_path: Path) -> Path:
    """Get project directory under ~/.cc/projects/."""
    ...

def get_session_file(session_id: str, project_path: Path) -> Path:
    """Get path to session JSONL file."""
    ...

def get_history_file() -> Path:
    """Get path to history.jsonl."""
    ...

def find_claude_md(start_path: Path) -> Optional[Path]:
    """Find CLAUDE.md file starting from path."""
    ...
```

---

### 9. Session Module (`session/`)

#### `session/manager.py`

```python
"""Session lifecycle management."""

from typing import Optional, List
from pathlib import Path
import uuid
from dataclasses import dataclass

@dataclass
class SessionInfo:
    """Information about a session."""
    id: str
    project: str
    last_modified: str
    message_count: int

class SessionManager:
    """Manages conversation sessions."""

    def __init__(self, project_path: Path) -> None:
        ...

    def create(self) -> str:
        """Create a new session and return its ID."""
        ...

    def get_current(self) -> Optional[str]:
        """Get current session ID."""
        ...

    def get_recent(self) -> Optional[str]:
        """Get most recent session ID for -c flag."""
        ...

    def list_sessions(self) -> List[SessionInfo]:
        """List all sessions for current project."""
        ...

    def load(self, session_id: str) -> "Session":
        """Load a session by ID."""
        ...

    def fork(self, session_id: str) -> str:
        """Create a fork of existing session."""
        ...
```

#### `session/storage.py`

```python
"""JSONL session storage."""

from typing import List, Dict, Any, Iterator
from pathlib import Path
import json

class SessionStorage:
    """Read/write session JSONL files."""

    def __init__(self, path: Path) -> None:
        ...

    def read(self) -> List[Dict[str, Any]]:
        """Read all entries from session file."""
        ...

    def append(self, entry: Dict[str, Any]) -> None:
        """Append an entry to session file."""
        ...

    def iter_messages(self) -> Iterator[Dict[str, Any]]:
        """Iterate over message entries only."""
        ...

    @staticmethod
    def create_user_entry(
        content: str,
        session_id: str,
        cwd: str,
        parent_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a user message entry."""
        ...

    @staticmethod
    def create_assistant_entry(
        response: Dict[str, Any],
        session_id: str,
        cwd: str,
        parent_uuid: str
    ) -> Dict[str, Any]:
        """Create an assistant message entry."""
        ...
```

#### `session/history.py`

```python
"""Command history management."""

from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

@dataclass
class HistoryEntry:
    """A single history entry."""
    display: str
    timestamp: int
    project: str
    pasted_contents: Dict[str, str]

class CommandHistory:
    """Manages history.jsonl."""

    def __init__(self, path: Optional[Path] = None) -> None:
        ...

    def add(self, entry: HistoryEntry) -> None:
        """Add entry to history."""
        ...

    def search(
        self,
        query: str,
        limit: int = 50
    ) -> List[HistoryEntry]:
        """Search history entries."""
        ...

    def get_recent(self, limit: int = 100) -> List[HistoryEntry]:
        """Get recent history entries."""
        ...
```

---

### 10. Hooks Module (`hooks/`)

#### `hooks/types.py`

```python
"""Hook type definitions."""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

class HookType(Enum):
    """Types of hooks."""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SUBAGENT_START = "SubagentStart"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"

@dataclass
class HookContext:
    """Context passed to hooks."""
    hook_type: HookType
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
```

#### `hooks/manager.py`

```python
"""Hook registration and dispatch."""

from typing import List, Callable, Awaitable, Optional
from .types import HookType, HookContext

HookHandler = Callable[[HookContext], Awaitable[Optional[Dict[str, Any]]]]

class HookManager:
    """Manages hook registration and execution."""

    def __init__(self, settings: "Settings") -> None:
        ...

    def register(
        self,
        hook_type: HookType,
        handler: HookHandler,
        matcher: Optional[str] = None
    ) -> None:
        """Register a hook handler."""
        ...

    async def dispatch(
        self,
        hook_type: HookType,
        context: HookContext
    ) -> Optional[Dict[str, Any]]:
        """Dispatch hook to all matching handlers.

        Returns:
            Modified context or None
        """
        ...

    def load_from_settings(self) -> None:
        """Load hooks from settings configuration."""
        ...
```

---

### 11. UI Module (`ui/`)

#### `ui/renderer.py`

```python
"""Output rendering with markdown support."""

from typing import Optional
from rich.console import Console
from rich.markdown import Markdown

class Renderer:
    """Renders output to terminal."""

    def __init__(self, console: Optional[Console] = None) -> None:
        ...

    def markdown(self, text: str) -> None:
        """Render markdown text."""
        ...

    def code(self, code: str, language: str = "") -> None:
        """Render code block."""
        ...

    def error(self, message: str) -> None:
        """Render error message."""
        ...

    def success(self, message: str) -> None:
        """Render success message."""
        ...

    def stream_text(self, text: str) -> None:
        """Stream text without newline."""
        ...
```

#### `ui/prompt.py`

```python
"""Input prompt handling."""

from typing import Optional, List
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

class InputPrompt:
    """Handles user input with history and completion."""

    def __init__(
        self,
        history_file: Optional[str] = None
    ) -> None:
        ...

    async def get_input(self, prompt: str = "> ") -> str:
        """Get user input with prompt."""
        ...

    def set_completer(self, completions: List[str]) -> None:
        """Set available completions (slash commands, etc)."""
        ...
```

---

## Data Flow

### 1. Interactive Session Flow

```
User Input
    │
    ▼
┌──────────────┐
│ REPL.process │
│   _input()   │
└──────┬───────┘
       │
       ▼
   Slash Command? ──Yes──► CommandRegistry.execute()
       │                         │
       No                        ▼
       │                   CommandResult
       ▼                         │
┌──────────────────┐             │
│ Conversation.    │◄────────────┘
│  send_message()  │
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│ APIClient.      │
│ create_message()│
└────────┬────────┘
         │
         ▼
    Streaming Response
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  Text    Tool Use
    │         │
    ▼         ▼
 Render   ToolExecutor
    │     .execute()
    │         │
    │    ┌────┴────┐
    │    │         │
    │    ▼         ▼
    │  Result   Permission
    │    │      Check
    │    │         │
    │    └────┬────┘
    │         │
    └────┬────┘
         │
         ▼
    Continue Loop
```

### 2. Tool Execution Flow

```
Tool Use Request
       │
       ▼
┌──────────────────┐
│ HookManager.     │
│ dispatch(PRE_)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PermissionManager│
│ .check()         │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
 Allowed    Denied/Ask
    │         │
    ▼         ▼
Execute   Prompt User
    │         │
    └────┬────┘
         │
         ▼
┌──────────────────┐
│ Tool.execute()   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ HookManager.     │
│ dispatch(POST_)  │
└────────┬─────────┘
         │
         ▼
   Return Result
```

---

## Configuration Hierarchy

Settings are loaded and merged in this order (later overrides earlier):

1. **Defaults** (hardcoded in `config/settings.py`)
2. **User Settings** (`~/.cc/settings.json`)
3. **Project Settings** (`.cc/settings.json`)
4. **Local Settings** (`~/.cc/settings.local.json`, `.cc/settings.local.json`)
5. **CLI Arguments** (command line flags)

```
┌─────────────────────────────────────────────────────────────┐
│                      Final Settings                          │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ merge
┌─────────────────────────────┴─────────────────────────────┐
│ CLI Args    │ Local      │ Project   │ User     │ Defaults │
│ (highest)   │ Settings   │ Settings  │ Settings │ (lowest) │
└─────────────────────────────────────────────────────────────┘
```

---

## External Dependencies

### Required
- `anthropic>=0.40.0` - Anthropic SDK
- `rich>=13.0.0` - Terminal rendering
- `prompt_toolkit>=3.0.0` - Input handling
- `click>=8.0.0` - CLI framework (alternative to argparse)
- `pydantic>=2.0.0` - Data validation

### Optional
- `pygments>=2.0.0` - Syntax highlighting
- `httpx>=0.25.0` - Async HTTP (for MCP)

---

## Key Design Decisions

### 1. Async-First Architecture
All I/O operations are async to support streaming responses and concurrent tool execution.

### 2. Dependency Injection
Components receive dependencies through constructors, enabling testing and modularity.

### 3. Plugin-Ready Structure
Hooks, commands, and tools use registries that can be extended at runtime.

### 4. JSONL for Storage
Using the same JSONL format as Claude Code ensures compatibility and simplicity.

### 5. Rich for Rendering
Rich provides excellent markdown and code rendering out of the box.

### 6. Separation of Concerns
- `conversation.py` - Pure conversation logic
- `repl.py` - UI and input handling
- `api/` - External API communication
- `tools/` - Tool implementations
- `session/` - Persistence layer

---

## Implementation Priority

### Phase 1: Core Functionality
1. `main.py` - CLI entry point with basic args
2. `api/client.py` - API wrapper with streaming
3. `conversation.py` - Basic conversation loop
4. `repl.py` - Minimal REPL
5. `ui/renderer.py` - Text output

### Phase 2: Tools & Commands
1. `tools/bash.py`, `tools/read.py`, `tools/write.py`, `tools/edit.py`
2. `commands/help.py`, `commands/clear.py`, `commands/cost.py`
3. `config/permissions.py` - Basic permission checks

### Phase 3: Session Management
1. `session/storage.py` - JSONL read/write
2. `session/manager.py` - Session lifecycle
3. `-c` and `-r` flags

### Phase 4: Advanced Features
1. `hooks/` - Hook system
2. Custom commands loader
3. MCP integration
4. Print mode formats

---

## Testing Strategy

### Unit Tests
- Each module has corresponding test file
- Mock external dependencies (API, filesystem)
- Test edge cases and error handling

### Integration Tests
- Test full conversation flows
- Test tool execution with real filesystem (in temp dirs)
- Test session persistence

### E2E Tests
- Test CLI invocation with subprocess
- Compare behavior with actual `claude` command
- Test all flags and subcommands

---

## Security Considerations

1. **Command Injection**: Sanitize bash commands, use subprocess properly
2. **Path Traversal**: Validate file paths, restrict to allowed directories
3. **API Key Storage**: Use environment variables, never log keys
4. **Permission System**: Deny by default, require explicit allows
5. **File Backups**: Store backups before modifications
