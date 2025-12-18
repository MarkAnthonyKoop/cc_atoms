# Next Test Steps - Manual Validation Guide

This document provides step-by-step instructions for manually validating cc_atoms functionality that cannot be fully automated.

---

## Quick Automated Test

Before manual testing, run the automated suite:

```bash
/opt/homebrew/bin/python3 tests/run_all_tests.py
```

**Expected:** All 33 tests pass.

---

## Manual Test 1: Live Atom Session

**Purpose:** Verify the full atom workflow with actual Claude Code.

### Steps:

1. **Create a test directory:**
   ```bash
   mkdir /tmp/atom_test
   cd /tmp/atom_test
   ```

2. **Run atom with a simple task:**
   ```bash
   atom "Create a file called hello.txt containing 'Hello World'"
   ```

3. **Observe the output:**
   - Should see iteration messages
   - Should complete within a few iterations
   - Should show `EXIT_LOOP_NOW` or similar completion

4. **Validate results:**
   ```bash
   cat hello.txt
   # Should contain: Hello World

   cat USER_PROMPT.md
   # Should contain your prompt
   ```

### Expected Behavior:
- Claude executes and creates the file
- Session completes (doesn't hit max iterations)
- Files are created as expected

### Troubleshooting:
- If "claude: command not found" → Claude Code not installed
- If hangs → Check network, may need retry
- If max iterations → Task may be too complex

---

## Manual Test 2: atom-gui

**Purpose:** Verify the GUI session monitor works.

### Prerequisites:
- tkinter must be available
- Install with: `brew install python-tk@3.14` (if needed)

### Steps:

1. **Create a test session:**
   ```bash
   mkdir /tmp/gui_test
   cd /tmp/gui_test
   cat > README.md << 'EOF'
   # Test Session
   ## Status
   IN_PROGRESS
   ## Overview
   This is a test session for atom_gui.
   ## Progress
   - [x] Created README
   - [ ] Testing GUI
   EOF
   ```

2. **Launch atom-gui:**
   ```bash
   atom-gui /tmp/gui_test
   ```

3. **Verify in GUI:**
   - [ ] Window opens without errors
   - [ ] Left pane shows session tree
   - [ ] Session "." appears with status indicator
   - [ ] Clicking session shows README content
   - [ ] Status shows "IN_PROGRESS" (should be blue)

4. **Test auto-refresh:**
   - Edit README.md in another terminal
   - Wait 2-3 seconds
   - GUI should update automatically

### Expected Behavior:
- GUI launches and displays session info
- Tree navigation works
- Auto-refresh detects file changes

### Troubleshooting:
- If "No module named '_tkinter'" → Install python-tk
- If window doesn't appear → Check DISPLAY/X11 forwarding

---

## Manual Test 3: gui-control (macOS only)

**Purpose:** Verify GUI automation works with real applications.

### Prerequisites:
- macOS with Accessibility permissions for Terminal
- Safari or another GUI app open

### Steps:

1. **Open Safari with a simple page:**
   ```bash
   open -a Safari https://example.com
   ```

2. **Run gui-control:**
   ```bash
   gui-control "Take a screenshot and describe what you see" --verbose
   ```

3. **Observe:**
   - Should take screenshot
   - Should describe the Safari window
   - Should complete with EXIT_LOOP_NOW

4. **Test clicking (careful!):**
   ```bash
   gui-control "Find the Safari window and describe its title bar"
   ```

### Expected Behavior:
- Screenshots are captured
- GUI elements are identified
- Natural language commands are interpreted

### Troubleshooting:
- If "accessibility not enabled" → System Preferences > Privacy > Accessibility
- If can't find window → Window may be minimized/hidden

---

## Manual Test 4: Prompt Loading

**Purpose:** Verify prompt composition works correctly.

### Steps:

1. **Check base prompt loads:**
   ```bash
   /opt/homebrew/bin/python3 -c "
   from cc_atoms import PromptLoader
   loader = PromptLoader()
   prompt = loader.load()
   print(f'Base prompt length: {len(prompt)} chars')
   print(f'First 100 chars: {prompt[:100]}...')
   "
   ```

2. **Check project-local prompts:**
   ```bash
   mkdir -p /tmp/prompt_test/.atom/prompts
   echo "# Custom Prompt\nYou are a custom tool." > /tmp/prompt_test/.atom/prompts/CUSTOM.md
   cd /tmp/prompt_test

   /opt/homebrew/bin/python3 -c "
   from cc_atoms import PromptLoader
   loader = PromptLoader()
   prompt = loader.load('custom')
   print(prompt)
   "
   ```

### Expected Behavior:
- Base prompt (ATOM.md) loads correctly
- Project-local prompts override global
- `atom_X` prefix combines ATOM.md + X.md

---

## Manual Test 5: Retry Behavior (requires patience)

**Purpose:** Verify retry logic handles real errors.

### Option A: Network Simulation (if possible)
1. Disconnect network temporarily
2. Run `atom "test"`
3. Reconnect network
4. Observe retry with backoff

### Option B: Observe Session Limits
1. Run many atom sessions quickly
2. If you hit session limit, observe retry behavior
3. Should wait and retry automatically

### Expected Behavior:
- Network errors trigger exponential backoff
- Session limits trigger wait until reset
- Transient errors don't crash the session

---

## Manual Test 6: Embedded Atom (for developers)

**Purpose:** Verify atom_core can be embedded in custom tools.

### Steps:

```python
#!/usr/bin/env python3
from cc_atoms import AtomRuntime

# Create ephemeral runtime
runtime = AtomRuntime.create_ephemeral(
    system_prompt="You are a helpful assistant. Say 'DONE' and EXIT_LOOP_NOW when finished.",
    max_iterations=3,
    verbose=True
)

# Run a simple task
result = runtime.run("Say hello and then say DONE")

print(f"\nResult: {result}")
print(f"Success: {result['success']}")
print(f"Iterations: {result['iterations']}")
```

### Expected Behavior:
- Runtime creates temp directory
- Executes Claude with your prompt
- Returns structured result dict
- Temp files cleaned up

---

## Test Checklist Summary

| Test | Type | Status |
|------|------|--------|
| Automated tests (33) | Automated | Run `run_all_tests.py` |
| Live atom session | Manual | Create file, verify output |
| atom-gui launch | Manual | GUI displays session info |
| gui-control screenshot | Manual | Captures and describes screen |
| Prompt loading | Manual | Verify composition rules |
| Retry behavior | Manual | Observe network/limit handling |
| Embedded atom | Manual | Test AtomRuntime API |

---

## Validation Criteria

### Pass Criteria:
- All automated tests pass (33/33)
- Live atom session completes task
- GUI launches and displays correctly
- Prompts load and compose correctly

### Acceptable Limitations:
- gui-control may not work without macOS Accessibility
- atom-gui may not work without tkinter
- Retry tests require inducing errors

### Failure Indicators:
- Automated tests fail
- Claude subprocess errors
- GUI crashes on launch
- Prompts don't load

---

## After Manual Testing

If all tests pass, the package is ready for:
1. Local use (`pip install -e .`)
2. Distribution (build wheel)
3. Publishing to PyPI (if desired)

Report any issues to the project repository.
