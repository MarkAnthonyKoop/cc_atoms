# Undo/Redo Feature

## Overview

The atom_gui now includes a comprehensive undo/redo system with **arbitrary depth** for all JSONL edits. You can undo and redo any number of changes, navigating through the complete edit history.

## Features

### Arbitrary Depth History

- **Unlimited undo levels**: The history is only limited by available memory
- **Full edit tracking**: Every save operation is recorded
- **Non-linear editing**: Edit different prompts and undo them independently
- **Persistent state**: History is maintained throughout the session

### History Navigation

- **Undo**: Revert to the previous version of the edited prompt
- **Redo**: Reapply a change that was undone
- **History position**: See your current position in the history (e.g., "History: 3/5")
- **Smart button states**: Undo/Redo buttons are only enabled when applicable

## User Interface

### Toolbar Buttons

The toolbar includes:
- **Save Edits**: Save current changes (adds to history)
- **Undo**: Revert the last edit (grayed out if no history)
- **Redo**: Reapply an undone edit (grayed out if at end of history)
- **History Label**: Shows "History: X/Y" where X is current position, Y is total edits

### Button States

- **Undo button**: Enabled when there are edits to undo (position > 0)
- **Redo button**: Enabled when you've undone edits (position < total)
- Both buttons are grayed out when not applicable

## How It Works

### 1. Recording History

When you click "Save Edits":

1. **Get original content** from JSONL file (before edit)
2. **Save new content** to JSONL file
3. **Record in history**:
   - JSONL file path
   - Prompt index and type
   - Old content (for undo)
   - New content (for redo)
   - Timestamp
4. **Update button states**

### 2. Undo Operation

When you click "Undo":

1. **Get undo action** from history (retrieves old content)
2. **Apply to JSONL** file directly
3. **Move back** in history (position decreases)
4. **Update buttons** (Redo becomes enabled)
5. **Optionally re-extract** session log to see changes

### 3. Redo Operation

When you click "Redo":

1. **Get redo action** from history (retrieves new content)
2. **Apply to JSONL** file directly
3. **Move forward** in history (position increases)
4. **Update buttons** (may disable Redo if at end)
5. **Optionally re-extract** session log to see changes

### 4. Branching History

If you undo several changes, then make a new edit:
- **Future history is discarded** (standard undo/redo behavior)
- **New edit starts a new branch** from current position
- Cannot redo to the discarded future

## Data Structure

### EditHistory Class

```python
class EditHistory:
    def __init__(self):
        self.history = []          # List of edit actions
        self.current_position = -1  # Current position in history
```

### History Entry

Each entry contains:
```python
{
    'jsonl_path': '/path/to/file.jsonl',      # Full path to JSONL file
    'prompt_index': 0,                         # Which prompt (0-based)
    'prompt_type': 'user',                     # 'user' or 'assistant'
    'old_content': 'Original text...',         # For undo
    'new_content': 'Edited text...',           # For redo
    'timestamp': 1234567890.123                # When edit was made
}
```

## Usage Examples

### Example 1: Simple Undo/Redo

```
1. Edit prompt "Hello" → "Hello World"
   Save → History: 1/1, Undo enabled

2. Click Undo
   → Restores "Hello"
   → History: 0/1, Redo enabled, Undo disabled

3. Click Redo
   → Restores "Hello World"
   → History: 1/1, Redo disabled, Undo enabled
```

### Example 2: Multiple Edits

```
1. Edit prompt A: "foo" → "bar"
   Save → History: 1/1

2. Edit prompt B: "hello" → "world"
   Save → History: 2/2

3. Edit prompt A: "bar" → "baz"
   Save → History: 3/3

4. Click Undo (reverts prompt A to "bar")
   → History: 2/3, Redo enabled

5. Click Undo (reverts prompt B to "hello")
   → History: 1/3, Redo enabled

6. Click Undo (reverts prompt A to "foo")
   → History: 0/3, Redo enabled, Undo disabled
```

### Example 3: Branching History

```
1. Edit prompt: "A" → "B"
   Save → History: 1/1

2. Edit prompt: "B" → "C"
   Save → History: 2/2

3. Click Undo (back to "B")
   → History: 1/2

4. Edit prompt: "B" → "D" (different from "C")
   Save → History: 2/2 (previous "C" is lost)
   → Can no longer redo to "C"
```

## Implementation Details

### History Navigation

```python
# Check if operations are available
can_undo = history.current_position >= 0
can_redo = history.current_position < len(history.history) - 1

# Get action to perform
undo_action = history.get_undo_action()  # Returns old_content
redo_action = history.get_redo_action()  # Returns new_content

# Update position after operation
history.move_back()     # After undo
history.move_forward()  # After redo
```

### Adding to History

```python
# When saving
self.edit_history.add_edit(
    jsonl_file,          # Path to JSONL file
    prompt_index,        # Which prompt
    prompt_type,         # 'user' or 'assistant'
    original_content,    # Content before edit
    edited_content       # Content after edit
)

# Automatically handles:
# - Truncating future history if not at end
# - Updating current position
# - Adding timestamp
```

## Keyboard Shortcuts

Currently, undo/redo is only available via toolbar buttons. Future enhancements could add:
- Ctrl+Z for Undo
- Ctrl+Y or Ctrl+Shift+Z for Redo

## Limitations

### Current Limitations

1. **Session scope**: History is lost when closing the GUI
2. **Single session**: Each GUI instance has its own history
3. **No persistence**: History is not saved to disk
4. **No visual diff**: Changes aren't shown before applying undo/redo

### Technical Limitations

1. **Memory usage**: Large histories consume memory (typically not an issue)
2. **No file watching**: Changes made outside GUI aren't detected
3. **No merge conflicts**: Concurrent edits by Claude Code could cause issues

## Best Practices

### When to Use Undo

- Made a mistake in an edit
- Want to compare versions
- Testing different phrasings
- Reverting experimental changes

### When to Use Redo

- Changed your mind about an undo
- Comparing before/after versions
- Restoring changes you undid

### Tips

1. **Save frequently**: Each save creates an undo point
2. **Test before committing**: Use undo if unsure about changes
3. **Branch deliberately**: Know that new edits discard redo history
4. **Re-extract after undo/redo**: See changes in session log

## Future Enhancements

Possible improvements:

- [ ] Persistent history (save to file)
- [ ] History view window (browse all edits)
- [ ] Visual diff before undo/redo
- [ ] Keyboard shortcuts (Ctrl+Z, Ctrl+Y)
- [ ] Undo/redo from context menu
- [ ] Selective undo (skip to specific point)
- [ ] Export history as patch file
- [ ] Undo for multiple prompts at once
- [ ] History search and filter

## Technical Details

### Code Location

- **EditHistory class**: `atom_gui.py:70-146`
- **SessionSaver.get_original_content()**: `atom_gui.py:186-224`
- **SessionSaver.apply_undo_redo()**: `atom_gui.py:286-335`
- **MainWindow.undo_edit()**: `atom_gui.py:1050-1082`
- **MainWindow.redo_edit()**: `atom_gui.py:1084-1116`
- **MainWindow.update_history_buttons()**: `atom_gui.py:816-835`

### Memory Usage

Typical memory per history entry:
- Metadata: ~200 bytes
- Content: Variable (typically 1-10 KB per prompt)
- 100 edits ≈ 100-1000 KB (negligible)

## See Also

- `SAVE_FEATURE.md` - JSONL save functionality
- `ISSUE_REPORT.md` - Session log caching fix
- `ENHANCEMENT_SUMMARY.md` - All features
