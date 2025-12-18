# cc_atoms Refactor Specification
## Making Atoms Embeddable

**Version:** 1.0
**Date:** 2025-11-22
**Purpose:** Enable atom orchestration to be embedded in any project
**Status:** Awaiting Review from cc_atoms conversation

---

## Executive Summary

We want to refactor cc_atoms to extract its core orchestration logic into an **embeddable library** (`atom_core`), while maintaining 100% backward compatibility with existing atom.py CLI.

**Key Changes:**
1. Extract reusable components into `atom_core/` package
2. Add tool/prompt search paths for project-local tools
3. Refactor `atom.py` to use `atom_core` (no behavior change)
4. Create example tool (`gui_control`) that uses embedded atom

**Benefits:**
- Tools can use atom iteration/retry logic internally
- Projects can embed atom power without exposing complexity
- Core logic is testable and reusable
- Updates to `atom_core` benefit all users automatically

---

## Motivation

### Current Limitation
cc_atoms is **only** usable as a CLI tool:
```bash
cd my-project
atom "Do task"
```

Users must:
- Know about cc_atoms
- Set up USER_PROMPT.md
- Run in correct directory
- See all iteration output

### Desired Capability
Tools should be able to **embed** atom orchestration:
```bash
# User runs simple command
gui_control "Click submit in Safari"

# Behind the scenes:
# - Tool creates embedded atom session
# - Atom iterates/retries until task solved
# - Returns result to user
# User never sees the complexity!
```

### Use Case: gui_control Tool
We're building a GUI automation tool that uses the `mac_gui_control` library. The tool should:
1. Try accessibility API first
2. Fall back to vision if that fails
3. Try different confidence levels
4. Retry on errors
5. Iterate until solved or max attempts

This is **exactly what atom orchestration does**, but we can't reuse it because it's locked in the CLI.

---

## Proposed Architecture

### Current Structure
```
~/cc_atoms/
├── atom.py              # CLI orchestrator (243 lines, does everything)
├── config.py
├── bin/
├── tools/
└── prompts/
```

### Proposed Structure
```
~/cc_atoms/
├── atom.py              # CLI interface (REFACTORED to use atom_core)
├── atom_core/           # NEW - Reusable components
│   ├── __init__.py
│   ├── runtime.py       # AtomRuntime class
│   ├── retry.py         # RetryManager (extracted from atom.py)
│   ├── context.py       # ContextAccumulator (new)
│   ├── prompt_loader.py # PromptLoader (extracted from atom.py)
│   └── claude_runner.py # ClaudeRunner (extracted from atom.py)
├── config.py            # UPDATED - add search paths
├── bin/
├── tools/
│   └── gui_control/     # NEW - Example embedded usage
└── prompts/
```

**Key Principle:** Extract logic from `atom.py` into classes, then refactor `atom.py` to use them.

---

## API Design

### atom_core/runtime.py

```python
"""Core atom orchestration engine - embeddable in any project"""
from pathlib import Path
from typing import Optional, Dict, Any

class AtomRuntime:
    """
    Embeddable atom orchestration.

    Provides iteration, retry, context accumulation without CLI overhead.
    """

    def __init__(
        self,
        system_prompt: str,
        max_iterations: int = 25,
        working_dir: Optional[Path] = None,
        exit_signal: str = "EXIT_LOOP_NOW",
        verbose: bool = True
    ):
        """
        Args:
            system_prompt: System prompt for Claude (can include {max_iterations})
            max_iterations: Maximum iterations before giving up
            working_dir: Directory to run claude -c in (determines conversation)
            exit_signal: String that signals task completion
            verbose: Print iteration progress
        """
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.working_dir = working_dir or Path.cwd()
        self.exit_signal = exit_signal
        self.verbose = verbose

        from .retry import RetryManager
        from .context import ContextAccumulator

        self.retry_manager = RetryManager()
        self.context = ContextAccumulator()

    def run(self, user_prompt: str) -> Dict[str, Any]:
        """
        Run atom iterations until complete or max iterations.

        Args:
            user_prompt: User's task description (written to USER_PROMPT.md)

        Returns:
            {
                "success": bool,           # True if EXIT_LOOP_NOW found
                "iterations": int,         # Number of iterations used
                "output": str,            # Final stdout from Claude
                "context": List[dict],    # Full iteration history
                "reason": str             # If failed: "max_iterations", "error", etc.
            }
        """
        # Setup
        self._create_user_prompt(user_prompt)

        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            if self.verbose:
                print(f"{'='*60}\nIteration {iteration}/{self.max_iterations}\n{'='*60}\n")

            # Run iteration with retry
            result = self._run_iteration_with_retry(iteration)

            # Check completion
            if self._is_complete(result):
                return {
                    "success": True,
                    "iterations": iteration,
                    "output": result["stdout"],
                    "context": self.context.get_all()
                }

            # Accumulate context (for inspection, not for Claude - that's handled by -c)
            self.context.add(iteration, result)

        # Max iterations reached
        return {
            "success": False,
            "reason": "max_iterations",
            "iterations": self.max_iterations,
            "output": result["stdout"],
            "context": self.context.get_all()
        }

    def _run_iteration_with_retry(self, iteration: int) -> Dict[str, Any]:
        """Run single iteration with infinite retry on errors"""
        from .claude_runner import ClaudeRunner

        runner = ClaudeRunner()
        prompt = self.system_prompt.format(max_iterations=self.max_iterations)

        attempt = 0
        while True:
            attempt += 1
            stdout, returncode = runner.run(prompt, self.working_dir)

            should_retry, wait_seconds = self.retry_manager.check(
                stdout, returncode, attempt
            )

            if not should_retry:
                return {"stdout": stdout, "returncode": returncode}

            import time
            time.sleep(wait_seconds)

    def _is_complete(self, result: Dict[str, Any]) -> bool:
        """Check if task is complete"""
        return self.exit_signal in result.get("stdout", "")

    def _create_user_prompt(self, user_prompt: str):
        """Create USER_PROMPT.md in working directory"""
        prompt_file = self.working_dir / "USER_PROMPT.md"
        prompt_file.write_text(user_prompt)
```

### atom_core/retry.py

```python
"""Retry logic for network errors, session limits, etc."""
import re
from datetime import datetime, timedelta
from config import (
    NETWORK_ERROR_KEYWORDS, NETWORK_RETRY_BASE, NETWORK_RETRY_MAX,
    OTHER_RETRY_BASE, OTHER_RETRY_MAX, SESSION_LIMIT_BUFFER,
    DEFAULT_SESSION_LIMIT_WAIT
)

class RetryManager:
    """Handles retry logic - extracted from atom.py"""

    def check(self, stdout: str, returncode: int, attempt: int = 1) -> tuple[bool, int]:
        """
        Check if we should retry.

        Returns:
            (should_retry: bool, wait_seconds: int)
        """
        # Success - no retry
        if returncode == 0:
            return False, 0

        # Session limit with specific reset time
        if "Session limit reached" in stdout:
            wait = self._parse_reset_time(stdout)
            if wait > 0:
                print(f"⏳ Session limit - waiting until reset ({wait//60} minutes)")
                return True, wait
            else:
                print(f"⏳ Session limit - waiting {DEFAULT_SESSION_LIMIT_WAIT//60} minutes")
                return True, DEFAULT_SESSION_LIMIT_WAIT

        # Network/transient errors
        if any(err in stdout.lower() for err in NETWORK_ERROR_KEYWORDS):
            wait = min(NETWORK_RETRY_BASE * (2 ** (attempt - 1)), NETWORK_RETRY_MAX)
            print(f"⚠️  Network error - waiting {wait}s (attempt {attempt})")
            return True, wait

        # Other errors - exponential backoff
        wait = min(OTHER_RETRY_BASE * (2 ** (attempt - 1)), OTHER_RETRY_MAX)
        print(f"⚠️  Error (code {returncode}) - waiting {wait}s (attempt {attempt})")
        return True, wait

    def _parse_reset_time(self, text: str) -> int:
        """Parse 'resets Xpm' message, return seconds to wait"""
        match = re.search(r'resets (\d+)(am|pm)', text, re.IGNORECASE)
        if not match:
            return 0

        hour = int(match.group(1))
        period = match.group(2).lower()

        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0

        now = datetime.now()
        reset = now.replace(hour=hour, minute=0, second=0, microsecond=0)

        if reset <= now:
            reset += timedelta(days=1)

        return int((reset - now).total_seconds() + SESSION_LIMIT_BUFFER)
```

### atom_core/context.py

```python
"""Context accumulation across iterations"""
from typing import List, Dict, Any

class ContextAccumulator:
    """
    Track iteration history.

    Note: Claude Code's -c flag handles actual context accumulation.
    This is for inspection/debugging only.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def add(self, iteration: int, result: Dict[str, Any]):
        """Add iteration result to history"""
        self.history.append({
            "iteration": iteration,
            "stdout": result.get("stdout", ""),
            "returncode": result.get("returncode", -1)
        })

    def get_all(self) -> List[Dict[str, Any]]:
        """Get full history"""
        return self.history

    def get_summary(self) -> str:
        """Get summary for debugging"""
        return f"{len(self.history)} iterations completed"
```

### atom_core/prompt_loader.py

```python
"""Prompt loading with search path support"""
from pathlib import Path
from typing import Optional
from config import PROMPT_SEARCH_PATHS

class PromptLoader:
    """Load prompts with composition and search paths"""

    def load(self, toolname: Optional[str] = None) -> str:
        """
        Load system prompt(s) based on toolname.

        Rules:
        - toolname=None -> ATOM.md
        - toolname='atom_foo' -> ATOM.md + FOO.md
        - toolname='foo' -> FOO.md only

        Searches in order:
        1. Project-local (.atom_tools/prompts/)
        2. Global (~/cc_atoms/prompts/)
        3. User override (ATOM_PROMPTS_PATH env var)
        """
        # Determine which files to load
        if toolname is None:
            files = ["ATOM.md"]
        elif toolname.startswith("atom_"):
            files = ["ATOM.md", f"{toolname[5:].upper()}.md"]
        else:
            files = [f"{toolname.upper()}.md"]

        # Load and combine
        contents = []
        for filename in files:
            filepath = self._find_prompt(filename)
            if not filepath:
                raise FileNotFoundError(
                    f"Prompt {filename} not found in search paths: {PROMPT_SEARCH_PATHS}"
                )
            contents.append(filepath.read_text())

        return "\n\n".join(contents)

    def _find_prompt(self, filename: str) -> Optional[Path]:
        """Find prompt file in search paths"""
        for search_path in PROMPT_SEARCH_PATHS:
            if not search_path.exists():
                continue
            filepath = search_path / filename
            if filepath.exists():
                return filepath
        return None
```

### atom_core/claude_runner.py

```python
"""Execute Claude Code"""
import subprocess
from pathlib import Path

class ClaudeRunner:
    """Execute Claude Code with proper flags"""

    def run(
        self,
        prompt: str,
        working_dir: Path,
        use_context: bool = True,
        dangerous_skip: bool = True
    ) -> tuple[str, int]:
        """
        Run Claude Code and return (stdout, returncode).

        Args:
            prompt: System prompt (passed via -p)
            working_dir: Where to run claude -c (determines conversation)
            use_context: Use -c flag for context accumulation
            dangerous_skip: Use --dangerously-skip-permissions

        Returns:
            (stdout, returncode)
        """
        cmd = ["claude"]

        if use_context:
            cmd.append("-c")

        cmd.extend(["-p", prompt])

        if dangerous_skip:
            cmd.append("--dangerously-skip-permissions")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=working_dir
        )

        return result.stdout, result.returncode
```

### atom_core/__init__.py

```python
"""cc_atoms core - Embeddable atom orchestration"""

from .runtime import AtomRuntime
from .retry import RetryManager
from .context import ContextAccumulator
from .prompt_loader import PromptLoader
from .claude_runner import ClaudeRunner

__version__ = "1.0.0"

__all__ = [
    "AtomRuntime",
    "RetryManager",
    "ContextAccumulator",
    "PromptLoader",
    "ClaudeRunner",
]
```

---

## Config Changes

### config.py (UPDATED)

```python
"""Central configuration for cc_atoms project."""
from pathlib import Path
import os

# Directory structure
ATOMS_HOME = Path.home() / "cc_atoms"
BIN_DIR = ATOMS_HOME / "bin"
TOOLS_DIR = ATOMS_HOME / "tools"
PROMPTS_DIR = ATOMS_HOME / "prompts"
TESTS_DIR = ATOMS_HOME / "tests"

# NEW - Search paths for tools and prompts
# Priority: project-local → global → user override
TOOL_SEARCH_PATHS = [
    Path.cwd() / ".atom_tools",                          # Project-local (highest priority)
    TOOLS_DIR,                                           # Global cc_atoms tools
    Path(os.getenv("ATOM_TOOLS_PATH", "/nonexistent"))  # User override via env var
]

PROMPT_SEARCH_PATHS = [
    Path.cwd() / ".atom_tools" / "prompts",              # Project-local prompts
    PROMPTS_DIR,                                         # Global prompts
    Path(os.getenv("ATOM_PROMPTS_PATH", "/nonexistent")) # User override via env var
]

# Iteration settings
MAX_ITERATIONS = 25
EXIT_SIGNAL = "EXIT_LOOP_NOW"

# Retry settings (unchanged)
NETWORK_ERROR_KEYWORDS = ["network", "timeout", "connection", "temporary"]
NETWORK_RETRY_BASE = 5
NETWORK_RETRY_MAX = 300
OTHER_RETRY_BASE = 10
OTHER_RETRY_MAX = 600
SESSION_LIMIT_BUFFER = 300
DEFAULT_SESSION_LIMIT_WAIT = 3600
```

---

## Refactored atom.py

### atom.py (REFACTORED)

```python
#!/usr/bin/env python3
"""atom.py - Minimal autonomous Claude Code orchestrator"""
import argparse
import sys
from pathlib import Path

from atom_core import AtomRuntime, PromptLoader
from config import MAX_ITERATIONS

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Atom: Minimal autonomous Claude Code orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompt text to create USER_PROMPT.md"
    )
    parser.add_argument(
        "--toolname",
        type=str,
        default=None,
        help="Tool name to load specialized prompts (e.g., 'atom_my_tool' or 'my_tool')"
    )
    return parser.parse_args()

def handle_command_line_prompt(prompt_args):
    """Create USER_PROMPT.md from command line arguments if provided."""
    if prompt_args:
        prompt_text = " ".join(prompt_args)
        prompt_file = Path("USER_PROMPT.md")
        prompt_file.write_text(prompt_text)
        print(f"📝 Created USER_PROMPT.md with provided prompt\n")

def validate_user_prompt():
    """Ensure USER_PROMPT.md exists in current directory."""
    prompt_file = Path("USER_PROMPT.md")
    if not prompt_file.exists():
        print("❌ USER_PROMPT.md not found in current directory")
        print("Usage: atom [prompt text]")
        print("   or: create USER_PROMPT.md manually and run: atom")
        sys.exit(1)

def setup_atoms_environment():
    """Ensure ~/cc_atoms directory structure exists and bin is in PATH."""
    import os
    from config import BIN_DIR, TOOLS_DIR, PROMPTS_DIR

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    if str(BIN_DIR) not in os.environ.get('PATH', ''):
        os.environ['PATH'] = f"{BIN_DIR}:{os.environ['PATH']}"

def main():
    # Parse command line arguments
    args = parse_arguments()

    # Setup phase
    handle_command_line_prompt(args.prompt)
    validate_user_prompt()
    setup_atoms_environment()

    print(f"🔬 Atom: {Path.cwd().name}\n")

    # Load system prompt
    loader = PromptLoader()
    system_prompt = loader.load(args.toolname)

    # Create runtime
    runtime = AtomRuntime(
        system_prompt=system_prompt,
        max_iterations=MAX_ITERATIONS,
        working_dir=Path.cwd(),
        verbose=True
    )

    # Read user prompt
    user_prompt = Path("USER_PROMPT.md").read_text()

    # Run
    result = runtime.run(user_prompt)

    # Report
    if result["success"]:
        print(f"\n✅ Complete after {result['iterations']} iterations")
        return 0
    else:
        print(f"\n⚠️  {result['reason']}")
        return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Key Changes:**
- Went from 243 lines → ~90 lines
- All logic delegated to `atom_core`
- **Behavior identical** to current atom.py
- Same CLI arguments
- Same output format
- Same iteration loop

---

## Example Tool: gui_control

### tools/gui_control/gui_control.py

```python
#!/usr/bin/env python3
"""
gui_control - GUI automation tool with embedded atom orchestration
"""
import sys
import tempfile
from pathlib import Path

# Import atom_core for embedded orchestration
from atom_core import AtomRuntime

class GUIControlTool:
    """GUI automation using embedded atom iteration/retry"""

    def __init__(self):
        # Load specialized prompt
        prompt_file = Path(__file__).parent / "GUI_CONTROL.md"
        self.system_prompt = prompt_file.read_text()

    def execute(self, task: str, max_iterations: int = 10) -> dict:
        """
        Execute GUI task with atom iteration/retry.

        Args:
            task: Natural language GUI task description
            max_iterations: Max iterations (GUI tasks are usually quick)

        Returns:
            {"success": bool, "iterations": int, "output": str}
        """
        # Use temporary directory for ephemeral atom session
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = AtomRuntime(
                system_prompt=self.system_prompt,
                max_iterations=max_iterations,
                working_dir=Path(tmpdir),
                verbose=False  # Don't spam user with iteration details
            )

            result = runtime.run(task)

        return result

def main():
    if len(sys.argv) < 2:
        print("Usage: gui_control 'task description'")
        print("\nExamples:")
        print("  gui_control 'Click the submit button in Safari'")
        print("  gui_control 'Type test@example.com in login field'")
        sys.exit(1)

    tool = GUIControlTool()
    task = " ".join(sys.argv[1:])

    print(f"🎯 Task: {task}")
    print("🔄 Executing...\n")

    result = tool.execute(task)

    if result["success"]:
        print(f"\n✅ Success in {result['iterations']} iterations")
        return 0
    else:
        print(f"\n❌ Failed: {result.get('reason', 'unknown')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### tools/gui_control/GUI_CONTROL.md

```markdown
# You are a GUI Automation Specialist

You use the mac_gui_control Python library to automate macOS GUI interactions.

## Available Library

```python
from mac_gui_control import Mouse, Keyboard, Vision, Screen, Element, Window, Role
```

## Three-Level Strategy

Try methods in this order:

1. **Accessibility API** (fastest, most reliable for standard UIs)
2. **Vision System** (works on custom UIs, games)
3. **Raw Coordinates** (always works)

## Iteration Pattern

Each iteration:
1. Try one approach
2. Verify it worked
3. If success: Output "EXIT_LOOP_NOW"
4. If failure: Try next approach in next iteration

## Example

Task: "Click submit button in Safari"

Iteration 1:
```python
from mac_gui_control import Element, Mouse, Role

button = Element.find(role=Role.BUTTON, title="Submit", app_name="Safari")
if button:
    Mouse.click_at(*button.center)
    print("✅ Clicked via accessibility")
    print("EXIT_LOOP_NOW")
else:
    print("❌ Not found via accessibility")
```

Iteration 2 (if needed):
```python
from mac_gui_control import Vision, Mouse

matches = Vision.find_image("submit.png", app_name="Safari", confidence=0.8)
if matches:
    Mouse.click_at(*matches[0].center)
    print("✅ Clicked via vision")
    print("EXIT_LOOP_NOW")
```
```

---

## Project-Local Tools

### Directory Structure

```
~/my-project/
├── .atom_tools/              # Project-local tools (not in ~/cc_atoms)
│   ├── prompts/             # Project-specific prompts
│   │   └── MY_TOOL.md
│   └── my_tool/             # Project-specific tool
│       └── my_tool.py
└── my_project_code/
```

### Usage

```bash
cd ~/my-project
atom --toolname my_tool "Do task"

# Looks for prompts in order:
# 1. ~/my-project/.atom_tools/prompts/MY_TOOL.md  (found! uses this)
# 2. ~/cc_atoms/prompts/MY_TOOL.md               (fallback)
```

### Benefits

- ✅ Tools stay with the project
- ✅ Don't pollute global ~/cc_atoms/tools/
- ✅ Can version control with project
- ✅ Project-specific customization

---

## Backward Compatibility

### Existing Behavior Preserved

All existing usage patterns continue to work identically:

```bash
# These all work exactly the same
atom "Create a TODO app"
atom --toolname atom_test "Run tests"
cd project && atom
```

### Conversation Mapping (Unchanged)

```
Directory                       Conversation
---------------------------------------------------------------------
~/my-project/                → ~/.claude/conversations/<hash1>/
~/my-project/sub-atom/       → ~/.claude/conversations/<hash2>/
/tmp/tmpdir123/              → ~/.claude/conversations/<hash3>/
```

**Conversation location is determined by `working_dir` passed to `claude -c`.**
This is unchanged - Claude Code handles it automatically.

### No Migration Required

Existing atoms continue working:
- atom.py behavior identical
- Same prompts work
- Same directory structure
- Same output format

---

## Migration Path

### Phase 1: Create atom_core (No Breaking Changes)

1. Create `~/cc_atoms/atom_core/` directory
2. Create all atom_core modules:
   - `runtime.py`
   - `retry.py`
   - `context.py`
   - `prompt_loader.py`
   - `claude_runner.py`
   - `__init__.py`
3. **Test:** Import atom_core, verify classes work

### Phase 2: Update config.py (Additive)

1. Add `TOOL_SEARCH_PATHS`
2. Add `PROMPT_SEARCH_PATHS`
3. **Test:** Config imports without errors

### Phase 3: Refactor atom.py (Behavior Identical)

1. Backup current `atom.py` as `atom.py.backup`
2. Refactor `atom.py` to use `atom_core`
3. **Test:** Run existing atoms, verify identical behavior
4. **Test:** All existing prompts work
5. **Test:** Context accumulation works

### Phase 4: Create gui_control Tool (New Feature)

1. Create `tools/gui_control/` directory
2. Create `gui_control.py`
3. Create `GUI_CONTROL.md` prompt
4. Create launcher in `bin/gui_control`
5. **Test:** `gui_control "Click button"` works

### Phase 5: Validate (Comprehensive)

1. Run existing test suite
2. Test all existing tools (atom_gui, atom_create_tool, etc.)
3. Test project-local tools
4. Test prompt search paths
5. Verify conversations still map correctly

---

## Testing Strategy

### Unit Tests

```python
# tests/test_atom_core.py
from atom_core import AtomRuntime

def test_runtime_basic():
    """Test basic runtime execution"""
    runtime = AtomRuntime(
        system_prompt="Test prompt {max_iterations}",
        max_iterations=3,
        working_dir=Path("/tmp/test")
    )
    # Mock claude execution, verify iteration loop works

def test_retry_logic():
    """Test retry manager"""
    from atom_core import RetryManager
    manager = RetryManager()

    # Test network error retry
    should_retry, wait = manager.check("network error", 1, attempt=1)
    assert should_retry == True
    assert wait == 5  # NETWORK_RETRY_BASE
```

### Integration Tests

```bash
# Test existing atom.py behavior
cd test-project
echo "Create hello.txt" > USER_PROMPT.md
atom
# Verify: hello.txt created, EXIT_LOOP_NOW in output

# Test gui_control tool
gui_control "Move mouse to 500,500"
# Verify: tool completes successfully

# Test project-local prompts
mkdir -p .atom_tools/prompts
echo "Custom prompt" > .atom_tools/prompts/TEST.md
atom --toolname test
# Verify: uses local prompt, not global
```

### Backward Compatibility Tests

```bash
# Test all existing prompts work
atom --toolname atom_test
atom --toolname atom_session_analyzer

# Test all existing tools work
atom_gui .
atom_create_tool

# Verify conversation locations unchanged
# (Check ~/.claude/conversations/<hash>/ created correctly)
```

---

## Files to Create/Modify

### New Files (9 files)

1. `~/cc_atoms/atom_core/__init__.py`
2. `~/cc_atoms/atom_core/runtime.py`
3. `~/cc_atoms/atom_core/retry.py`
4. `~/cc_atoms/atom_core/context.py`
5. `~/cc_atoms/atom_core/prompt_loader.py`
6. `~/cc_atoms/atom_core/claude_runner.py`
7. `~/cc_atoms/tools/gui_control/gui_control.py`
8. `~/cc_atoms/tools/gui_control/GUI_CONTROL.md`
9. `~/cc_atoms/bin/gui_control` (launcher)

### Modified Files (2 files)

1. `~/cc_atoms/config.py` (add search paths)
2. `~/cc_atoms/atom.py` (refactor to use atom_core)

### Backup Files (1 file)

1. `~/cc_atoms/atom.py.backup` (preserve original)

---

## Questions for Review

### 1. Architecture

**Q:** Does extracting logic into `atom_core/` make sense?
**Q:** Are there atom patterns this won't support?
**Q:** Better way to structure the modules?

### 2. API Design

**Q:** Is the `AtomRuntime` API intuitive?
**Q:** Should `verbose` parameter exist, or always be True?
**Q:** Any missing parameters or return values?

### 3. Search Paths

**Q:** Does the tool/prompt search path mechanism make sense?
**Q:** Should we support more than 3 search locations?
**Q:** Better naming for `.atom_tools/` directory?

### 4. Backward Compatibility

**Q:** Any existing usage patterns this breaks?
**Q:** Should we preserve atom.py.backup permanently?
**Q:** Migration path missing any steps?

### 5. Conversation Handling

**Q:** Does the `working_dir` → conversation mapping concern you?
**Q:** Any edge cases with temporary directories?
**Q:** Should we document conversation lifecycle more explicitly?

### 6. Testing

**Q:** What tests would give you confidence this works?
**Q:** Should we add integration tests to existing test suite?
**Q:** Any atom behaviors we should specifically test?

### 7. Implementation Order

**Q:** Is the migration path reasonable?
**Q:** Should we implement differently (e.g., parallel branch)?
**Q:** Any dependencies we're missing?

---

## Success Criteria

This refactor is successful if:

1. ✅ All existing atoms continue working identically
2. ✅ All existing tools (atom_gui, etc.) continue working
3. ✅ New tools can use `atom_core` for embedded orchestration
4. ✅ Project-local tools work via search paths
5. ✅ Conversations still map correctly to directories
6. ✅ Test suite passes
7. ✅ No performance regression
8. ✅ Code is more maintainable (logic extracted into classes)

---

## Next Steps

1. **Review this spec** - cc_atoms conversation feedback
2. **Address feedback** - Adjust design based on review
3. **Implement** - Execute migration path in order
4. **Test** - Comprehensive testing at each phase
5. **Validate** - Verify existing atoms still work
6. **Document** - Update cc_atoms documentation

---

## Appendix: Example Usage Scenarios

### Scenario 1: Existing Atom (No Change)

```bash
cd ~/my-project
atom "Create a web scraper"
# Works exactly as before
```

### Scenario 2: Embedded in Tool

```bash
gui_control "Click submit in Safari"
# Behind scenes: uses AtomRuntime for iteration
# User sees: simple command, clean output
```

### Scenario 3: Project-Local Tool

```bash
cd ~/my-library
mkdir -p .atom_tools/prompts
cat > .atom_tools/prompts/TEST.md << EOF
You are a test specialist for this library.
EOF

atom --toolname test "Run all tests"
# Uses local TEST.md prompt
```

### Scenario 4: Embedded in Library

```python
# In mac_gui_control/auto.py
from atom_core import AtomRuntime

agent = AutomationAgent()
result = agent.execute("Automate download")
# Library provides AI automation without exposing atom complexity
```

---

**END OF SPECIFICATION**

**Status:** Ready for review by cc_atoms conversation
**Reviewers:** Please provide feedback on architecture, API, compatibility, and implementation approach
**Target:** Implement in current conversation after approval
