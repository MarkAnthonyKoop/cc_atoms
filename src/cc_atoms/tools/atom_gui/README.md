# Atom GUI - Real-time Atom Session Monitor

## Overview

Enhanced GUI application to monitor atom progress in real-time. Features a resizable left pane with session/prompt navigation, editable prompt view, and all original monitoring capabilities. Navigate through sessions and individual prompts, edit them with cut/paste and image support.

## Status
COMPLETE (v2.0 - Modular Architecture)

## Architecture

**Post-refactor modular structure:**

```
tools/atom_gui/
├── atom_gui.py              # Entry point (~35 lines)
├── core/                    # Business logic
│   ├── __init__.py
│   ├── parser.py            # PromptParser - parse session logs
│   ├── history.py           # EditHistory - undo/redo management
│   ├── saver.py             # SessionSaver - save to JSONL
│   └── session.py           # SessionInfo, SessionScanner - discovery
└── gui/                     # UI layer
    ├── __init__.py
    └── main_window.py       # MainWindow - tkinter GUI
```

### Module Responsibilities

| Module | Lines | Purpose |
|--------|-------|---------|
| `atom_gui.py` | ~35 | Entry point, CLI argument handling |
| `core/parser.py` | ~97 | Parse session logs into prompts |
| `core/history.py` | ~82 | Undo/redo with arbitrary depth |
| `core/saver.py` | ~209 | Save edits to JSONL files |
| `core/session.py` | ~175 | Session discovery and scanning |
| `gui/main_window.py` | ~745 | Main tkinter application |

## Usage

```bash
# Monitor current directory
atom_gui

# Monitor specific directory
atom_gui /path/to/project

# Monitor all tools
cd ~/cc_atoms/tools
atom_gui .
```

See [USAGE.md](USAGE.md) for detailed documentation.

## Features

### 1. Resizable Paned Layout
- **Left pane**: Session and prompt tree (📁 sessions, 👤 user, 🤖 assistant)
- **Right pane**: Tabbed content display
- Drag divider to resize - supports full screen expansion
- Pane sizes preserved during session

### 2. Session & Prompt Navigation
- Tree shows all sessions with descriptions (truncated to 25 chars)
- Click session to view details in right pane
- Expands to show individual prompts from session log
- Click any prompt to view/edit it
- Icons distinguish user prompts (👤) from assistant responses (🤖)

### 3. Four Content Tabs
- **Overview**: Status, overview text, progress checklist
- **README.md**: Full README content (read-only)
- **Session Log**: Complete session log (read-only)
- **Edit Prompt**: Editable view of selected prompt

### 4. Prompt Editor
- Edit user prompts and assistant responses
- Cut/Copy/Paste buttons for text manipulation
- Insert Image button (adds image references)
- Shows prompt type with color coding (blue=user, green=assistant)
- Undo/Redo support
- Save button - **Saves to JSONL files** in `~/.claude/projects/`

### 5. Session Management & History
- Auto-refresh: Monitors file changes every 2 seconds
- Extract Log: Gets latest session from Claude Code
- Proper caching: Checks file modification times
- **Undo/Redo**: Arbitrary depth history for all edits
- History indicator: Shows position (e.g., "History: 3/5")
- Color-coded status: COMPLETE=green, IN_PROGRESS=blue, BLOCKED=red
- F5 keyboard shortcut for manual refresh

### 6. Integration & Discovery
- Uses atom_session_analyzer for session extraction
- Parses session logs to extract individual prompts
- Discovers sessions via README.md scanning
- Recursive directory scanning

## Files

### Core Application
- `atom_gui.py` - Entry point
- `core/` - Business logic modules
- `gui/` - UI layer

### Documentation
- `README.md` - This file
- `USAGE.md` - Detailed usage documentation
- `QUICKSTART.md` - Quick start guide
- `SAVE_FEATURE.md` - JSONL save functionality details
- `UNDO_REDO.md` - Comprehensive undo/redo guide
- `TREE_VIEW_GUIDE.md` - Tree navigation guide
- `HIERARCHICAL_TREE_IMPLEMENTATION.md` - Implementation details

### Legacy/Archive
- `atom_gui_original.py` - Pre-refactor monolithic version (for reference)

## Testing

```bash
# Run tests
python3 tests/test_session_scanner.py

# Test on specific directory
cd ~/cc_atoms/tools
python3 atom_gui/tests/test_session_scanner.py scan_cwd
```

## Progress
- [x] Created project structure
- [x] Implement session discovery
- [x] Build main monitoring window
- [x] Build tree view window
- [x] Add auto-refresh
- [x] Test with real sessions
- [x] Create launcher
- [x] Add comprehensive documentation
- [x] Enhanced UI with resizable panes
- [x] Parse session logs into individual prompts
- [x] Editable prompt view with cut/paste
- [x] Image insertion support
- [x] Fixed session log caching issue
- [x] **Refactored to modular architecture** (v2.0)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-11 | Modular architecture: split 1,311-line monolith into core/ and gui/ |
| 1.0 | 2025-10 | Initial release with full feature set |

## Decisions
- Using tkinter for cross-platform compatibility and no extra dependencies
- Leveraging atom_session_analyzer to extract session details
- Using file modification times to track "latest" session in subprojects
- **Modular design**: Separated business logic (core/) from UI (gui/) for maintainability
