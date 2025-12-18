# Contributing to CC CLI

Thank you for your interest in contributing to CC CLI! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Architecture Overview](#architecture-overview)
- [Adding New Features](#adding-new-features)

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- An Anthropic API key (for testing)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cc-cli.git
   cd cc-cli
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up your API key**
   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

5. **Run tests to verify setup**
   ```bash
   pytest
   ```

## Code Style

We follow Python best practices and PEP 8 guidelines.

### Style Guidelines

- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions and classes
- **Line Length**: Maximum 100 characters (flexible for readability)
- **Imports**: Group imports in order: standard library, third-party, local
- **Naming**:
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private members: `_leading_underscore`

### Example

```python
from typing import Optional, List, Dict, Any

class ExampleClass:
    """Brief description of the class.

    Longer description if needed, explaining the purpose
    and usage of the class.

    Attributes:
        public_attr: Description of public attribute
    """

    def __init__(self, param: str, optional_param: Optional[int] = None) -> None:
        """Initialize the class.

        Args:
            param: Description of param
            optional_param: Description of optional param
        """
        self.public_attr = param
        self._private_attr = optional_param

    async def public_method(
        self,
        required_arg: str,
        optional_arg: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Brief description of what this method does.

        Args:
            required_arg: Description of required argument
            optional_arg: Description of optional argument

        Returns:
            Description of return value

        Raises:
            ValueError: When and why this is raised
            RuntimeError: When and why this is raised
        """
        if not required_arg:
            raise ValueError("required_arg cannot be empty")

        # Implementation
        return ["result"]

    def _private_method(self) -> None:
        """Private methods can have briefer docstrings."""
        pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cc

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_client_initialization

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures from `tests/conftest.py`
- Aim for >80% code coverage
- Test both success and error cases

Example test:

```python
import pytest
from cc.api import APIClient, APIKeyError

def test_client_requires_api_key():
    """Test that APIClient raises error without API key."""
    with pytest.raises(APIKeyError):
        APIClient(api_key=None)

@pytest.mark.asyncio
async def test_client_creates_message(mock_api_client):
    """Test successful message creation."""
    messages = [{"role": "user", "content": "Hello"}]

    events = []
    async for event in mock_api_client.create_message(messages):
        events.append(event)

    assert len(events) > 0
    assert events[0]["type"] in ("text_delta", "message_start")
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and linting**
   ```bash
   pytest
   # If you have linting tools:
   black .
   mypy cc/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

   Use conventional commit messages:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test additions/changes
   - `refactor:` Code refactoring
   - `perf:` Performance improvements

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

6. **PR Review**
   - Address any feedback from reviewers
   - Keep the PR focused on a single feature/fix
   - Update tests and docs as requested

## Architecture Overview

Understanding the codebase structure:

```
cc/
├── __init__.py          # Package exports
├── main.py              # CLI entry point
├── app.py               # Application context (dependency injection)
├── repl.py              # Interactive REPL
├── conversation.py      # Conversation management
├── print_mode.py        # Non-interactive mode
├── api/                 # Anthropic API integration
│   ├── client.py        # API client with retry logic
│   └── models.py        # Model name resolution
├── config/              # Configuration management
│   ├── settings.py      # Settings loading/merging
│   └── paths.py         # Path utilities
├── hooks/               # Hooks system
│   └── hooks.py         # Hook event management
├── session/             # Session persistence
│   ├── manager.py       # Session lifecycle
│   └── storage.py       # JSONL storage
├── tools/               # Tool implementations
│   ├── base.py          # Base tool class
│   ├── executor.py      # Tool execution & permissions
│   ├── bash.py          # Bash command tool
│   ├── read.py          # File reading tool
│   ├── write.py         # File writing tool
│   ├── edit.py          # File editing tool
│   ├── glob.py          # File pattern matching
│   └── grep.py          # Content search
└── ui/                  # User interface
    ├── renderer.py      # Output rendering
    ├── prompt.py        # Input handling
    ├── spinner.py       # Loading spinners
    └── colors.py        # Terminal colors
```

### Key Concepts

**Dependency Injection**: The `Application` class (`app.py`) manages all dependencies using lazy initialization.

**Session Management**: Conversations are persisted as JSONL files in `~/.cc/sessions/`.

**Tool Execution**: Tools are defined with schemas, executed through `ToolExecutor`, and permission-checked.

**Hooks**: Custom shell commands can run before/after tool execution.

**Settings Hierarchy**: Settings merge from defaults → user global → project local → CLI args.

## Adding New Features

### Adding a New Tool

1. Create tool file in `cc/tools/`:

```python
from typing import Any, Dict
from .base import BaseTool, ToolResult

class MyNewTool(BaseTool):
    """Description of what this tool does."""

    name = "MyNewTool"

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Return tool definition for the API."""
        return {
            "name": cls.name,
            "description": "What this tool does",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of param1",
                    },
                },
                "required": ["param1"],
            },
        }

    async def execute(self, param1: str, **kwargs) -> ToolResult:
        """Execute the tool.

        Args:
            param1: Description

        Returns:
            ToolResult with output or error
        """
        try:
            # Implementation
            result = f"Processed: {param1}"
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

2. Register in `cc/tools/executor.py`:

```python
from .my_new_tool import MyNewTool

class ToolRegistry:
    def _register_builtin_tools(self) -> None:
        builtin_tools = [
            # ... existing tools
            MyNewTool,
        ]
```

3. Add tests in `tests/test_tools.py`:

```python
@pytest.mark.asyncio
async def test_my_new_tool():
    tool = MyNewTool()
    result = await tool.execute(param1="test")
    assert result.success
    assert "Processed: test" in result.output
```

### Adding a New Slash Command

1. Add command to `SLASH_COMMANDS` dict in `repl.py`
2. Add handler method in REPL class
3. Add tests for the new command

### Adding Configuration Options

1. Add default value in `Settings` class (`config/settings.py`)
2. Add CLI argument if needed (`main.py`)
3. Document in README.md
4. Add tests for the new option

## Questions?

If you have questions or need help:

- Open an issue on GitHub
- Check existing issues and documentation
- Reach out to maintainers

Thank you for contributing! 🎉
