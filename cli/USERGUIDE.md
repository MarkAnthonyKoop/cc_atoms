# CC CLI User Guide

Complete guide to using the CC CLI (Claude Code CLI clone).

## Table of Contents

- [Quick Start](#quick-start)
- [Interactive Mode](#interactive-mode)
- [Print Mode](#print-mode)
- [Session Management](#session-management)
- [Configuration](#configuration)
- [Tools and Permissions](#tools-and-permissions)
- [Hooks System](#hooks-system)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)

## Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/yourusername/cc-cli.git
cd cc-cli
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY='your-api-key-here'

# Start CC CLI
cc
```

### Your First Conversation

```bash
# Start interactive mode
cc

# CC CLI will show a prompt:
> Hello, Claude!

# Claude will respond and you can continue the conversation
> Can you help me write a Python function?
```

## Interactive Mode

Interactive mode provides a REPL (Read-Eval-Print-Loop) for conversing with Claude.

### Starting Interactive Mode

```bash
# Start with default settings
cc

# Start with a specific model
cc -m haiku

# Start with an initial prompt
cc -p "Explain async/await in Python"

# Continue your last conversation
cc -c

# Resume a specific session
cc -r abc123def456
```

### REPL Commands

All REPL commands start with `/`:

#### Essential Commands

```bash
/help          # Show all available commands
/exit          # Exit the REPL (or use Ctrl+D)
/quit          # Same as /exit
/clear         # Clear conversation history
/status        # Show session information
```

#### Configuration Commands

```bash
/config                 # Show all settings
/config <key>           # Get specific setting
/config <key>=<value>   # Set a setting

# Examples:
/config model=opus
/config maxTokens=8192
```

#### Model Commands

```bash
/model          # Show current model
/model sonnet   # Switch to Sonnet
/model opus     # Switch to Opus
/model haiku    # Switch to Haiku
```

#### Session Commands

```bash
/sessions       # List recent sessions
/memory         # Show context information
/cost           # Show token usage and estimated cost
/compact        # Reduce context by compacting history
```

#### Utility Commands

```bash
/doctor         # Run health check
/init           # Initialize project config
/permissions    # View/change permission mode
/hooks          # Show configured hooks
/review         # Review uncommitted git changes
/terminal-setup # Show terminal setup info
/vim            # Toggle vim mode (experimental)
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel current operation |
| `Ctrl+D` | Exit REPL |
| `Esc+Enter` | Submit multiline input |
| `↑` / `↓` | Navigate command history |
| `Tab` | Auto-complete commands |

### Multiline Input

For multiline prompts, just keep typing. Press `Esc+Enter` to submit.

```bash
> Please review this code:
...
... def hello():
...     print("Hello, world!")
...
[Press Esc+Enter to submit]
```

## Print Mode

Print mode is for non-interactive use, perfect for scripts and pipelines.

### Basic Usage

```bash
# Single prompt with text output
cc --print -p "What is 2+2?"

# Pipe input
echo "Explain recursion" | cc --print

# Redirect output
cc --print -p "Generate a README template" > README.md
```

### Output Formats

```bash
# Plain text (default)
cc --print -p "Hello"

# JSON output
cc --print --output-format json -p "Hello"

# Streaming JSON (for tool tracking)
cc --print --output-format stream-json -p "List files"
```

### Use Cases

**Generate files:**
```bash
cc --print -p "Create a Python hello world" > hello.py
```

**Process logs:**
```bash
cat error.log | cc --print -p "Summarize these errors"
```

**Scripting:**
```bash
#!/bin/bash
response=$(cc --print -p "Suggest a project name for a chat app")
echo "Project name: $response"
```

## Session Management

CC CLI automatically saves all conversations to sessions.

### Session Files

Sessions are stored in `~/.cc/sessions/` as JSONL files:

```
~/.cc/sessions/
├── project_abc123def.jsonl
├── project_xyz789ghi.jsonl
└── ...
```

### Managing Sessions

```bash
# List all sessions
cc sessions list

# Export a session to JSON
cc sessions export abc123

# Export to file
cc sessions export abc123 > session-backup.json

# Delete a session
cc sessions delete abc123

# Continue last session
cc -c

# Resume specific session
cc -r abc123
```

### Session Organization

Sessions are project-scoped. Each project directory gets its own sessions:

```bash
cd ~/project-a
cc -p "Help with project A"  # Creates session for project-a

cd ~/project-b
cc -p "Help with project B"  # Creates separate session for project-b

cd ~/project-a
cc -c  # Continues project-a session
```

## Configuration

CC CLI uses a hierarchical configuration system.

### Configuration Hierarchy

Settings are merged in this order (later overrides earlier):

1. **Built-in defaults**
2. **User global**: `~/.cc/settings.json`
3. **User local**: `~/.cc/settings.local.json`
4. **Project**: `.cc/settings.json`
5. **Project local**: `.cc/settings.local.json`
6. **CLI arguments**

### Common Settings

Create `~/.cc/settings.json`:

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

### All Available Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `model` | string | Model to use | `claude-sonnet-4-5-20250929` |
| `maxTokens` | number | Max response tokens | `8192` |
| `markdown` | boolean | Enable markdown rendering | `true` |
| `permissions.defaultMode` | string | Permission mode | `default` |
| `skipPermissions` | boolean | Skip all permission checks | `false` |
| `allowedTools` | array | Allowed tool patterns | `[]` |
| `disallowedTools` | array | Disallowed tool patterns | `[]` |
| `hooks` | object | Hook configurations | `{}` |
| `mcpServers` | object | MCP server configs | `{}` |

### Using CLI Arguments

Override any setting with CLI flags:

```bash
# Override model
cc -m opus

# Override max tokens
cc --max-tokens 16384

# Skip permissions
cc --dangerously-skip-permissions

# Set working directory
cc -d /path/to/project
```

## Tools and Permissions

Claude can use tools to interact with your system.

### Available Tools

| Tool | Description | Example Use |
|------|-------------|-------------|
| `Bash` | Execute shell commands | Run tests, git operations |
| `Read` | Read file contents | View code, config files |
| `Write` | Write files | Create new files |
| `Edit` | Precise string replacements | Update existing code |
| `Glob` | Find files by pattern | Search for `*.py` files |
| `Grep` | Search file contents | Find TODO comments |

### Permission Modes

```bash
# View current permission mode
cc
> /permissions

# Change permission mode
> /permissions dontAsk
```

| Mode | Description | Use When |
|------|-------------|----------|
| `default` | Ask for each tool use | Normal use, stay in control |
| `dontAsk` | Auto-approve all tools | Trusted operations |
| `acceptEdits` | Auto-approve file edits | Code generation workflows |
| `plan` | Read-only (no modifications) | Exploring/analyzing code |

### Tool Patterns

Control which tools are allowed:

```bash
# Allow only specific git commands
cc --allowedTools "Bash(git:*)"

# Allow multiple patterns
cc --allowedTools "Bash(git:*)" "Read" "Glob" "Grep"

# Deny dangerous operations
cc --disallowedTools "Bash(rm:*)" "Bash(sudo:*)"
```

### Pattern Syntax

```
Tool                  # Match all uses of Tool
Bash                  # Match all Bash commands
Bash(git:*)           # Match all git commands
Bash(git:commit)      # Match specific git subcommand
Read                  # Match all Read operations
Read(/etc/*)          # Match reads from /etc/ (not implemented)
```

## Hooks System

Hooks run shell commands at specific events.

### Hook Events

- `PreToolUse` - Before a tool executes
- `PostToolUse` - After a tool executes
- `UserPromptSubmit` - When user sends a message

### Configuration

Add hooks to your `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "echo 'About to execute tool'",
        "matchers": ["Bash"]
      }
    ],
    "PostToolUse": [
      "echo 'Tool execution completed'"
    ],
    "UserPromptSubmit": [
      {
        "command": "date >> prompts.log",
        "matchers": []
      }
    ]
  }
}
```

### Use Cases

**Logging:**
```json
{
  "hooks": {
    "PostToolUse": ["echo \"$(date): Tool used\" >> ~/.cc/tool-log.txt"]
  }
}
```

**Notifications:**
```json
{
  "hooks": {
    "PostToolUse": ["osascript -e 'display notification \"Tool completed\"'"]
  }
}
```

**Validation:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "./validate-before-tool.sh",
        "matchers": ["Write", "Edit"]
      }
    ]
  }
}
```

## Advanced Features

### CLAUDE.md Files

CC CLI automatically loads `CLAUDE.md` from your project:

```markdown
<!-- CLAUDE.md -->
# Project: My Web App

This is a FastAPI web application.

## Code Style
- Use type hints
- Follow PEP 8
- Write tests for new features

## Architecture
- `app/` - Main application
- `tests/` - Test suite
- `docs/` - Documentation
```

Claude will see these instructions in every conversation.

### Custom Slash Commands

Create custom commands in `.cc/commands/`:

```bash
# Create command
mkdir -p .cc/commands
cat > .cc/commands/review-pr.md << 'EOF'
Please review the current pull request:
1. Check code quality
2. Look for bugs
3. Suggest improvements

Use git diff to see changes.
EOF

# Use command
cc
> /review-pr
```

**With arguments:**

```bash
# .cc/commands/explain.md
Please explain this file: $ARGS
```

```bash
cc
> /explain src/main.py
```

### MCP Servers

Configure Model Context Protocol servers:

```bash
# Add MCP server
cc mcp add my-server --command "node" --args "server.js"

# List servers
cc mcp list

# Remove server
cc mcp remove my-server
```

Or in `settings.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    }
  }
}
```

## Best Practices

### Efficient Token Usage

**Compact long conversations:**
```bash
> /compact
```

**Start fresh when changing topics:**
```bash
> /clear
```

**Use appropriate models:**
- `haiku` - Fast, cheap for simple tasks
- `sonnet` - Balanced for most work
- `opus` - Most capable for complex tasks

### Security

**Never skip permissions for untrusted prompts:**
```bash
# Bad: running unknown commands
cc --dangerously-skip-permissions -p "$(curl malicious-site.com/prompt)"

# Good: review first
cc -p "Help me with this task"
# Review each tool use before approving
```

**Use deny lists for dangerous operations:**
```json
{
  "disallowedTools": [
    "Bash(rm:*)",
    "Bash(sudo:*)",
    "Bash(dd:*)",
    "Write(/etc/*)"
  ]
}
```

### Project Organization

**Use `.cc/` for project-specific config:**
```
my-project/
├── .cc/
│   ├── settings.json       # Project settings
│   └── commands/           # Custom commands
│       └── test.md
├── CLAUDE.md               # Project instructions
└── src/
```

**Use `.gitignore`:**
```
.cc/settings.local.json
.cc/sessions/
```

### Performance

**Limit context size:**
```json
{
  "maxTokens": 4096
}
```

**Use print mode for automation:**
```bash
# Faster than interactive
cc --print -p "Quick task"
```

**Close old sessions:**
```bash
cc sessions list
cc sessions delete <old-session-id>
```

### Collaboration

**Share project config:**
```bash
git add .cc/settings.json CLAUDE.md
git commit -m "Add CC CLI project config"
```

**Document custom commands:**
```markdown
<!-- README.md -->
## Claude Commands

- `/test` - Run test suite and analyze results
- `/review-pr` - Review current PR
```

### Troubleshooting

**Check health:**
```bash
cc
> /doctor
```

**Enable verbose mode:**
```bash
cc --verbose
```

**View session details:**
```bash
cc sessions export | less
```

---

## Quick Reference

### Command Cheat Sheet

```bash
# Start CC CLI
cc                              # Interactive mode
cc -p "prompt"                  # With initial prompt
cc -c                           # Continue last session
cc --print                      # Print mode

# REPL commands
/help                           # Show help
/status                         # Session info
/cost                           # Token usage
/clear                          # Clear history
/model <name>                   # Change model
/exit                           # Quit

# Subcommands
cc sessions list                # List sessions
cc config list                  # Show config
cc mcp list                     # List MCP servers
```

### Useful Patterns

```bash
# Generate code to file
cc --print -p "Python hello world" > hello.py

# Process with pipe
cat error.log | cc --print -p "Summarize errors"

# Safe execution with review
cc --allowedTools "Read" "Glob" "Grep"

# Code review workflow
cc -p "Review uncommitted changes" --allowedTools "Bash(git:*)" "Read"
```

---

For more help, visit the [README](README.md) or [CONTRIBUTING](CONTRIBUTING.md) guide.
