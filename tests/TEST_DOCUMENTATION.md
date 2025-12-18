# cc_atoms Test Documentation

## Quick Start

```bash
# Run all tests (33 total)
/opt/homebrew/bin/python3 tests/run_all_tests.py

# Run individual test suites
/opt/homebrew/bin/python3 tests/test_atom_core.py    # 22 tests
/opt/homebrew/bin/python3 tests/test_atom.py         # 5 tests
/opt/homebrew/bin/python3 tests/test_gui_control.py  # 10 tests
/opt/homebrew/bin/python3 tests/test_atom_gui.py     # 15 tests
/opt/homebrew/bin/python3 tests/test_integration.py  # 8 tests
```

---

## Test Suite Overview

| Suite | File | Tests | Purpose |
|-------|------|-------|---------|
| Comprehensive | `run_all_tests.py` | 33 | Full verification of package |
| Core Library | `test_atom_core.py` | 22 | atom_core components |
| CLI | `test_atom.py` | 5 | Command-line interface |
| GUI Control | `test_gui_control.py` | 10 | gui_control tool |
| Atom GUI | `test_atom_gui.py` | 15 | atom_gui tool (core modules) |
| Integration | `test_integration.py` | 8 | End-to-end workflows |

---

## run_all_tests.py (33 tests)

Comprehensive verification script that checks the entire package.

### 1. Package Structure (13 tests)

Verifies all required files exist in `src/cc_atoms/`.

| File | Purpose |
|------|---------|
| `__init__.py` | Package root, exports main classes |
| `cli.py` | CLI entry point (atom command) |
| `config.py` | Central configuration |
| `atom_core/__init__.py` | Core library exports |
| `atom_core/runtime.py` | AtomRuntime orchestration engine |
| `atom_core/retry.py` | RetryManager for error handling |
| `atom_core/context.py` | IterationHistory tracking |
| `atom_core/prompt_loader.py` | PromptLoader with search paths |
| `atom_core/claude_runner.py` | ClaudeRunner subprocess wrapper |
| `tools/__init__.py` | Tools package |
| `tools/gui_control/__init__.py` | gui_control exports |
| `tools/gui_control/gui_control.py` | GUI automation tool |
| `prompts/ATOM.md` | Base system prompt |

### 2. pyproject.toml Validity (5 tests)

| Check | What it verifies |
|-------|------------------|
| File exists | pyproject.toml present in project root |
| Valid TOML | Parses without syntax errors |
| Build system | `[build-system]` section with setuptools |
| Project metadata | `[project]` section with name, version, etc. |
| CLI entry points | `[project.scripts]` defines atom, atom-gui, etc. |

### 3. Import Tests (8 tests)

Runs `python3 -c "from cc_atoms import X"` for each component.

| Import Statement | Component |
|------------------|-----------|
| `from cc_atoms import AtomRuntime` | Main orchestration class |
| `from cc_atoms import PromptLoader` | Prompt loading with search paths |
| `from cc_atoms import RetryManager` | Retry logic with backoff |
| `from cc_atoms import IterationHistory` | Iteration tracking |
| `from cc_atoms import ClaudeRunner` | Claude subprocess execution |
| `from cc_atoms import cli` | CLI module |
| `from cc_atoms import config` | Configuration module |
| `from cc_atoms.tools.gui_control import control_gui` | GUI control function |

### 4. CLI Entry Points (1 test)

| Test | What it does |
|------|--------------|
| `atom --help` | Runs CLI, verifies exit code 0 and help output |

### 5. Unit Test Suites (2 tests)

Executes the detailed test files and checks they pass.

| Test File | Result |
|-----------|--------|
| `test_atom_core.py` | All 22 tests pass |
| `test_atom.py` | All 5 tests pass |

### 6. pip Installation (1 test)

| Test | What it does |
|------|--------------|
| `pip show cc-atoms` | Verifies package is installed |

---

## test_atom_core.py (22 tests)

Detailed unit tests for the core library components.

### PromptLoader Tests (4 tests)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_load_default_atom` | `loader.load()` | Returns contents of ATOM.md |
| `test_load_atom_prefix` | `loader.load("atom_test")` | Returns ATOM.md + TEST.md combined |
| `test_load_no_prefix` | `loader.load("mytool")` | Returns MYTOOL.md only |
| `test_search_path_priority` | Local and global ATOM.md exist | Local version returned (priority) |

**Prompt Loading Rules:**
- `toolname=None` → ATOM.md
- `toolname="atom_foo"` → ATOM.md + FOO.md (combined with `\n\n`)
- `toolname="foo"` → FOO.md only

### RetryManager Tests (4 tests)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_no_retry_on_success` | returncode=0 | `should_retry=False, wait=0` |
| `test_retry_on_session_limit` | "Session limit reached. resets 3pm" | `should_retry=True, wait>0` |
| `test_retry_on_network_error` | "Network timeout", attempt 1 vs 2 | Exponential backoff (5s → 10s) |
| `test_custom_callback` | Custom callback function | Callback receives message and seconds |

**Retry Logic:**
- Success (returncode=0): No retry
- Session limit: Parse reset time, wait until then + buffer
- Network errors: Exponential backoff (5, 10, 20... max 300s)
- Other errors: Exponential backoff (10, 20, 40... max 600s)

### IterationHistory Tests (3 tests)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_add_and_retrieve_iterations` | Add 2 iterations | `get_all_iterations()` returns list of 2 |
| `test_iteration_includes_timestamp` | Add 1 iteration | Entry has `timestamp` field > 0 |
| `test_empty_history` | New IterationHistory | `get_all_iterations()` returns `[]` |

### ClaudeRunner Tests (2 tests)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_builds_correct_command` | `run(prompt, dir, use_context=True)` | Command contains `claude -c -p --dangerously-skip-permissions` |
| `test_raises_on_missing_directory` | Non-existent directory | Raises `FileNotFoundError` |

**Command Structure:**
```
claude -c -p "prompt" --dangerously-skip-permissions
```
- `-c`: Continue conversation (context accumulation)
- `-p`: Provide prompt
- `--dangerously-skip-permissions`: Skip permission prompts

### AtomRuntime Tests (9 tests)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_create_ephemeral` | `AtomRuntime.create_ephemeral(prompt, max_iterations=5)` | Temp dir exists, cleanup=True, verbose=False |
| `test_conversation_dir_parameter` | `AtomRuntime(conversation_dir=path)` | `runtime.conversation_dir == path` |
| `test_smart_verbose_detection` | `verbose=True` or `verbose=False` | Explicit value honored |
| `test_creates_user_prompt_file` | `runtime.run("Test task")` | USER_PROMPT.md created with "Test task" |
| `test_cleanup_removes_user_prompt` | `cleanup=True`, then run | USER_PROMPT.md deleted after completion |
| `test_result_dict_structure` | `runtime.run()` returns | Dict has: success, iterations, output, duration |
| `test_error_handling` | Claude not found | `success=False, reason="claude_not_found"` |
| `test_max_iterations_reached` | max_iterations=2, never completes | `success=False, reason="max_iterations", iterations=2` |

**Result Dictionary Structure:**
```python
{
    "success": bool,        # True if EXIT_LOOP_NOW found
    "iterations": int,      # Number of iterations executed
    "output": str,          # Final stdout from Claude
    "duration": float,      # Seconds elapsed
    "context": List[dict],  # Full iteration history
    "reason": str,          # If failed: "max_iterations", "error", etc.
    "error": Optional[str]  # Error message if exception occurred
}
```

---

## test_atom.py (5 tests)

Unit tests for the CLI interface.

| Test | What it verifies |
|------|------------------|
| `test_helper_functions_exist` | `cli` module has: `parse_arguments`, `handle_command_line_prompt`, `validate_user_prompt`, `setup_atoms_environment` |
| `test_handle_command_line_prompt` | `["Hello", "World"]` → creates USER_PROMPT.md containing "Hello World" |
| `test_validate_user_prompt` | Missing USER_PROMPT.md → `sys.exit(1)` |
| `test_setup_atoms_environment` | Creates `bin/`, `tools/`, `prompts/` directories |
| `test_atom_uses_atom_core` | Can import `AtomRuntime`, `PromptLoader` from `cc_atoms.atom_core` |

---

## test_gui_control.py (10 tests)

Tests for the gui_control GUI automation tool.

### Module Structure Tests (4 tests)

| Test | What it verifies |
|------|------------------|
| `test_module_imports` | control_gui and main are importable |
| `test_system_prompt_exists` | SYSTEM_PROMPT is defined (10,747 chars) |
| `test_system_prompt_has_key_sections` | Contains: GUI, macOS, accessibility, click, screenshot |
| `test_system_prompt_has_task_placeholder` | Has `{user_task}` placeholder for injection |

### Function Tests (5 tests)

| Test | What it verifies |
|------|------------------|
| `test_function_signature` | Has: task, working_dir, max_iterations, verbose params |
| `test_returns_dict_on_success` | Returns dict with success, iterations, output, duration |
| `test_passes_task_to_prompt` | Task string is injected into system prompt |
| `test_respects_max_iterations` | max_iterations param is passed to runtime |
| `test_uses_ephemeral_runtime` | Uses create_ephemeral (not regular constructor) |

### CLI Tests (1 test)

| Test | What it verifies |
|------|------------------|
| `test_cli_help_works` | `--help` exits with code 0 and shows usage |

---

## test_atom_gui.py (15 tests)

Tests for the atom_gui session monitor. Core modules tested without tkinter.

### Import Tests (6 tests)

| Test | What it verifies |
|------|------------------|
| `test_core_parser_imports` | PromptParser importable from core.parser |
| `test_core_history_imports` | EditHistory importable from core.history |
| `test_core_saver_imports` | SessionSaver importable from core.saver |
| `test_core_session_imports` | SessionInfo, SessionScanner importable |
| `test_gui_main_window_imports` | MainWindow importable (skipped if no tkinter) |
| `test_main_module_imports` | main() importable (skipped if no tkinter) |

### PromptParser Tests (3 tests)

| Test | What it verifies |
|------|------------------|
| `test_parser_instantiation` | PromptParser() creates instance |
| `test_parser_parse_empty` | Empty string returns empty list |
| `test_parser_parse_session_log` | Parses user/assistant prompts from markdown |

### EditHistory Tests (4 tests)

| Test | What it verifies |
|------|------------------|
| `test_history_instantiation` | EditHistory() creates instance |
| `test_history_add_and_undo` | add_edit/get_undo_action work correctly |
| `test_history_redo` | get_redo_action returns new content |
| `test_history_empty` | Empty history can't undo/redo |

### SessionScanner Tests (3 tests)

| Test | What it verifies |
|------|------------------|
| `test_scanner_instantiation` | SessionScanner(path) creates instance |
| `test_scanner_finds_sessions` | Finds dirs with README.md containing `## Status` |
| `test_scanner_empty_directory` | Returns empty dict for empty dirs |

---

## test_integration.py (8 tests)

End-to-end integration tests with mocked Claude subprocess.

### Full Workflow Tests (4 tests)

| Test | What it verifies |
|------|------------------|
| `test_runtime_creates_and_uses_user_prompt` | USER_PROMPT.md created, Claude called |
| `test_prompt_loader_integration_with_runtime` | PromptLoader output works with AtomRuntime |
| `test_iteration_loop_stops_on_exit_signal` | Loop stops when EXIT_LOOP_NOW found |
| `test_iteration_loop_stops_at_max` | Loop stops at max_iterations |

### CLI Integration Tests (1 test)

| Test | What it verifies |
|------|------------------|
| `test_cli_creates_user_prompt_and_runs` | CLI creates USER_PROMPT.md from args |

### Retry Integration Tests (1 test)

| Test | What it verifies |
|------|------------------|
| `test_retry_on_transient_error` | Transient errors trigger retry |

### Cleanup Behavior Tests (2 tests)

| Test | What it verifies |
|------|------------------|
| `test_cleanup_true_removes_files` | cleanup=True deletes USER_PROMPT.md |
| `test_cleanup_false_keeps_files` | cleanup=False keeps USER_PROMPT.md |

---

## Test Results Summary

Last run: All 33 tests passing

| Category | Passed | Total | Status |
|----------|--------|-------|--------|
| Package structure | 13 | 13 | PASS |
| pyproject.toml | 5 | 5 | PASS |
| Imports | 8 | 8 | PASS |
| CLI entry points | 1 | 1 | PASS |
| Unit tests | 5 | 5 | PASS |
| pip installation | 1 | 1 | PASS |
| **Total** | **33** | **33** | **PASS** |

---

## Adding New Tests

### To test_atom_core.py:

```python
class TestMyComponent:
    def test_something(self):
        # Arrange
        component = MyComponent()

        # Act
        result = component.do_something()

        # Assert
        assert result == expected, "Description of failure"
        print("✓ TestMyComponent: test_something passed")
```

Then add to `main()`:
```python
print("Testing MyComponent...")
test_my = TestMyComponent()
test_my.test_something()
```

### To run_all_tests.py:

Add a new test function:
```python
def test_my_feature():
    """Description of what this tests"""
    print_header("Testing My Feature")

    # Your tests here
    passed = 0
    total = 0

    # Example check
    total += 1
    if some_condition:
        print_pass("Feature works")
        passed += 1
    else:
        print_fail("Feature broken")

    return passed, total
```

Then add to `test_functions` list in `main()`.

---

## Troubleshooting

### Import errors
```bash
# Check if cc_atoms is installed
pip show cc-atoms

# Reinstall
pip install -e /path/to/cc --break-system-packages
```

### Test failures
```bash
# Run with verbose output
python3 -c "from cc_atoms import AtomRuntime; print(AtomRuntime)"

# Check specific test
python3 tests/test_atom_core.py 2>&1 | head -50
```

### Missing prompts
```bash
# Check prompts directory
ls -la src/cc_atoms/prompts/
```
