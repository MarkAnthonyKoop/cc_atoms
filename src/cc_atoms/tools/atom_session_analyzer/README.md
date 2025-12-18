# atom_session_analyzer - Claude Code Session Analysis Tool

## Quick Start

**Extract current session log:**
```bash
atom_session_analyzer
# Outputs: /path/to/current/dir/session_log.md
```

**Analyze session with AI:**
```bash
atom_session_analyzer "summarize the key decisions and files created"
atom_session_analyzer "extract all Python code and create separate files"
atom_session_analyzer "create a detailed error report with solutions"
atom_session_analyzer "generate API documentation from this session"
```

## What This Tool Does

`atom_session_analyzer` combines session extraction with AI-powered analysis:

1. **Extracts** your current Claude Code session using `claude-conversation-extractor`
2. **Saves** it as `session_log.md` with full detail (includes all tool calls)
3. **Optionally** spawns an AI agent to analyze the session based on your prompt

The AI agent has access to:
- Your complete session log
- All `claude-conversation-extractor` commands for cross-session analysis
- Full file system access to create reports, extract code, etc.

## Examples

### Extract Session Only
```bash
# Just get the log file path
cd ~/my-project
atom_session_analyzer
# Output: /home/user/my-project/session_log.md
```

### Generate Session Summary
```bash
atom_session_analyzer "Create a summary.md with: 1) key topics discussed, 2) files created/modified, 3) important decisions made"
```

### Extract Code from Session
```bash
atom_session_analyzer "Extract all code blocks, organize by language, save to ./code/ directory with descriptive filenames"
```

### Error Analysis
```bash
atom_session_analyzer "Find all errors in the session, document what caused them and how they were resolved, create error_report.md"
```

### Cross-Session Analysis
```bash
atom_session_analyzer "Search my other sessions for related work on authentication, compare approaches, create comparison.md"
```

### Documentation Generation
```bash
atom_session_analyzer "Generate a comprehensive README.md for this project based on what was built in this session"
```

## How It Works

1. **Extraction**: Uses `claude-extract --extract 1 --detailed` to get your current session
2. **Naming**: Renames to `session_log.md` for consistent access
3. **Analysis** (if prompt provided):
   - Creates a subproject directory (handled by atom system)
   - Loads `ATOM.md` + `ATOM_SESSION_ANALYZER.md` prompts
   - Spawns AI agent with your analysis prompt
   - Agent reads `../session_log.md` and performs requested analysis
   - Returns results via stdout/files

## Installation

This tool requires:
- `claude-conversation-extractor` (installed via pipx)
- `atom` command in PATH

```bash
# Install prerequisites
pipx install claude-conversation-extractor

# The tool is in ~/cc_atoms/tools/session_logger/
# Add to PATH or copy to ~/cc_atoms/bin/
```

---

# Research and Tool Comparison

## Overview

This document provides a comprehensive analysis of existing tools for logging and exporting Claude Code sessions. Multiple mature, well-maintained tools already exist for this purpose.

## Status

COMPLETE - Research phase completed. Adequate tools exist; custom tool development not required.

## Research Findings

Claude Code stores all conversations in `~/.claude/projects/` as JSONL files. Several third-party tools have been developed to extract and export these conversations.

## Recommended Tools

### 1. claude-conversation-extractor (Python)

**Repository**: https://github.com/ZeroSumQuant/claude-conversation-extractor
**PyPI**: https://pypi.org/project/claude-conversation-extractor/

#### Features
- Automatically locates conversations in `~/.claude/projects/`
- Multiple export formats: Markdown, JSON, HTML
- Interactive UI with real-time search
- Bulk export capabilities
- 100% local operation (no internet required)
- Cross-platform (Windows, macOS, Linux)
- Open source with no tracking/telemetry

#### Installation
```bash
pipx install claude-conversation-extractor
```

#### Usage Examples
```bash
# Interactive UI with search
claude-start

# Export all conversations
claude-extract --all

# Search conversations
claude-search "API integration"

# Export with specific format
claude-extract --format html --detailed

# Export as JSON
claude-extract --format json
```

#### Export Formats
- **Markdown**: Clean, human-readable text format
- **JSON**: Structured data with full metadata
- **HTML**: Web-viewable with syntax highlighting

#### Best For
- Users who want an interactive UI
- Real-time search across conversation history
- Simple, straightforward extraction
- Privacy-conscious users (100% local)

---

### 2. claude-code-exporter (Node.js)

**Repository**: https://github.com/developerisnow/claude-code-exporter
**MCP Server**: Available for Claude Desktop (v2.0.1+)

#### Features
- Multiple export modes:
  - Prompts only (default)
  - Assistant outputs only
  - Full conversations
- Aggregate conversations across multiple projects
- Time-based filtering (7 days, 2 weeks, 30 days, etc.)
- Group exports by daily, weekly, monthly periods
- Nested directory structure support
- MCP (Model Context Protocol) server integration

#### Installation
```bash
# Global installation
npm install -g claude-code-exporter

# Local project installation
npm install claude-code-exporter

# Run without installation
npx claude-code-exporter /path/to/project
```

#### Usage Examples
```bash
# Basic export (prompts only)
claude-prompts

# Aggregate all projects
claude-prompts --aggregate

# Export last 30 days
claude-prompts --aggregate --period=30d

# Export full conversations as JSON
claude-prompts --mode=full --format=json

# Export to specific directory
claude-prompts --output=/path/to/exports
```

#### Export Formats
- **Markdown**: Human-readable format
- **JSON**: Structured data format
- **Both**: Export in both formats simultaneously

#### Best For
- JavaScript/Node.js users
- Aggregating multiple projects
- Time-based filtering and analysis
- MCP server integration with Claude Desktop
- Advanced filtering and organization needs

---

### 3. claude-history (Python)

**Repository**: https://github.com/thejud/claude-history

#### Features
- Parses JSONL session files from `~/.claude/projects/`
- Extracts user prompts with optional assistant responses
- Generates chronologically sorted markdown reports
- Lightweight with no external dependencies
- Simple command-line interface

#### Installation
```bash
# Clone and make executable
git clone https://github.com/thejud/claude-history.git
cd claude-history
chmod +x claude_history.py
```

#### Usage Examples
```bash
# Extract from current directory
python3 claude_history.py

# Extract from specific project
python3 claude_history.py ~/my-project

# Include assistant responses
python3 claude_history.py --agent ~/my-project

# Remove timestamps
python3 claude_history.py --nodate ~/my-project
```

#### Command Line Options
- `--agent` or `-a`: Include assistant responses
- `--nodate` or `-N`: Remove timestamps
- `--help` or `-h`: Show help message

#### Output Format
- **Default**: Chronological list of user prompts with timestamps
- **With --agent**: Structured markdown with both prompts and responses

#### Best For
- Simple, lightweight extraction
- Users who prefer minimal dependencies
- Quick command-line exports
- Reviewing conversation chronology

---

## Comparison Matrix

| Feature | claude-conversation-extractor | claude-code-exporter | claude-history |
|---------|-------------------------------|----------------------|----------------|
| Language | Python | Node.js | Python |
| Interactive UI | Yes | No | No |
| Search | Yes | No | No |
| Markdown Export | Yes | Yes | Yes |
| JSON Export | Yes | Yes | No |
| HTML Export | Yes | No | No |
| Time Filtering | No | Yes | No |
| Multi-Project | Yes | Yes | Yes |
| MCP Server | No | Yes | No |
| Dependencies | pipx | npm | None |
| Installation Ease | Easy | Easy | Manual |

---

## Recommendation

**For most users**: **claude-conversation-extractor** is recommended because:
- Easy installation via pipx
- Interactive UI for browsing and searching
- Multiple export formats (Markdown, JSON, HTML)
- 100% local and privacy-focused
- Active development and maintenance

**For Node.js users** or those needing **time-based filtering**: **claude-code-exporter** is excellent for:
- Aggregating multiple projects
- Filtering by time periods
- JavaScript/TypeScript workflows
- MCP server integration

**For minimal dependencies**: **claude-history** is perfect for:
- Simple script-based extraction
- No external dependencies required
- Quick chronological reviews

---

## Claude Code Session Storage Format

All three tools parse the JSONL files stored in `~/.claude/projects/`. The directory structure follows this pattern:

```
~/.claude/projects/
  └── -path-to-project/
      └── session-<timestamp>.jsonl
```

Each JSONL file contains one JSON object per line representing a conversation turn, including:
- User prompts
- Assistant responses
- Tool use and results
- Metadata (timestamps, model info, etc.)

---

## CLI Testing Results

### claude-conversation-extractor CLI Verification

**Status**: ✅ **FULLY TESTED AND CONFIRMED**

Comprehensive CLI testing confirms that `claude-conversation-extractor` works excellently from the command line. See [CLI_TEST_REPORT.md](CLI_TEST_REPORT.md) for detailed test results.

#### Quick CLI Overview

**4 Commands Available**:
- `claude-extract` - Main extraction tool (tested ✅)
- `claude-logs` - Alias for claude-extract
- `claude-search` - Search across conversations
- `claude-start` - Interactive UI

**Key Features Tested**:
- ✅ List all sessions: `claude-extract --list`
- ✅ Extract specific session: `claude-extract --extract 1`
- ✅ Multiple formats: `--format markdown|json|html`
- ✅ Detailed mode: `--detailed` (includes tool use)
- ✅ Search functionality: `--search "query"`
- ✅ Custom output: `--output ./session_logs`

**Test Results**:
- Found 84 sessions across all projects
- Successfully extracted current session in all 3 formats:
  - Markdown: 14 KB (standard), 31 KB (detailed)
  - JSON: 16 KB with proper structure
  - HTML: 18 KB with syntax highlighting
- Detailed mode showed 46 messages vs 13 standard (includes all tool calls)
- Search found 3 matches across conversations
- All files human-readable with clean formatting

**Example Usage**:
```bash
# List all sessions
claude-extract --list

# Extract current session (usually #1) with tool details
claude-extract --extract 1 --output ./session_logs --detailed

# Search for specific topics
claude-search "authentication"

# Export last 5 sessions as JSON
claude-extract --recent 5 --format json
```

**Performance**: Installation < 10s, extraction < 1s per session, search < 2s across 84 sessions

---

## Conclusion

**No custom tool development is required.** Multiple mature, well-maintained tools already exist for logging and exporting Claude Code sessions. The recommended approach is to use one of the existing tools based on your needs:

1. **claude-conversation-extractor** - Best overall choice ✅ **CLI VERIFIED**
2. **claude-code-exporter** - Best for advanced filtering and Node.js users
3. **claude-history** - Best for minimal dependencies

All three tools are actively maintained, well-documented, and handle the undocumented JSONL format used by Claude Code.

---

## Additional Resources

- Claude Code Documentation: https://docs.claude.com/en/docs/claude-code
- Claude Code Best Practices: https://www.anthropic.com/engineering/claude-code-best-practices
- Claude Code GitHub: https://github.com/anthropics/claude-code

---

**Created**: 2025-10-13
**Status**: Research Complete
**Next Steps**: Review tools and select one for installation
