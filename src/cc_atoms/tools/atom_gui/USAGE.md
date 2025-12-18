# Atom GUI - Usage Guide

## Overview

Atom GUI is a real-time monitoring tool for atom sessions. It provides visual tracking of atom progress with two main windows:

1. **Main Window**: Displays the current/latest session with live updates
2. **Tree View Window**: Shows all sessions in an expandable tree structure

## Installation

The tool is already set up if you're in the cc_atoms ecosystem:

```bash
# The launcher is in ~/cc_atoms/bin/atom_gui
# It should be in your PATH
```

## Basic Usage

### Starting the GUI

**Monitor current directory:**
```bash
atom_gui
```

**Monitor specific directory:**
```bash
atom_gui /path/to/project
```

**Monitor from parent to see all tools:**
```bash
cd ~/cc_atoms/tools
atom_gui .
```

### Main Window Features

The main window shows:

- **Path**: Current session directory
- **Status**: Session status (COMPLETE, IN_PROGRESS, BLOCKED, NEEDS_DECOMPOSITION)
  - Color-coded for quick identification
  - Green = COMPLETE
  - Blue = IN_PROGRESS
  - Red = BLOCKED
  - Orange = NEEDS_DECOMPOSITION

- **Overview**: Brief description of what the session is about
- **Progress**: Task checklist showing completed and pending items

- **Two tabs**:
  - **README.md**: Full README content
  - **Session Log**: Extracted Claude Code session log

### Toolbar Buttons

- **Refresh**: Manually scan for sessions and update display
- **All Sessions**: Open the tree view window
- **Extract Log**: Extract session log for current session using atom_session_analyzer
- **Auto-refresh**: Toggle automatic updates (checks every 2 seconds)

### Tree View Window

Opens a hierarchical view of all sessions:

- **Expandable tree structure**: Navigate through directories
- **Session information**: Shows status and last modified time
- **Double-click**: Set a session as the current session to track in main window

### Auto-Refresh

When enabled (default):
- Monitors file changes every 2 seconds
- Automatically updates display when README.md changes
- Shows timestamp of last update in status bar

## Use Cases

### 1. Monitor Active Development

While working on an atom project:
```bash
cd ~/cc_atoms/tools/my_project
atom_gui .
```

Keep the window open to see:
- Status updates as the atom progresses
- Task completions in real-time
- README updates

### 2. Browse All Tools

View all atom tools at once:
```bash
cd ~/cc_atoms/tools
atom_gui .
```

Use the tree view to:
- See which tools are complete vs in progress
- Find the most recently updated session
- Jump between different tool sessions

### 3. Debug Complex Projects

For projects with sub-atoms:
```bash
cd ~/my_complex_project
atom_gui .
```

The tree view shows:
- Parent project and all sub-atoms
- Status of each component
- Which sub-atoms are still active

### 4. Extract Session Logs

To analyze what an atom is doing:
1. Select a session (main window or from tree view)
2. Click "Extract Log"
3. View the session log in the "Session Log" tab

This uses `atom_session_analyzer` to extract detailed session information including all tool calls.

## Session Discovery

The GUI automatically discovers atom sessions by:

1. Scanning for `README.md` files in the directory tree
2. Checking if they contain a `## Status` section (indicates an atom session)
3. Parsing status, overview, and progress information
4. Building a hierarchical view of all sessions

### What Counts as a Session

A directory is recognized as an atom session if it has a `README.md` with:
```markdown
## Status
IN_PROGRESS (or COMPLETE, BLOCKED, NEEDS_DECOMPOSITION)
```

### Session Information Parsed

From the README.md:
- **Status**: From `## Status` section
- **Overview**: From `## Overview` section
- **Progress**: Task list items (- [x] and - [ ])
- **Last Modified**: File modification time

## Tips

### Performance

- Scanning large directory trees may take a few seconds
- Use specific directories when possible to reduce scan time
- Auto-refresh only updates the current session, not the full scan

### Session Logs

- Session logs are extracted to `session_log.md` in the session directory
- They're cached - refresh won't re-extract unless you click "Extract Log"
- Logs can be large (30+ KB) depending on session length

### Multiple Sessions

- The "latest" session is determined by most recent README.md modification
- Tree view shows all sessions with modification times
- Use tree view to track specific sessions rather than just the latest

## Requirements

- Python 3 with tkinter (usually included with Python)
- `atom_session_analyzer` tool (for session log extraction)
- `claude-conversation-extractor` (for session log extraction)

## Troubleshooting

### "No sessions found"

- Make sure you're in a directory with atom sessions (README.md with Status section)
- Try refreshing or rescanning

### "Failed to extract session log"

- Ensure `atom_session_analyzer` is installed and in PATH
- Ensure `claude-conversation-extractor` is installed (`pipx install claude-conversation-extractor`)
- Check that you're in a valid Claude Code project directory

### GUI not responding

- Auto-refresh runs in a background thread - shouldn't block UI
- If frozen, check terminal for error messages
- Try disabling auto-refresh

## Examples

### Example 1: Monitor Current Tool Development

```bash
cd ~/cc_atoms/tools/atom_gui
atom_gui .
```

Shows:
- Status: IN_PROGRESS
- Overview of what atom_gui does
- Progress checklist
- Auto-updates as you work

### Example 2: Browse All Tools

```bash
cd ~/cc_atoms/tools
atom_gui .
```

Main window shows latest tool being worked on.
Click "All Sessions" to see:
```
tools/
  ├── atom_create_tool (COMPLETE)
  ├── atom_gui (IN_PROGRESS)
  └── atom_session_analyzer (COMPLETE)
```

### Example 3: Debug Complex Project

```bash
cd ~/my_project
atom_gui .
```

Tree view might show:
```
my_project/ (IN_PROGRESS)
  ├── authentication/ (COMPLETE)
  ├── database/ (COMPLETE)
  └── api/ (IN_PROGRESS)
```

Double-click `api/` to track its progress specifically.

## Advanced Usage

### Integration with atom_session_analyzer

The GUI integrates with atom_session_analyzer:

```bash
# In main window, "Extract Log" button runs:
atom_session_analyzer
# This creates session_log.md with full session details
```

You can then view the log in the "Session Log" tab.

### Scripting

You can programmatically use the session scanner:

```python
from atom_gui import SessionScanner

scanner = SessionScanner("/path/to/projects")
sessions = scanner.scan()

for path, session in sessions.items():
    print(f"{path}: {session.status}")

latest = scanner.get_latest_session()
print(f"Latest: {latest.path}")
```

## Keyboard Shortcuts

- **F5**: Refresh (when main window is focused)
- **Double-click tree item**: Track that session
- **Close tree view**: Just closes tree view, main window stays open

## See Also

- `atom_session_analyzer` - Extract and analyze session logs
- `atom` - The atom orchestrator
- `atom_create_tool` - Create new atom tools
