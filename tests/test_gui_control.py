#!/usr/bin/env python3
"""
Tests for gui_control tool

These tests verify:
1. Module imports and structure
2. System prompt content
3. control_gui function signature and behavior
4. Integration with AtomRuntime (mocked)
5. CLI entry point
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from cc_atoms.tools.gui_control import control_gui, main
from cc_atoms.tools.gui_control.gui_control import SYSTEM_PROMPT


class TestGuiControlModule:
    """Tests for gui_control module structure"""

    def test_module_imports(self):
        """Test that gui_control can be imported"""
        from cc_atoms.tools.gui_control import control_gui, main
        assert callable(control_gui), "control_gui should be callable"
        assert callable(main), "main should be callable"
        print("✓ gui_control module imports correctly")

    def test_system_prompt_exists(self):
        """Test that SYSTEM_PROMPT is defined and non-empty"""
        assert SYSTEM_PROMPT is not None, "SYSTEM_PROMPT should exist"
        assert len(SYSTEM_PROMPT) > 100, "SYSTEM_PROMPT should be substantial"
        print(f"✓ SYSTEM_PROMPT exists ({len(SYSTEM_PROMPT)} chars)")

    def test_system_prompt_has_key_sections(self):
        """Test that SYSTEM_PROMPT contains expected content"""
        required_content = [
            "GUI",
            "macOS",
            "accessibility",
            "click",
            "screenshot",
        ]
        for content in required_content:
            assert content.lower() in SYSTEM_PROMPT.lower(), f"SYSTEM_PROMPT should mention '{content}'"
        print("✓ SYSTEM_PROMPT contains key sections")

    def test_system_prompt_has_task_placeholder(self):
        """Test that SYSTEM_PROMPT has {user_task} placeholder"""
        assert "{user_task}" in SYSTEM_PROMPT, "SYSTEM_PROMPT should have {user_task} placeholder"
        print("✓ SYSTEM_PROMPT has {user_task} placeholder")


class TestControlGuiFunction:
    """Tests for the control_gui function"""

    def test_function_signature(self):
        """Test that control_gui has expected parameters"""
        import inspect
        sig = inspect.signature(control_gui)
        params = list(sig.parameters.keys())

        assert "task" in params, "Should have 'task' parameter"
        assert "max_iterations" in params, "Should have 'max_iterations' parameter"
        print(f"✓ control_gui signature: {params}")

    def test_returns_dict_on_success(self):
        """Test that control_gui returns proper result dict"""
        with patch('cc_atoms.tools.gui_control.gui_control.AtomRuntime') as MockRuntime:
            # Setup mock
            mock_instance = MagicMock()
            mock_instance.run.return_value = {
                "success": True,
                "iterations": 3,
                "output": "Task completed\nEXIT_LOOP_NOW",
                "duration": 15.5,
            }
            MockRuntime.create_ephemeral.return_value = mock_instance

            # Call function
            result = control_gui("Click the button")

            # Verify
            assert isinstance(result, dict), "Should return dict"
            assert "success" in result, "Result should have 'success' key"
            assert result["success"] == True, "Should indicate success"
            print("✓ control_gui returns proper result dict")

    def test_passes_task_to_prompt(self):
        """Test that task is injected into system prompt"""
        with patch('cc_atoms.tools.gui_control.gui_control.AtomRuntime') as MockRuntime:
            mock_instance = MagicMock()
            mock_instance.run.return_value = {"success": True, "iterations": 1, "output": "", "duration": 1.0}
            MockRuntime.create_ephemeral.return_value = mock_instance

            # Call with specific task
            control_gui("Click the submit button in Safari")

            # Check that create_ephemeral was called with task in prompt
            call_args = MockRuntime.create_ephemeral.call_args
            system_prompt = call_args[1]["system_prompt"]
            assert "Click the submit button in Safari" in system_prompt, "Task should be in system prompt"
            print("✓ Task is injected into system prompt")

    def test_respects_max_iterations(self):
        """Test that max_iterations is passed to runtime"""
        with patch('cc_atoms.tools.gui_control.gui_control.AtomRuntime') as MockRuntime:
            mock_instance = MagicMock()
            mock_instance.run.return_value = {"success": True, "iterations": 1, "output": "", "duration": 1.0}
            MockRuntime.create_ephemeral.return_value = mock_instance

            # Call with custom max_iterations
            control_gui("Test task", max_iterations=5)

            # Verify
            call_args = MockRuntime.create_ephemeral.call_args
            assert call_args[1]["max_iterations"] == 5, "Should pass max_iterations to runtime"
            print("✓ max_iterations is respected")

    def test_uses_ephemeral_runtime(self):
        """Test that control_gui uses create_ephemeral (not regular constructor)"""
        with patch('cc_atoms.tools.gui_control.gui_control.AtomRuntime') as MockRuntime:
            mock_instance = MagicMock()
            mock_instance.run.return_value = {"success": True, "iterations": 1, "output": "", "duration": 1.0}
            MockRuntime.create_ephemeral.return_value = mock_instance

            control_gui("Test task")

            # Should use create_ephemeral, not direct instantiation
            MockRuntime.create_ephemeral.assert_called_once()
            MockRuntime.assert_not_called()  # Direct constructor not called
            print("✓ Uses create_ephemeral for temporary sessions")


class TestGuiControlCLI:
    """Tests for gui_control CLI entry point"""

    def test_cli_help_works(self):
        """Test that CLI --help works"""
        import subprocess
        result = subprocess.run(
            ["/opt/homebrew/bin/python3", "-m", "cc_atoms.tools.gui_control.gui_control", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"--help should exit 0, got {result.returncode}"
        assert "gui-control" in result.stdout.lower() or "usage" in result.stdout.lower()
        print("✓ CLI --help works")


def main_test():
    """Run all gui_control tests"""
    print("Running gui_control tests...\n")

    try:
        # Module tests
        print("Testing module structure...")
        test_module = TestGuiControlModule()
        test_module.test_module_imports()
        test_module.test_system_prompt_exists()
        test_module.test_system_prompt_has_key_sections()
        test_module.test_system_prompt_has_task_placeholder()
        print()

        # Function tests
        print("Testing control_gui function...")
        test_func = TestControlGuiFunction()
        test_func.test_function_signature()
        test_func.test_returns_dict_on_success()
        test_func.test_passes_task_to_prompt()
        test_func.test_respects_max_iterations()
        test_func.test_uses_ephemeral_runtime()
        print()

        # CLI tests
        print("Testing CLI...")
        test_cli = TestGuiControlCLI()
        test_cli.test_cli_help_works()
        print()

        print("\n✅ All gui_control tests passed!")
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main_test())
