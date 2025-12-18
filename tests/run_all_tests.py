#!/usr/bin/env python3
"""
Comprehensive test suite for cc_atoms

Run this script to verify the current status of cc_atoms:
    python3 tests/run_all_tests.py

Or run individual test modules:
    python3 tests/test_atom_core.py
    python3 tests/test_atom.py
"""
import sys
import subprocess
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_pass(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_fail(text):
    print(f"{RED}✗ {text}{RESET}")


def print_warn(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


PYTHON = "/opt/homebrew/bin/python3"


def run_command(cmd, description):
    """Run a command and return success/failure"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print_pass(description)
            return True, result.stdout
        else:
            print_fail(f"{description}\n  Error: {result.stderr[:200]}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print_fail(f"{description} (timeout)")
        return False, "timeout"
    except Exception as e:
        print_fail(f"{description}\n  Exception: {e}")
        return False, str(e)


def test_imports():
    """Test that all cc_atoms imports work"""
    print_header("Testing Imports")

    tests = [
        ("from cc_atoms import AtomRuntime", "Import AtomRuntime"),
        ("from cc_atoms import PromptLoader", "Import PromptLoader"),
        ("from cc_atoms import RetryManager", "Import RetryManager"),
        ("from cc_atoms import IterationHistory", "Import IterationHistory"),
        ("from cc_atoms import ClaudeRunner", "Import ClaudeRunner"),
        ("from cc_atoms import cli", "Import CLI module"),
        ("from cc_atoms import config", "Import config module"),
        ("from cc_atoms.tools.gui_control import control_gui", "Import gui_control"),
    ]

    passed = 0
    for import_stmt, description in tests:
        success, _ = run_command(
            [PYTHON, "-c", import_stmt],
            description
        )
        if success:
            passed += 1

    return passed, len(tests)


def test_cli_help():
    """Test that CLI entry points show help"""
    print_header("Testing CLI Entry Points")

    tests = [
        ([PYTHON, "-m", "cc_atoms.cli", "--help"], "atom --help"),
    ]

    passed = 0
    for cmd, description in tests:
        success, output = run_command(cmd, description)
        if success:
            passed += 1

    return passed, len(tests)


def test_unit_tests():
    """Run the unit test suites"""
    print_header("Running Unit Tests")

    tests_dir = Path(__file__).parent
    python = "/opt/homebrew/bin/python3"

    tests = [
        ([python, str(tests_dir / "test_atom_core.py")], "atom_core unit tests"),
        ([python, str(tests_dir / "test_atom.py")], "CLI unit tests"),
        ([python, str(tests_dir / "test_gui_control.py")], "gui_control unit tests"),
        ([python, str(tests_dir / "test_atom_gui.py")], "atom_gui unit tests"),
        ([python, str(tests_dir / "test_integration.py")], "integration tests"),
    ]

    passed = 0
    for cmd, description in tests:
        success, output = run_command(cmd, description)
        if success:
            passed += 1
        else:
            # Show partial output on failure
            print(f"  Output: {output[:500]}...")

    return passed, len(tests)


def test_package_structure():
    """Verify the package structure is correct"""
    print_header("Testing Package Structure")

    src_dir = Path(__file__).parent.parent / "src" / "cc_atoms"

    required_files = [
        src_dir / "__init__.py",
        src_dir / "cli.py",
        src_dir / "config.py",
        src_dir / "atom_core" / "__init__.py",
        src_dir / "atom_core" / "runtime.py",
        src_dir / "atom_core" / "retry.py",
        src_dir / "atom_core" / "context.py",
        src_dir / "atom_core" / "prompt_loader.py",
        src_dir / "atom_core" / "claude_runner.py",
        src_dir / "tools" / "__init__.py",
        src_dir / "tools" / "gui_control" / "__init__.py",
        src_dir / "tools" / "gui_control" / "gui_control.py",
        src_dir / "prompts" / "ATOM.md",
    ]

    passed = 0
    for filepath in required_files:
        if filepath.exists():
            print_pass(f"Found {filepath.relative_to(src_dir.parent.parent)}")
            passed += 1
        else:
            print_fail(f"Missing {filepath.relative_to(src_dir.parent.parent)}")

    return passed, len(required_files)


def test_pyproject():
    """Verify pyproject.toml is valid"""
    print_header("Testing pyproject.toml")

    pyproject = Path(__file__).parent.parent / "pyproject.toml"

    tests_passed = 0
    tests_total = 0

    # Check file exists
    tests_total += 1
    if pyproject.exists():
        print_pass("pyproject.toml exists")
        tests_passed += 1
    else:
        print_fail("pyproject.toml not found")
        return 0, 1

    # Check it's valid TOML
    tests_total += 1
    try:
        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        print_pass("pyproject.toml is valid TOML")
        tests_passed += 1
    except ImportError:
        # Python < 3.11
        try:
            import toml
            data = toml.load(pyproject)
            print_pass("pyproject.toml is valid TOML")
            tests_passed += 1
        except ImportError:
            print_warn("Cannot validate TOML (install toml package)")
            data = None
    except Exception as e:
        print_fail(f"Invalid TOML: {e}")
        return tests_passed, tests_total

    if data:
        # Check required sections
        required_keys = [
            ("build-system", "Build system defined"),
            ("project", "Project metadata defined"),
            ("project.scripts", "CLI entry points defined"),
        ]

        for key_path, description in required_keys:
            tests_total += 1
            keys = key_path.split(".")
            obj = data
            found = True
            for k in keys:
                if isinstance(obj, dict) and k in obj:
                    obj = obj[k]
                else:
                    found = False
                    break

            if found:
                print_pass(description)
                tests_passed += 1
            else:
                print_fail(f"{description} (missing {key_path})")

    return tests_passed, tests_total


def test_pip_installable():
    """Test that the package can be pip installed"""
    print_header("Testing pip Installation (dry run)")

    project_root = Path(__file__).parent.parent

    # Just check that pip can parse the project
    success, output = run_command(
        [PYTHON, "-m", "pip", "show", "cc-atoms"],
        "Check if cc-atoms is installed"
    )

    if not success:
        print_warn("cc-atoms not installed. Install with: pip install -e .")
        return 0, 1

    return 1, 1


def main():
    print(f"\n{BLUE}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║           cc_atoms Verification Test Suite               ║{RESET}")
    print(f"{BLUE}╚══════════════════════════════════════════════════════════╝{RESET}")

    total_passed = 0
    total_tests = 0

    # Run all test categories
    test_functions = [
        test_package_structure,
        test_pyproject,
        test_imports,
        test_cli_help,
        test_unit_tests,
        test_pip_installable,
    ]

    results = []
    for test_fn in test_functions:
        passed, total = test_fn()
        total_passed += passed
        total_tests += total
        results.append((test_fn.__doc__, passed, total))

    # Summary
    print_header("Test Summary")

    for description, passed, total in results:
        status = GREEN + "PASS" + RESET if passed == total else RED + "FAIL" + RESET
        print(f"  {description}: {passed}/{total} [{status}]")

    print(f"\n{BLUE}{'─'*60}{RESET}")

    if total_passed == total_tests:
        print(f"{GREEN}All tests passed: {total_passed}/{total_tests}{RESET}")
        return 0
    else:
        print(f"{RED}Some tests failed: {total_passed}/{total_tests}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
