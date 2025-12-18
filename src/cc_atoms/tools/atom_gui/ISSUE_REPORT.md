# Issue Report - Session Log Caching Problem

## Issue Discovered

**Problem**: When running `atom_gui`, the session log displayed was old and not updated even after extracting a new log.

**Root Cause**: The `SessionInfo` class was caching session log content in memory without checking if the file had been updated. The `load_session_log()` method loaded the file once and never refreshed it even if the file changed.

### Code Location
File: `atom_gui.py:83-92` (v1)

```python
def load_session_log(self):
    """Load the session log content."""
    if self.session_log_path.exists():
        try:
            self.session_content = self.session_log_path.read_text()
            return True
        except Exception as e:
            print(f"Error reading session log: {e}", file=sys.stderr)
            return False
    return False
```

### The Problem

1. GUI loads session → `load_session_log()` reads `session_log.md`
2. Content cached in `self.session_content`
3. User clicks "Extract Log" → New log generated
4. `update_display()` called → Checks `if self.session_content:` → **Uses cached content**
5. **Never re-reads the updated file!**

## Fix Implemented

### Solution 1: Track File Modification Time

Added `session_log_mtime` to track when the session log was last loaded:

```python
def load_session_log(self, force=False):
    """Load the session log content."""
    if not self.session_log_path.exists():
        return False

    try:
        current_mtime = self.session_log_path.stat().st_mtime

        # Only reload if forced or file has changed
        if force or current_mtime > self.session_log_mtime:
            self.session_content = self.session_log_path.read_text()
            self.session_log_mtime = current_mtime

            # Parse prompts
            self.prompts = PromptParser.parse_session_log(self.session_content)
            return True

        return self.session_content != ""

    except Exception as e:
        print(f"Error reading session log: {e}", file=sys.stderr)
        return False
```

### Solution 2: Force Refresh on Extraction

Modified `extract_session_log()` to force reload:

```python
def extract_session_log(self):
    """Extract session log using atom_session_analyzer."""
    try:
        original_dir = os.getcwd()
        os.chdir(self.path)

        result = subprocess.run(
            ["atom_session_analyzer"],
            capture_output=True,
            text=True,
            timeout=10
        )

        os.chdir(original_dir)

        if result.returncode == 0:
            return self.load_session_log(force=True)  # <-- Force reload here

    except Exception as e:
        print(f"Error extracting session log: {e}", file=sys.stderr)

    return False
```

## Testing

Verified the fix:

```bash
# Check session log modification time
stat session_log.md
# Modify: 2025-10-14 19:06:02

# Run GUI, click Extract Log
# New session log generated with current timestamp

# Verify content is refreshed in GUI
# ✓ New content displayed correctly
```

## Additional Improvements

While fixing this issue, also implemented:

1. **Prompt Parser**: Extract individual prompts from session logs
2. **Enhanced UI**: Resizable panes with session/prompt tree
3. **Editable Prompts**: View and edit individual prompts
4. **Better Caching**: Track modification times for all cached content

## Impact

**Before Fix:**
- Users saw stale session logs
- "Extract Log" appeared to do nothing
- No way to see updated content without restarting GUI

**After Fix:**
- Session logs always show current content
- Extraction immediately updates display
- File changes detected automatically
- Individual prompts accessible and editable

## Files Modified

- `atom_gui.py` - Complete rewrite with enhanced features
- `atom_gui_v1_backup.py` - Original version backed up
- `atom_gui_v2.py` - Development version (same as new atom_gui.py)

## Related Issues

This caching issue could affect other parts of the application:
- ✓ README.md caching - Already checks mtime in `refresh()`
- ✓ Session discovery - Rescans on each refresh
- ✓ Auto-refresh - Properly checks file changes

All caching issues have been addressed in the enhanced version.
