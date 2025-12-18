#!/usr/bin/env python3
"""
Integration tests for cc_atoms

These tests verify end-to-end behavior with controlled environments.
They test real interactions between components without mocking internal parts.

Note: These tests do NOT call actual Claude API - they mock at the subprocess level.
"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from cc_atoms import AtomRuntime, PromptLoader
from cc_atoms.config import EXIT_SIGNAL


class TestRealConfiguration:
    """Tests that verify real configuration works (not mocked)"""

    def test_package_prompts_exist(self):
        """Test that package-bundled prompts are accessible"""
        from cc_atoms.config import PACKAGE_PROMPTS_DIR

        assert PACKAGE_PROMPTS_DIR.exists(), f"Package prompts dir should exist: {PACKAGE_PROMPTS_DIR}"

        atom_md = PACKAGE_PROMPTS_DIR / "ATOM.md"
        assert atom_md.exists(), f"ATOM.md should exist: {atom_md}"

        content = atom_md.read_text()
        assert len(content) > 100, "ATOM.md should have substantial content"
        print(f"✓ Package prompts exist at {PACKAGE_PROMPTS_DIR}")

    def test_prompt_loader_finds_real_atom_md(self):
        """Test that PromptLoader can find ATOM.md without mocking"""
        from cc_atoms import PromptLoader

        loader = PromptLoader()
        prompt = loader.load()  # Should find ATOM.md

        assert prompt is not None, "Should load prompt"
        assert len(prompt) > 100, "Prompt should have content"
        assert "iteration" in prompt.lower() or "claude" in prompt.lower(), "Should look like ATOM.md"
        print(f"✓ PromptLoader finds real ATOM.md ({len(prompt)} chars)")

    def test_search_paths_include_package_dir(self):
        """Test that search paths include the package prompts directory"""
        from cc_atoms.config import PROMPT_SEARCH_PATHS, PACKAGE_PROMPTS_DIR

        assert PACKAGE_PROMPTS_DIR in PROMPT_SEARCH_PATHS, \
            f"PACKAGE_PROMPTS_DIR should be in search paths. Got: {PROMPT_SEARCH_PATHS}"
        print(f"✓ Search paths include package dir: {PACKAGE_PROMPTS_DIR}")


class TestFullAtomWorkflow:
    """Integration tests for complete atom workflow"""

    def test_runtime_creates_and_uses_user_prompt(self):
        """Test that AtomRuntime creates USER_PROMPT.md and passes it to Claude"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            # Create runtime
            runtime = AtomRuntime(
                system_prompt="You are a test assistant.",
                conversation_dir=conversation_dir,
                max_iterations=1,
                verbose=False
            )

            # Mock subprocess.run to capture what would be sent to Claude
            captured_calls = []

            def mock_subprocess_run(cmd, *args, **kwargs):
                captured_calls.append(cmd)
                mock_result = MagicMock()
                mock_result.stdout = f"Task done.\n{EXIT_SIGNAL}"
                mock_result.returncode = 0
                return mock_result

            with patch('subprocess.run', side_effect=mock_subprocess_run):
                result = runtime.run("Build a web scraper")

            # Verify USER_PROMPT.md was created
            user_prompt_file = conversation_dir / "USER_PROMPT.md"
            assert user_prompt_file.exists(), "USER_PROMPT.md should be created"
            assert user_prompt_file.read_text() == "Build a web scraper"

            # Verify Claude was called
            assert len(captured_calls) >= 1, "Should have called subprocess"

            # Verify result
            assert result["success"] == True
            assert result["iterations"] == 1
            print("✓ Full workflow: USER_PROMPT.md created, Claude called, success returned")

    def test_prompt_loader_integration_with_runtime(self):
        """Test that PromptLoader output works with AtomRuntime"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup prompt directory
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()
            (prompts_dir / "ATOM.md").write_text("# Base Prompt\nYou are helpful.")
            (prompts_dir / "TEST.md").write_text("# Test Extension\nFocus on testing.")

            conversation_dir = Path(tmpdir) / "conv"
            conversation_dir.mkdir()

            # Load prompt
            with patch('cc_atoms.atom_core.prompt_loader.PROMPT_SEARCH_PATHS', [prompts_dir]):
                loader = PromptLoader()
                system_prompt = loader.load("atom_test")

            # Verify composition
            assert "Base Prompt" in system_prompt
            assert "Test Extension" in system_prompt

            # Use with runtime
            runtime = AtomRuntime(
                system_prompt=system_prompt,
                conversation_dir=conversation_dir,
                max_iterations=1,
                verbose=False
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout=EXIT_SIGNAL, returncode=0)
                result = runtime.run("Run tests")

            assert result["success"] == True
            print("✓ PromptLoader integrates with AtomRuntime")

    def test_iteration_loop_stops_on_exit_signal(self):
        """Test that iteration loop correctly stops when EXIT_SIGNAL is found"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=conversation_dir,
                max_iterations=10,  # High limit
                verbose=False
            )

            call_count = [0]

            def mock_run(cmd, *args, **kwargs):
                call_count[0] += 1
                mock_result = MagicMock()
                if call_count[0] >= 3:
                    mock_result.stdout = f"Done!\n{EXIT_SIGNAL}"
                else:
                    mock_result.stdout = "Still working..."
                mock_result.returncode = 0
                return mock_result

            with patch('subprocess.run', side_effect=mock_run):
                result = runtime.run("Task")

            assert result["success"] == True
            assert result["iterations"] == 3, f"Should stop at 3 iterations, got {result['iterations']}"
            print("✓ Iteration loop stops on EXIT_SIGNAL")

    def test_iteration_loop_stops_at_max(self):
        """Test that iteration loop stops at max_iterations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=conversation_dir,
                max_iterations=3,
                verbose=False
            )

            def mock_run(cmd, *args, **kwargs):
                mock_result = MagicMock()
                mock_result.stdout = "Still working..."  # Never sends EXIT_SIGNAL
                mock_result.returncode = 0
                return mock_result

            with patch('subprocess.run', side_effect=mock_run):
                result = runtime.run("Endless task")

            assert result["success"] == False
            assert result["reason"] == "max_iterations"
            assert result["iterations"] == 3
            print("✓ Iteration loop stops at max_iterations")


class TestCLIIntegration:
    """Integration tests for CLI"""

    def test_cli_creates_user_prompt_and_runs(self):
        """Test that CLI creates USER_PROMPT.md from arguments"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # Create required prompt file
                prompts_dir = Path(tmpdir) / ".atom" / "prompts"
                prompts_dir.mkdir(parents=True)
                (prompts_dir / "ATOM.md").write_text("# Test")

                # Simulate CLI behavior
                from cc_atoms.cli import handle_command_line_prompt, validate_user_prompt

                # Handle command line prompt
                handle_command_line_prompt(["Create", "a", "calculator"])

                # Verify file created
                user_prompt = Path("USER_PROMPT.md")
                assert user_prompt.exists()
                assert user_prompt.read_text() == "Create a calculator"

                # Validate should pass now
                validate_user_prompt()  # Should not raise

                print("✓ CLI creates USER_PROMPT.md from arguments")

            finally:
                os.chdir(original_cwd)


class TestRetryIntegration:
    """Integration tests for retry behavior"""

    def test_retry_on_transient_error(self):
        """Test that transient errors trigger retry"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=conversation_dir,
                max_iterations=5,
                verbose=False
            )

            call_count = [0]

            def mock_run(cmd, *args, **kwargs):
                call_count[0] += 1
                mock_result = MagicMock()

                if call_count[0] == 1:
                    # First call fails with network error
                    mock_result.stdout = "Network timeout occurred"
                    mock_result.returncode = 1
                else:
                    # Second call succeeds
                    mock_result.stdout = f"Success!\n{EXIT_SIGNAL}"
                    mock_result.returncode = 0

                return mock_result

            # Patch time.sleep to avoid actual waiting
            with patch('subprocess.run', side_effect=mock_run):
                with patch('time.sleep'):
                    result = runtime.run("Task with retry")

            # Should have retried and succeeded
            assert call_count[0] >= 2, "Should have retried at least once"
            print(f"✓ Retry on transient error (called {call_count[0]} times)")


class TestCleanupBehavior:
    """Integration tests for cleanup behavior"""

    def test_cleanup_true_removes_files(self):
        """Test that cleanup=True removes USER_PROMPT.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=conversation_dir,
                max_iterations=1,
                verbose=False,
                cleanup=True
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout=EXIT_SIGNAL, returncode=0)
                runtime.run("Task")

            user_prompt = conversation_dir / "USER_PROMPT.md"
            assert not user_prompt.exists(), "USER_PROMPT.md should be deleted with cleanup=True"
            print("✓ cleanup=True removes USER_PROMPT.md")

    def test_cleanup_false_keeps_files(self):
        """Test that cleanup=False keeps USER_PROMPT.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=conversation_dir,
                max_iterations=1,
                verbose=False,
                cleanup=False
            )

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout=EXIT_SIGNAL, returncode=0)
                runtime.run("Task")

            user_prompt = conversation_dir / "USER_PROMPT.md"
            assert user_prompt.exists(), "USER_PROMPT.md should be kept with cleanup=False"
            print("✓ cleanup=False keeps USER_PROMPT.md")


def main():
    """Run all integration tests"""
    print("Running integration tests...\n")

    try:
        # Real configuration tests (no mocking!)
        print("Testing real configuration (no mocks)...")
        test_config = TestRealConfiguration()
        test_config.test_package_prompts_exist()
        test_config.test_prompt_loader_finds_real_atom_md()
        test_config.test_search_paths_include_package_dir()
        print()

        # Full workflow tests
        print("Testing full atom workflow...")
        test_workflow = TestFullAtomWorkflow()
        test_workflow.test_runtime_creates_and_uses_user_prompt()
        test_workflow.test_prompt_loader_integration_with_runtime()
        test_workflow.test_iteration_loop_stops_on_exit_signal()
        test_workflow.test_iteration_loop_stops_at_max()
        print()

        # CLI integration tests
        print("Testing CLI integration...")
        test_cli = TestCLIIntegration()
        test_cli.test_cli_creates_user_prompt_and_runs()
        print()

        # Retry integration tests
        print("Testing retry integration...")
        test_retry = TestRetryIntegration()
        test_retry.test_retry_on_transient_error()
        print()

        # Cleanup tests
        print("Testing cleanup behavior...")
        test_cleanup = TestCleanupBehavior()
        test_cleanup.test_cleanup_true_removes_files()
        test_cleanup.test_cleanup_false_keeps_files()
        print()

        print("\n✅ All integration tests passed!")
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
    sys.exit(main())
