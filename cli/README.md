# CC CLI - Claude Code CLI Clone

A Python-based clone of the Claude Code CLI that provides interactive conversation with Claude, tool execution, and session management.

## ✅ VERIFICATION STATUS

**The CC CLI is FULLY FUNCTIONAL as an agentic assistant.**

The agentic loop is already implemented and working. See [README_VERIFICATION.md](./README_VERIFICATION.md) for detailed analysis.

**Test Results**: 112/112 tests pass ✅

## Installation

```bash
# Install from source
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Usage

### Interactive Mode

```bash
# Start interactive REPL
cc

# Start with an initial prompt
cc -p "Hello, Claude!"

# Continue last conversation
cc -c

# Resume specific session
cc -r SESSION_ID
```

### Print Mode (Non-interactive)

```bash
# Single prompt with text output
cc --print -p "What is 2+2?"

# JSON output
cc --print --output-format json -p "Hello"

# Streaming JSON output
cc --print --output-format stream-json -p "Hello"

# Pipe input
echo "Hello" | cc --print
```

### Model Selection

```bash
# Use a specific model
cc -m opus    # Claude Opus
cc -m sonnet  # Claude Sonnet
cc -m haiku   # Claude Haiku

# Or full model name
cc -m claude-sonnet-4-5-20250929
```

### Permission Control

```bash
# Skip all permission checks (use with caution)
cc --dangerously-skip-permissions

# Allow only specific tools
cc --allowedTools "Bash(git:*)" "Read" "Glob"

# Deny specific tools
cc --disallowedTools "Bash(rm:*)" "Bash(sudo:*)"
```

### Slash Commands

Available commands in the REPL:

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/clear` | Clear conversation history |
| `/compact` | Compact conversation to reduce tokens |
| `/config` | View or modify configuration |
| `/cost` | Show token usage and cost |
| `/doctor` | Check system health and configuration |
| `/hooks` | Show configured hooks |
| `/init` | Initialize project configuration |
| `/memory` | Show memory/context information |
| `/model [name]` | View or change the model |
| `/permissions [mode]` | View or set permission mode |
| `/review` | Review uncommitted git changes |
| `/sessions` | List recent sessions |
| `/status` | Show session status |
| `/terminal-setup` | Show terminal setup instructions |
| `/vim` | Toggle vim mode |
| `/bug` | Report a bug |
| `/exit`, `/quit` | Exit the REPL |

### Custom Commands

Create custom slash commands by adding Markdown files to `.cc/commands/` or `.claude/commands/`:

```bash
# Create a custom command
mkdir -p .cc/commands
echo "Please review this code and suggest improvements" > .cc/commands/review-code.md

# Use the command
cc
> /review-code

# You can also use arguments with $ARGS or {{ARGS}} placeholders
echo "Please review this file: $ARGS" > .cc/commands/review-file.md
cc
> /review-file src/main.py
```

### Subcommands

```bash
# MCP management
cc mcp list
cc mcp add <name>
cc mcp remove <name>

# Configuration
cc config list
cc config get <key>
cc config set <key> <value>

# Sessions
cc sessions list
cc sessions export
```

## Tools

CC CLI supports the following built-in tools that Claude can use:

| Tool | Description |
|------|-------------|
| `Bash` | Execute shell commands |
| `Read` | Read file contents |
| `Write` | Write content to files |
| `Edit` | Make precise string replacements |
| `Glob` | Find files by pattern |
| `Grep` | Search file contents with regex |

### Tool Permission Patterns

```
Bash(git:*)      # Allow all git commands
Bash(npm:*)      # Allow all npm commands
Bash(rm:*)       # Match rm commands (for deny list)
Read             # Match all Read operations
Write            # Match all Write operations
```

## Configuration

Settings are loaded from multiple sources (in order of precedence):

1. **Defaults** (built-in)
2. **User Settings** (`~/.cc/settings.json`)
3. **User Local Settings** (`~/.cc/settings.local.json`)
4. **Project Settings** (`.cc/settings.json`)
5. **Project Local Settings** (`.cc/settings.local.json`)
6. **CLI Arguments**

### Example settings.json

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "maxTokens": 8192,
  "markdown": true,
  "permissions": {
    "defaultMode": "default"
  }
}
```

### Permission Modes

| Mode | Description |
|------|-------------|
| `default` | Ask for each tool use |
| `dontAsk` | Don't ask for confirmations |
| `acceptEdits` | Auto-accept file edits |
| `plan` | Read-only mode |

## CLAUDE.md

CC CLI automatically loads `CLAUDE.md` from your project directory to provide project-specific instructions to Claude. This file is included in the system prompt for every conversation.

```markdown
# Project Instructions

This is a Python project using FastAPI.

## Code Style
- Use type hints
- Follow PEP 8
- Write docstrings for public functions
```

## Hooks

Configure hooks in your settings to run commands before/after tool execution:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "echo 'About to use tool'",
        "matchers": ["Bash*"]
      }
    ],
    "PostToolUse": [
      "echo 'Tool completed'"
    ]
  }
}
```

## Environment Variables

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=cc

# All tests should pass
pytest tests/ -v
# Expected: 112 passed
```

## Programmatic Usage

You can also use CC CLI programmatically:

```python
from cc import Application, AppConfig

# Create application with custom config
config = AppConfig(
    model="sonnet",
    skip_permissions=True,
)
app = Application(config)

# Access components
settings = app.settings
api_client = app.api_client
tool_executor = app.tool_executor
hooks_manager = app.hooks_manager

# Get system prompt with CLAUDE.md
system_prompt = app.get_system_prompt()
```

## Project Structure

```
cli/
├── cc/                     # Main package
│   ├── __init__.py         # Package exports and version
│   ├── main.py             # CLI entry point (argparse)
│   ├── app.py              # Application context (dependency injection)
│   ├── repl.py             # Interactive REPL engine
│   ├── print_mode.py       # Non-interactive print mode
│   ├── conversation.py     # Core conversation management (AGENTIC LOOP)
│   ├── api/                # Anthropic API integration
│   │   ├── client.py       # API client wrapper
│   │   └── models.py       # Model aliases and validation
│   ├── config/             # Configuration management
│   │   ├── settings.py     # Settings file handling
│   │   └── paths.py        # Path constants and utilities
│   ├── hooks/              # Hooks system
│   │   └── hooks.py        # Hook events and execution
│   ├── session/            # Session management
│   │   ├── manager.py      # Session lifecycle management
│   │   └── storage.py      # JSONL session storage
│   ├── tools/              # Tool implementations
│   │   ├── base.py         # Base tool class
│   │   ├── bash.py         # Bash command execution
│   │   ├── read.py         # File reading
│   │   ├── write.py        # File writing
│   │   ├── edit.py         # File editing
│   │   ├── glob.py         # File pattern matching
│   │   ├── grep.py         # Content searching
│   │   └── executor.py     # Tool execution with permissions
│   └── ui/                 # User interface components
│       ├── renderer.py     # Output rendering (markdown)
│       ├── prompt.py       # Input prompt handling
│       ├── spinner.py      # Loading spinners
│       └── colors.py       # Terminal colors
├── tests/                  # Test suite (112 tests)
│   ├── test_conversation.py  # NEW: Agentic loop tests
│   └── ...
├── setup.py                # Package installation
├── pyproject.toml          # Modern Python packaging
└── requirements.txt        # Dependencies
```

## Troubleshooting

### Common Issues

#### API Key Errors

**Problem**: `APIKeyError: Anthropic API key required`

**Solution**:
```bash
# Set your API key in your shell profile (~/.bashrc, ~/.zshrc, etc.)
export ANTHROPIC_API_KEY='your-api-key-here'

# Or set it for the current session
export ANTHROPIC_API_KEY='your-api-key-here'
cc

# Get your API key at: https://console.anthropic.com/settings/keys
```

**Problem**: `Invalid API key`

**Solution**:
- Verify your API key is correct (no extra spaces)
- Check that the key hasn't expired
- Ensure you have API access enabled on your account

#### Connection Issues

**Problem**: `Network connection failed`

**Solution**:
- Check your internet connection
- Verify you can reach `api.anthropic.com`
- Check if you're behind a proxy or firewall
- Try again - the CLI automatically retries with exponential backoff

**Problem**: `Rate limit exceeded`

**Solution**:
- Wait a few minutes before trying again
- Consider upgrading your API plan for higher rate limits
- The CLI will automatically retry with backoff

#### Session and Storage Issues

**Problem**: `No previous session found to continue`

**Solution**:
```bash
# List all sessions to find the one you want
cc sessions list

# Resume a specific session by ID
cc -r <session-id>

# Or just start a new session
cc
```

**Problem**: `Permission denied` when accessing session files

**Solution**:
```bash
# Check ~/.cc/sessions directory permissions
ls -la ~/.cc/sessions

# Fix permissions if needed
chmod 755 ~/.cc
chmod -R 644 ~/.cc/sessions/*
```

#### Configuration Issues

**Problem**: Settings not being applied

**Solution**:
```bash
# Check your settings hierarchy (later settings override earlier ones)
# 1. Defaults (built-in)
# 2. User settings: ~/.cc/settings.json
# 3. User local: ~/.cc/settings.local.json
# 4. Project: .cc/settings.json
# 5. Project local: .cc/settings.local.json
# 6. CLI arguments

# View current configuration
cc config list

# Set a configuration value
cc config set model sonnet
```

**Problem**: Malformed JSON in settings file

**Solution**:
```bash
# Validate your JSON
cat ~/.cc/settings.json | python -m json.tool

# Or fix manually
nano ~/.cc/settings.json

# Example valid settings.json:
{
  "model": "claude-sonnet-4-5-20250929",
  "maxTokens": 8192
}
```

#### Tool Execution Issues

**Problem**: `Permission denied for <tool>`

**Solution**:
```bash
# Check your permission settings
cc /permissions

# To allow all tools (use with caution):
cc --dangerously-skip-permissions

# To allow specific tools:
cc --allowedTools "Bash(git:*)" "Read" "Write"

# To deny specific dangerous operations:
cc --disallowedTools "Bash(rm:*)" "Bash(sudo:*)"
```

**Problem**: File operations failing

**Solution**:
- Ensure the file paths are correct (use absolute paths when possible)
- Check file/directory permissions
- Verify the current working directory with `/status`
- Make sure you have write permissions for the target directory

#### REPL Issues

**Problem**: Terminal display issues (garbled output, colors not working)

**Solution**:
```bash
# Disable markdown rendering if causing issues
cc --no-markdown

# Check terminal support
echo $TERM
# Should be something like: xterm-256color

# Use a modern terminal:
# - macOS: iTerm2
# - Windows: Windows Terminal
# - Linux: Alacritty, Kitty, or GNOME Terminal
```

**Problem**: Input not working correctly

**Solution**:
- Make sure you're using a compatible terminal
- Try updating Python's `prompt_toolkit` library
- Check for shell conflicts (tmux, screen, etc.)

**Problem**: Interrupting (Ctrl+C) not working properly

**Solution**:
- Press Ctrl+C during response to stop streaming
- Press Ctrl+D to exit the REPL completely
- Use `/exit` or `/quit` command

#### Model and Response Issues

**Problem**: Responses are incomplete or cut off

**Solution**:
```bash
# Increase max tokens
cc -m sonnet --max-tokens 16384

# Or set in configuration
cc config set maxTokens 16384
```

**Problem**: "Unknown model" error

**Solution**:
```bash
# Use model alias
cc -m sonnet
cc -m opus
cc -m haiku

# Or use full model ID
cc -m claude-sonnet-4-5-20250929
```

#### Installation Issues

**Problem**: `cc` command not found after installation

**Solution**:
```bash
# Ensure package is installed
pip list | grep cc-cli

# Reinstall if needed
pip install -e .

# Check that entry point is correct
which cc
```

**Problem**: Import errors or missing dependencies

**Solution**:
```bash
# Reinstall with all dependencies
pip install -e ".[dev]"

# Or install specific missing package
pip install <package-name>
```

### Health Check

Run the built-in diagnostic tool:

```bash
cc
> /doctor
```

This checks:
- API key configuration
- Configuration directory setup
- CLAUDE.md presence
- Hooks configuration
- MCP servers

### Getting Help

If you're still experiencing issues:

1. **Run with verbose mode**:
   ```bash
   cc --verbose
   ```

2. **Check the logs**: Session files are stored in `~/.cc/sessions/`

3. **Report an issue**: https://github.com/anthropics/claude-code/issues
   - Include the error message
   - Include your Python version: `python --version`
   - Include your OS
   - Include steps to reproduce

### Performance Tips

**Reduce token usage**:
```bash
# Compact conversation history
> /compact

# Or start fresh
> /clear
```

**Optimize for speed**:
```bash
# Use faster model
cc -m haiku

# Reduce max tokens for shorter responses
cc --max-tokens 4096
```

**Session management**:
```bash
# List sessions to find old ones
cc sessions list

# Delete old sessions
cc sessions delete <session-id>

# Export session before deleting
cc sessions export <session-id> > backup.json
```

## License

MIT
