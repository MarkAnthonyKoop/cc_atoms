# Save to JSONL Feature

## Overview

The atom_gui now supports saving edited prompts back to the original Claude Code session JSONL files stored in `~/.claude/projects/`.

## How It Works

### 1. File Location

Claude Code stores sessions in: `~/.claude/projects/-path-to-directory/*.jsonl`

The path mangling converts:
- `/home/tony/cc_atoms/tools/atom_gui` → `-home-tony-cc-atoms-tools-atom-gui`
- Underscores (`_`) are replaced with dashes (`-`)
- Forward slashes (`/`) are replaced with dashes (`-`)

### 2. JSONL Format

Each line in the JSONL file is a JSON object representing a conversation turn:

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "The actual prompt text..."
  },
  "uuid": "...",
  "timestamp": "...",
  ...
}
```

### 3. Save Process

When you click "Save Edits":

1. **Locate JSONL File**: `SessionSaver.find_jsonl_file()` finds the most recent `.jsonl` file in the project directory
2. **Parse File**: Read all lines and parse each JSON object
3. **Find Message**: Count through messages of the matching type (user/assistant) until reaching the prompt index
4. **Update Content**: Modify `data["message"]["content"]` with the new text
5. **Write Back**: Save the entire file with the updated line

### 4. Message Counting

Messages are counted separately by type:
- User messages: `{"type": "user", "message": {"role": "user", ...}}`
- Assistant messages: `{"type": "assistant", "message": {"role": "assistant", ...}}`

The prompt index (0-based) corresponds to its position among messages of the same type.

## Usage

1. Open atom_gui in a session directory
2. Click "Extract Log" to get the latest session
3. Navigate the tree to find a prompt (👤 user or 🤖 assistant)
4. Click the prompt to edit it in the "Edit Prompt" tab
5. Make your changes in the editor
6. Click "Save Edits" button
7. Confirm the save operation
8. Optionally extract the updated session log to verify changes

## Warnings

⚠️ **This modifies the original Claude Code session files!**

- Changes are permanent
- Backup files are not created automatically
- Consider using version control for important sessions
- The session log may need to be re-extracted to see changes

## Limitations

### Current Limitations

1. **Simple Content Only**: Only handles string content, not complex content blocks (images, etc.)
2. **No Undo**: Once saved, changes cannot be undone through the GUI
3. **No Backup**: Original content is not backed up automatically
4. **File Locking**: No protection against concurrent edits

### When Save May Fail

- JSONL file not found (session not in `~/.claude/projects/`)
- File permissions issues
- Malformed JSON in the file
- Message index out of range
- Concurrent edits by Claude Code

## Testing

Test the save functionality:

```bash
# 1. Start atom_gui in a session directory
atom_gui

# 2. Extract session log
# Click "Extract Log" button

# 3. Edit a prompt
# Click a prompt in tree, edit it, click "Save Edits"

# 4. Verify the change
# Check the JSONL file directly:
cat ~/.claude/projects/-home-tony-..../...jsonl | grep -A5 "your edited text"

# 5. Re-extract to see updated session log
# Click "Extract Log" again
```

## Error Handling

The save functionality provides detailed error messages:

- **"Could not find JSONL session file"**: Session directory not mapped to `~/.claude/projects/`
- **"Could not find message at index N"**: Message count mismatch (file may have changed)
- **"Error saving: ..."**: File I/O or JSON parsing error

## Future Enhancements

Possible improvements:

- [ ] Automatic backup before save
- [ ] Undo/redo support
- [ ] Handle complex content blocks (images, tool calls)
- [ ] Validate changes before save
- [ ] Show diff of changes
- [ ] Support for batch edits
- [ ] File locking to prevent concurrent edits
- [ ] Export edited sessions

## Technical Details

### Code Structure

- **SessionSaver class**: Handles all JSONL file operations
  - `find_jsonl_file(session_dir)`: Locates the JSONL file
  - `save_prompt_edit(session_dir, prompt_index, new_content, prompt_type)`: Saves changes

### Path Mangling

```python
# Convert session path to Claude's format
session_path_str = str(session_dir.resolve())
mangled_path = session_path_str.replace("/", "-").replace("_", "-")
project_dir = Path.home() / ".claude" / "projects" / mangled_path
```

### Message Matching

```python
if data.get("type") in ["user", "assistant"]:
    role = data.get("message", {}).get("role")
    if role == target_type:
        if message_count == prompt_index:
            # Found the message - update it
            data["message"]["content"] = new_content
```

## See Also

- `atom_gui.py` - Main implementation (lines 70-176: SessionSaver class)
- `ISSUE_REPORT.md` - Session log caching bug fix
- `ENHANCEMENT_SUMMARY.md` - Complete feature list
