# Claude Code CLI Research Document

## Overview

This document contains comprehensive research on the Claude Code CLI (`claude` command) for building a complete clone.

**Version Analyzed**: 2.0.55 (Claude Code)

---

## 1. CLI Commands and Options

### Main Usage
```
claude [options] [command] [prompt]
```

### Global Options

| Option | Description |
|--------|-------------|
| `-d, --debug [filter]` | Enable debug mode with optional category filtering (e.g., "api,hooks" or "!statsig,!file") |
| `--verbose` | Override verbose mode setting from config |
| `-p, --print` | Print response and exit (useful for pipes). Skips workspace trust dialog |
| `--output-format <format>` | Output format with --print: "text" (default), "json", "stream-json" |
| `--json-schema <schema>` | JSON Schema for structured output validation |
| `--include-partial-messages` | Include partial message chunks (with --print and stream-json) |
| `--input-format <format>` | Input format with --print: "text" (default), "stream-json" |
| `--dangerously-skip-permissions` | Bypass all permission checks (sandbox only) |
| `--allow-dangerously-skip-permissions` | Enable bypassing permissions as option |
| `--replay-user-messages` | Re-emit user messages from stdin (stream-json input/output) |
| `--allowedTools, --allowed-tools <tools...>` | Comma/space-separated list of allowed tools (e.g., "Bash(git:*) Edit") |
| `--tools <tools...>` | Specify available tools: "", "default", or specific names (--print only) |
| `--disallowedTools, --disallowed-tools <tools...>` | Comma/space-separated list of denied tools |
| `--mcp-config <configs...>` | Load MCP servers from JSON files or strings |
| `--system-prompt <prompt>` | System prompt for the session |
| `--append-system-prompt <prompt>` | Append to default system prompt |
| `--permission-mode <mode>` | Permission mode: acceptEdits, bypassPermissions, default, dontAsk, plan |
| `-c, --continue` | Continue the most recent conversation |
| `-r, --resume [sessionId]` | Resume a conversation by session ID or interactive selection |
| `--fork-session` | Create new session ID when resuming (with --resume or --continue) |
| `--model <model>` | Model for session: alias ('sonnet', 'opus') or full name |
| `--fallback-model <model>` | Fallback model when default overloaded (--print only) |
| `--settings <file-or-json>` | Path to settings JSON file or JSON string |
| `--add-dir <directories...>` | Additional directories for tool access |
| `--ide` | Auto-connect to IDE if exactly one valid IDE available |
| `--strict-mcp-config` | Only use MCP servers from --mcp-config |
| `--session-id <uuid>` | Use specific session ID (must be valid UUID) |
| `--agents <json>` | JSON object defining custom agents |
| `--setting-sources <sources>` | Comma-separated setting sources: user, project, local |
| `--plugin-dir <paths...>` | Load plugins from directories for this session |
| `-v, --version` | Output version number |
| `-h, --help` | Display help |

### Subcommands

| Command | Description |
|---------|-------------|
| `mcp` | Configure and manage MCP servers |
| `plugin` | Manage Claude Code plugins |
| `migrate-installer` | Migrate from global npm to local installation |
| `setup-token` | Set up long-lived authentication token |
| `doctor` | Check health of auto-updater |
| `update` | Check for updates and install |
| `install [target]` | Install native build (stable, latest, or specific version) |

---

## 2. MCP Subcommand

```
claude mcp [options] [command]
```

### MCP Commands

| Command | Description |
|---------|-------------|
| `serve [options]` | Start the Claude Code MCP server |
| `add [options] <name> <commandOrUrl> [args...]` | Add an MCP server |
| `remove [options] <name>` | Remove an MCP server |
| `list` | List configured MCP servers |
| `get <name>` | Get details about an MCP server |
| `add-json [options] <name> <json>` | Add MCP server with JSON string |
| `add-from-claude-desktop [options]` | Import MCP servers from Claude Desktop |
| `reset-project-choices` | Reset approved/rejected project-scoped servers |

### MCP Add Examples
```bash
# HTTP server
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp

# SSE server
claude mcp add --transport sse asana https://mcp.asana.com/sse

# stdio server
claude mcp add --transport stdio airtable --env AIRTABLE_API_KEY=KEY -- npx -y airtable-mcp-server
```

---

## 3. Plugin Subcommand

```
claude plugin [options] [command]
```

### Plugin Commands

| Command | Description |
|---------|-------------|
| `validate <path>` | Validate a plugin or marketplace manifest |
| `marketplace` | Manage Claude Code marketplaces |
| `install\|i <plugin>` | Install a plugin (use plugin@marketplace for specific) |
| `uninstall\|remove <plugin>` | Uninstall an installed plugin |
| `enable <plugin>` | Enable a disabled plugin |
| `disable <plugin>` | Disable an enabled plugin |

---

## 4. Directory Structure (~/.claude/)

### Root Directory Contents

| Path | Type | Description |
|------|------|-------------|
| `settings.json` | File | Global user settings |
| `settings.local.json` | File | Local machine settings (not synced) |
| `history.jsonl` | File | Command history (all user prompts) |
| `projects/` | Dir | Project-specific session data |
| `file-history/` | Dir | File backup versions per session |
| `todos/` | Dir | Todo list state per session |
| `session-env/` | Dir | Session environment snapshots |
| `shell-snapshots/` | Dir | Shell environment snapshots |
| `debug/` | Dir | Debug logs per session |
| `plans/` | Dir | Plan mode plans (currently empty) |
| `statsig/` | Dir | Feature flag evaluations and IDs |
| `.search_cache/` | Dir | Search result caching |
| `plugins/` | Dir | Installed plugins (installed_plugins.json) |
| `skills/` | Dir | User-defined skills |

### Project Directory Structure

Projects are stored under `~/.claude/projects/` with directory names based on the path (e.g., `-Users-tonyjabroni-claude/`).

Each project directory contains:
- `<uuid>.jsonl` - Conversation session files
- `agent-<shortid>.jsonl` - Subagent/task sessions

---

## 5. Settings File Formats

### settings.json (Global)
```json
{
  "permissions": {
    "defaultMode": "dontAsk"  // or "default", "acceptEdits", "plan", "bypassPermissions"
  }
}
```

### settings.local.json (Per-machine)
```json
{
  "permissions": {
    "allow": ["Bash(echo:*)"],  // Tool permission patterns
    "deny": [],
    "ask": []
  }
}
```

### Project .claude/settings.local.json
```json
{
  "spinnerTipsEnabled": false,
  "outputStyle": "default"
}
```

---

## 6. Conversation Session Format (JSONL)

Each line in session `.jsonl` files is a JSON object with different `type` values:

### File History Snapshot
```json
{
  "type": "file-history-snapshot",
  "messageId": "uuid",
  "snapshot": {
    "messageId": "uuid",
    "trackedFileBackups": {},
    "timestamp": "ISO-8601"
  },
  "isSnapshotUpdate": false
}
```

### User Message
```json
{
  "parentUuid": null,
  "isSidechain": false,
  "userType": "external",
  "cwd": "/path/to/dir",
  "sessionId": "uuid",
  "version": "2.0.55",
  "gitBranch": "",
  "type": "user",
  "message": {
    "role": "user",
    "content": "user prompt text"
  },
  "uuid": "message-uuid",
  "timestamp": "ISO-8601",
  "thinkingMetadata": {
    "level": "none",
    "disabled": true,
    "triggers": []
  },
  "todos": []
}
```

### Assistant Message
```json
{
  "parentUuid": "previous-uuid",
  "isSidechain": false,
  "userType": "external",
  "cwd": "/path/to/dir",
  "sessionId": "uuid",
  "version": "2.0.55",
  "gitBranch": "",
  "message": {
    "model": "claude-opus-4-5-20251101",
    "id": "msg_xxx",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "response"}],
    "stop_reason": null,
    "stop_sequence": null,
    "usage": {
      "input_tokens": 2,
      "cache_creation_input_tokens": 5817,
      "cache_read_input_tokens": 12610,
      "output_tokens": 1
    }
  },
  "requestId": "req_xxx",
  "type": "assistant",
  "uuid": "message-uuid",
  "timestamp": "ISO-8601"
}
```

---

## 7. History File Format (history.jsonl)

Each line is a prompt entry:
```json
{
  "display": "user prompt text",
  "pastedContents": {},
  "timestamp": 1761307454906,
  "project": "/Users/tonyjabroni"
}
```

---

## 8. Todos File Format

JSON array of todo items:
```json
[
  {
    "content": "Task description",
    "status": "in_progress",  // or "pending", "completed"
    "activeForm": "Present participle form of task"
  }
]
```

---

## 9. File History Format

Files in `file-history/<session-id>/` are versioned backups:
- Filename format: `<hash>@v<version>`
- Contains raw file content for rollback

---

## 10. Debug Log Format

Text files containing timestamped debug entries:
```
2025-12-06T00:53:40.324Z [DEBUG] Message text here
```

Categories include:
- LSP MANAGER
- LSP SERVER MANAGER
- Plugin loading
- Skills loading
- Hook matching
- Git operations
- File operations

---

## 11. Slash Commands (Known)

Based on USER_PROMPT.md requirements:
- `/help` - Display help
- `/clear` - Clear conversation
- `/compact` - Compact conversation history
- `/config` - Configuration management
- `/cost` - Show cost tracking
- `/doctor` - Health check
- `/init` - Initialize project
- `/memory` - Memory/context management
- `/model` - Model selection
- `/permissions` - Permission management
- `/review` - Code review
- `/status` - Show status
- `/terminal-setup` - Terminal configuration
- `/vim` - Vim mode

Additional likely commands based on debug logs:
- Custom commands from `.claude/commands/` directory

---

## 12. Tool System

### Known Built-in Tools
Based on `--allowedTools` examples:
- `Bash` - Execute bash commands
- `Edit` - Edit files
- `Read` - Read files (implicit)
- `Write` - Write files (implicit)

Tool patterns support glob-like syntax:
- `Bash(git:*)` - Allow all git commands
- `Bash(echo:*)` - Allow all echo commands

---

## 13. Hooks System

Hooks trigger on events (from debug logs):
- `SubagentStart` - When launching subagents
- `PreToolUse` - Before tool execution
- `PostToolUse` - After tool execution

Hook configuration in settings with matchers for queries.

---

## 14. Skills and Plugins

### Skills Directories
- Managed: `/Library/Application Support/ClaudeCode/.claude/skills`
- User: `~/.claude/skills`
- Project: `<project>/.claude/skills`

### Plugins
- Installed plugins tracked in `~/.claude/plugins/installed_plugins.json`
- Can provide skills, commands, and hooks

---

## 15. Permission System

### Permission Modes
| Mode | Description |
|------|-------------|
| `default` | Ask for each tool use |
| `dontAsk` | Don't ask for confirmations |
| `acceptEdits` | Auto-accept file edits |
| `bypassPermissions` | Bypass all checks |
| `plan` | Plan mode (read-only) |

### Permission Patterns
```json
{
  "allow": ["Bash(git:*)"],
  "deny": ["Bash(rm:*)"],
  "ask": ["Bash(sudo:*)"]
}
```

---

## 16. Session Management

### Session IDs
- UUIDs for main sessions
- `agent-<shortid>` for subagent sessions

### Session Continuity
- `-c` continues most recent session
- `-r <id>` resumes specific session
- `--fork-session` creates new ID from existing

---

## 17. Model Selection

### Aliases
- `sonnet` - Latest Sonnet model
- `opus` - Latest Opus model

### Full Names
- `claude-opus-4-5-20251101`
- `claude-sonnet-4-5-20250929`

---

## 18. Output Formats

### Print Mode (`--print`)
| Format | Description |
|--------|-------------|
| `text` | Plain text output |
| `json` | Single JSON result |
| `stream-json` | Realtime streaming JSON |

---

## 19. CLAUDE.md Files

Project instructions file that gets automatically loaded:
- `CLAUDE.md` in project root
- Can contain user-specific instructions for Claude
- Automatically included in context

---

## 20. Implementation Requirements

Based on this research, the clone (`cc`) must implement:

### Core Features
1. Interactive REPL with streaming responses
2. One-shot mode (`-p/--print`)
3. Session continuation (`-c`, `-r`)
4. Tool system (Bash, Edit, Read, Write)
5. Permission system with patterns
6. Configuration management
7. History tracking
8. Cost tracking

### Directory/File Management
1. `~/.cc/` (or similar) config directory
2. Session storage with JSONL format
3. File history backups
4. Todos tracking
5. Debug logging

### Slash Commands
1. `/help`, `/clear`, `/compact`, `/config`
2. `/cost`, `/model`, `/permissions`, `/status`
3. Custom commands from `.claude/commands/`

### Advanced Features
1. MCP server support
2. Plugin system
3. Hooks system
4. Subagent/task launching
5. Plan mode

---

## 21. API Integration

Uses Anthropic Python SDK:
- Messages API with streaming
- Tool use (function calling)
- System prompts
- Multi-turn conversations
- Caching (cache_creation_input_tokens, cache_read_input_tokens)

---

## Summary

The Claude Code CLI is a sophisticated tool with:
- Complex session management
- Rich configuration hierarchy
- Extensible plugin/skill system
- Tool-based interaction model
- Comprehensive history and debugging

The clone should prioritize:
1. Core REPL functionality
2. Tool system implementation
3. Session persistence
4. Configuration management
5. Then advanced features (MCP, plugins, hooks)
