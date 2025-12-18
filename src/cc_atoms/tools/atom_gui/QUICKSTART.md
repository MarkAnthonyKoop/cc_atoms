# Atom GUI - Quick Start

## What is it?

A real-time GUI monitor for atom sessions. Shows you what your atoms are doing as they work.

## Install

Already installed! Just run:

```bash
atom_gui
```

## Usage

### Monitor your current project
```bash
cd ~/my-project
atom_gui .
```

### Monitor all atom tools
```bash
cd ~/cc_atoms/tools
atom_gui .
```

### What you'll see

**Main Window:**
- Path to current session
- Status (color-coded)
- Overview and progress
- README.md content
- Session log (after clicking "Extract Log")

**Buttons:**
- **Refresh** - Rescan for sessions
- **All Sessions** - Open tree view of all sessions
- **Extract Log** - Get detailed session log
- **Auto-refresh** - Toggle live updates (on by default)

**Tree View Window:**
- Click "All Sessions" button
- See all sessions in a tree
- Double-click any session to track it

## Tips

- Auto-refresh checks for changes every 2 seconds
- F5 to manually refresh
- Status colors:
  - 🟢 Green = COMPLETE
  - 🔵 Blue = IN_PROGRESS
  - 🔴 Red = BLOCKED
  - 🟠 Orange = NEEDS_DECOMPOSITION

## Requirements

- Python 3 with tkinter (usually included)
- For session log extraction:
  - `atom_session_analyzer` (already in cc_atoms)
  - `claude-conversation-extractor` (install: `pipx install claude-conversation-extractor`)

## See Also

- [USAGE.md](USAGE.md) - Full documentation
- [README.md](README.md) - Technical details
