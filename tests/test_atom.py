#!/usr/bin/env python3
"""Test suite for cc_atoms CLI interface

Note: PromptLoader tests are now in test_atom_core.py.
This file tests the CLI helper functions.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from cc_atoms import cli
from cc_atoms import config


def test_helper_functions_exist():
    """Test that refactored helper functions exist"""
    assert hasattr(cli, 'parse_arguments'), "Missing parse_arguments"
    assert hasattr(cli, 'handle_command_line_prompt'), "Missing handle_command_line_prompt"
    assert hasattr(cli, 'validate_user_prompt'), "Missing validate_user_prompt"
    assert hasattr(cli, 'setup_atoms_environment'), "Missing setup_atoms_environment"
    print("✓ Test passed: All helper functions exist")


def test_handle_command_line_prompt():
    """Test that handle_command_line_prompt creates USER_PROMPT.md"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Test with prompt args
            cli.handle_command_line_prompt(["Hello", "World"])
            prompt_file = Path("USER_PROMPT.md")
            assert prompt_file.exists(), "Should create USER_PROMPT.md"
            assert prompt_file.read_text() == "Hello World", "Should join args with spaces"
            print("✓ Test passed: handle_command_line_prompt creates file")

            # Clean up
            prompt_file.unlink()

            # Test with empty args
            cli.handle_command_line_prompt([])
            assert not prompt_file.exists(), "Should not create file for empty args"
            print("✓ Test passed: handle_command_line_prompt skips empty args")

        finally:
            os.chdir(original_cwd)


def test_validate_user_prompt():
    """Test that validate_user_prompt checks for USER_PROMPT.md"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Should exit when no USER_PROMPT.md
            try:
                cli.validate_user_prompt()
                assert False, "Should have called sys.exit"
            except SystemExit as e:
                assert e.code == 1, "Should exit with code 1"
                print("✓ Test passed: validate_user_prompt exits when missing")

            # Should not exit when USER_PROMPT.md exists
            Path("USER_PROMPT.md").write_text("Test prompt")
            cli.validate_user_prompt()  # Should not raise
            print("✓ Test passed: validate_user_prompt passes when file exists")

        finally:
            os.chdir(original_cwd)


def test_setup_atoms_environment():
    """Test that setup_atoms_environment creates directories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch config paths to use temp directory
        test_atoms_home = Path(tmpdir) / "cc_atoms"
        test_bin_dir = test_atoms_home / "bin"
        test_tools_dir = test_atoms_home / "tools"
        test_prompts_dir = test_atoms_home / "prompts"

        with patch.object(config, 'BIN_DIR', test_bin_dir), \
             patch.object(config, 'TOOLS_DIR', test_tools_dir), \
             patch.object(config, 'PROMPTS_DIR', test_prompts_dir):

            cli.setup_atoms_environment()

            assert test_bin_dir.exists(), "Should create bin directory"
            assert test_tools_dir.exists(), "Should create tools directory"
            assert test_prompts_dir.exists(), "Should create prompts directory"
            print("✓ Test passed: setup_atoms_environment creates directories")


def test_atom_uses_atom_core():
    """Test that cc_atoms uses atom_core components"""
    # Verify imports work
    from cc_atoms.atom_core import AtomRuntime, PromptLoader
    assert AtomRuntime is not None
    assert PromptLoader is not None
    print("✓ Test passed: atom_core components available")


def main():
    """Run all tests"""
    print("Running cc_atoms CLI tests...\n")

    try:
        test_helper_functions_exist()
        test_handle_command_line_prompt()
        test_validate_user_prompt()
        test_setup_atoms_environment()
        test_atom_uses_atom_core()

        print("\n✅ All CLI tests passed!")
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
