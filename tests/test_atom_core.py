#!/usr/bin/env python3
"""Test suite for atom_core library"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cc_atoms.atom_core import (
    AtomRuntime,
    PromptLoader,
    RetryManager,
    IterationHistory,
    ClaudeRunner
)
from cc_atoms import config


class TestPromptLoader:
    """Tests for PromptLoader with search path support"""

    def test_load_default_atom(self):
        """Test loading ATOM.md when no toolname provided"""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir(parents=True)

            atom_content = "# ATOM System Prompt\nBase prompt."
            (prompts_dir / "ATOM.md").write_text(atom_content)

            # Patch search paths in both config and prompt_loader module
            with patch('cc_atoms.atom_core.prompt_loader.PROMPT_SEARCH_PATHS', [prompts_dir]):
                loader = PromptLoader()
                result = loader.load()
                assert result == atom_content, "Should load ATOM.md by default"
                print("✓ PromptLoader: Default loads ATOM.md")

    def test_load_atom_prefix(self):
        """Test loading ATOM.md + TOOL.md for atom_* toolnames"""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir(parents=True)

            atom_content = "# ATOM Base"
            tool_content = "# Tool Specific"
            (prompts_dir / "ATOM.md").write_text(atom_content)
            (prompts_dir / "TEST.md").write_text(tool_content)

            with patch('cc_atoms.atom_core.prompt_loader.PROMPT_SEARCH_PATHS', [prompts_dir]):
                loader = PromptLoader()
                result = loader.load("atom_test")
                expected = f"{atom_content}\n\n{tool_content}"
                assert result == expected, "Should compose ATOM.md + TEST.md"
                print("✓ PromptLoader: atom_test loads ATOM.md + TEST.md")

    def test_load_no_prefix(self):
        """Test loading TOOL.md only for toolnames without atom_ prefix"""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir(parents=True)

            tool_content = "# Standalone Tool"
            (prompts_dir / "MYTOOL.md").write_text(tool_content)

            with patch('cc_atoms.atom_core.prompt_loader.PROMPT_SEARCH_PATHS', [prompts_dir]):
                loader = PromptLoader()
                result = loader.load("mytool")
                assert result == tool_content, "Should load MYTOOL.md only"
                print("✓ PromptLoader: mytool loads MYTOOL.md only")

    def test_search_path_priority(self):
        """Test that project-local prompts override global ones"""
        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "local"
            global_dir = Path(tmpdir) / "global"
            local_dir.mkdir(parents=True)
            global_dir.mkdir(parents=True)

            local_content = "# Local ATOM"
            global_content = "# Global ATOM"
            (local_dir / "ATOM.md").write_text(local_content)
            (global_dir / "ATOM.md").write_text(global_content)

            with patch('cc_atoms.atom_core.prompt_loader.PROMPT_SEARCH_PATHS', [local_dir, global_dir]):
                loader = PromptLoader()
                result = loader.load()
                assert result == local_content, "Should prefer local over global"
                print("✓ PromptLoader: Local prompts override global")


class TestRetryManager:
    """Tests for RetryManager with callback logging"""

    def test_no_retry_on_success(self):
        """Test that successful runs don't trigger retry"""
        manager = RetryManager()
        stdout = "Task completed successfully\nEXIT_LOOP_NOW"
        returncode = 0

        should_retry, wait = manager.check(stdout, returncode, attempt=1)
        assert not should_retry, "Should not retry on success"
        print("✓ RetryManager: No retry on success")

    def test_retry_on_session_limit(self):
        """Test retry on session limit with proper wait time"""
        callback_calls = []
        def mock_callback(msg, seconds):
            callback_calls.append((msg, seconds))

        manager = RetryManager(on_retry_message=mock_callback)
        stdout = "Session limit reached. resets 3pm"
        returncode = 1  # Session limits return non-zero

        should_retry, wait = manager.check(stdout, returncode, attempt=1)
        assert should_retry, "Should retry on session limit"
        assert wait > 0, "Should have positive wait time"
        assert len(callback_calls) == 1, "Should call callback once"
        print(f"✓ RetryManager: Session limit triggers retry (wait={wait}s)")

    def test_retry_on_network_error(self):
        """Test retry on network errors with exponential backoff"""
        manager = RetryManager()
        stdout = "Network timeout occurred"
        returncode = 1

        # First attempt
        should_retry, wait1 = manager.check(stdout, returncode, attempt=1)
        assert should_retry, "Should retry on network error"

        # Second attempt - should have longer wait
        should_retry, wait2 = manager.check(stdout, returncode, attempt=2)
        assert should_retry, "Should retry again"
        assert wait2 >= wait1, "Should use exponential backoff"
        print(f"✓ RetryManager: Network errors use exponential backoff (wait1={wait1}, wait2={wait2})")

    def test_custom_callback(self):
        """Test that custom callback receives messages"""
        messages = []
        def custom_callback(msg, sec):
            messages.append(f"{msg} ({sec}s)")

        manager = RetryManager(on_retry_message=custom_callback)
        stdout = "Temporary error"
        returncode = 1

        manager.check(stdout, returncode, attempt=1)
        assert len(messages) > 0, "Custom callback should be called"
        print(f"✓ RetryManager: Custom callback works ({messages[0]})")


class TestIterationHistory:
    """Tests for IterationHistory context tracking"""

    def test_add_and_retrieve_iterations(self):
        """Test adding and retrieving iteration data"""
        history = IterationHistory()

        result1 = {"stdout": "Iteration 1 output", "returncode": 0}
        result2 = {"stdout": "Iteration 2 output", "returncode": 0}

        history.add_iteration(1, result1)
        history.add_iteration(2, result2)

        all_iterations = history.get_all_iterations()
        assert len(all_iterations) == 2, "Should have 2 iterations"
        assert all_iterations[0]["iteration"] == 1
        assert all_iterations[1]["iteration"] == 2
        print("✓ IterationHistory: Add and retrieve works")

    def test_iteration_includes_timestamp(self):
        """Test that iterations include timestamps"""
        history = IterationHistory()
        result = {"stdout": "Test", "returncode": 0}

        history.add_iteration(1, result)
        iterations = history.get_all_iterations()

        assert "timestamp" in iterations[0], "Should include timestamp"
        assert iterations[0]["timestamp"] > 0, "Timestamp should be positive"
        print("✓ IterationHistory: Timestamps included")

    def test_empty_history(self):
        """Test empty history returns empty list"""
        history = IterationHistory()
        assert history.get_all_iterations() == [], "Empty history should return []"
        print("✓ IterationHistory: Empty history works")


class TestClaudeRunner:
    """Tests for ClaudeRunner subprocess execution"""

    def test_builds_correct_command(self):
        """Test that ClaudeRunner builds the correct command"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runner = ClaudeRunner()

            # Mock subprocess.run to capture command
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout="test output", returncode=0)

                runner.run(
                    prompt="Test prompt",
                    conversation_dir=conversation_dir,
                    use_context=True,
                    dangerous_skip=True
                )

                # Check command structure
                called_cmd = mock_run.call_args[0][0]
                assert called_cmd[0] == "claude", "Should use claude command"
                assert "-c" in called_cmd, "Should include -c flag"
                assert "-p" in called_cmd, "Should include -p flag"
                assert "--dangerously-skip-permissions" in called_cmd, "Should include dangerous skip"
                print("✓ ClaudeRunner: Builds correct command")

    def test_raises_on_missing_directory(self):
        """Test that ClaudeRunner raises error if directory doesn't exist"""
        runner = ClaudeRunner()
        nonexistent_dir = Path("/tmp/this_directory_should_not_exist_12345")

        try:
            runner.run("Test", nonexistent_dir)
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError as e:
            assert "does not exist" in str(e)
            print("✓ ClaudeRunner: Raises on missing directory")


class TestAtomRuntime:
    """Tests for AtomRuntime orchestration"""

    def test_create_ephemeral(self):
        """Test creating ephemeral runtime with temp directory"""
        runtime = AtomRuntime.create_ephemeral(
            system_prompt="Test prompt",
            max_iterations=5
        )

        assert runtime.conversation_dir.exists(), "Temp dir should exist"
        assert runtime.max_iterations == 5, "Should use provided max_iterations"
        assert runtime.cleanup == True, "Ephemeral should auto-cleanup"
        assert runtime.verbose == False, "Ephemeral should default to quiet"
        print("✓ AtomRuntime: create_ephemeral() works")

    def test_conversation_dir_parameter(self):
        """Test that conversation_dir parameter is required"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=Path(tmpdir),
                max_iterations=10
            )

            assert runtime.conversation_dir == Path(tmpdir)
            print("✓ AtomRuntime: conversation_dir parameter works")

    def test_smart_verbose_detection(self):
        """Test smart verbose auto-detection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test explicit True
            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=Path(tmpdir),
                verbose=True
            )
            assert runtime.verbose == True

            # Test explicit False
            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=Path(tmpdir),
                verbose=False
            )
            assert runtime.verbose == False
            print("✓ AtomRuntime: Smart verbose detection works")

    def test_creates_user_prompt_file(self):
        """Test that runtime creates USER_PROMPT.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test {max_iterations}",
                conversation_dir=conversation_dir,
                max_iterations=10
            )

            # Mock claude_runner to avoid actual execution
            with patch.object(runtime.claude_runner, 'run') as mock_run:
                mock_run.return_value = ("EXIT_LOOP_NOW", 0)

                runtime.run("Test task")

                # Check that USER_PROMPT.md was created
                prompt_file = conversation_dir / "USER_PROMPT.md"
                assert prompt_file.exists(), "Should create USER_PROMPT.md"
                assert prompt_file.read_text() == "Test task"
                print("✓ AtomRuntime: Creates USER_PROMPT.md")

    def test_cleanup_removes_user_prompt(self):
        """Test that cleanup=True removes USER_PROMPT.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversation_dir = Path(tmpdir)

            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=conversation_dir,
                max_iterations=10,
                cleanup=True
            )

            with patch.object(runtime.claude_runner, 'run') as mock_run:
                mock_run.return_value = ("EXIT_LOOP_NOW", 0)

                runtime.run("Test task")

                prompt_file = conversation_dir / "USER_PROMPT.md"
                assert not prompt_file.exists(), "Should delete USER_PROMPT.md"
                print("✓ AtomRuntime: Cleanup removes USER_PROMPT.md")

    def test_result_dict_structure(self):
        """Test that run() returns proper result dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=Path(tmpdir),
                max_iterations=5
            )

            with patch.object(runtime.claude_runner, 'run') as mock_run:
                mock_run.return_value = ("EXIT_LOOP_NOW", 0)

                result = runtime.run("Test task")

                assert "success" in result
                assert "iterations" in result
                assert "output" in result
                assert "duration" in result
                assert result["success"] == True
                print("✓ AtomRuntime: Result dict has correct structure")

    def test_error_handling(self):
        """Test comprehensive error handling"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=Path(tmpdir),
                max_iterations=5
            )

            # Test FileNotFoundError
            with patch.object(runtime.claude_runner, 'run') as mock_run:
                mock_run.side_effect = FileNotFoundError("claude not found")

                result = runtime.run("Test task")

                assert result["success"] == False
                assert result["reason"] == "claude_not_found"
                assert "error" in result
                print("✓ AtomRuntime: Handles FileNotFoundError")

    def test_max_iterations_reached(self):
        """Test behavior when max iterations is reached"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = AtomRuntime(
                system_prompt="Test",
                conversation_dir=Path(tmpdir),
                max_iterations=2
            )

            with patch.object(runtime.claude_runner, 'run') as mock_run:
                # Never complete
                mock_run.return_value = ("Still working...", 0)

                result = runtime.run("Test task")

                assert result["success"] == False
                assert result["reason"] == "max_iterations"
                assert result["iterations"] == 2
                print("✓ AtomRuntime: Handles max iterations")


def main():
    """Run all tests"""
    print("Running atom_core tests...\n")

    try:
        # PromptLoader tests
        print("Testing PromptLoader...")
        test_loader = TestPromptLoader()
        test_loader.test_load_default_atom()
        test_loader.test_load_atom_prefix()
        test_loader.test_load_no_prefix()
        test_loader.test_search_path_priority()
        print()

        # RetryManager tests
        print("Testing RetryManager...")
        test_retry = TestRetryManager()
        test_retry.test_no_retry_on_success()
        test_retry.test_retry_on_session_limit()
        test_retry.test_retry_on_network_error()
        test_retry.test_custom_callback()
        print()

        # IterationHistory tests
        print("Testing IterationHistory...")
        test_history = TestIterationHistory()
        test_history.test_add_and_retrieve_iterations()
        test_history.test_iteration_includes_timestamp()
        test_history.test_empty_history()
        print()

        # ClaudeRunner tests
        print("Testing ClaudeRunner...")
        test_runner = TestClaudeRunner()
        test_runner.test_builds_correct_command()
        test_runner.test_raises_on_missing_directory()
        print()

        # AtomRuntime tests
        print("Testing AtomRuntime...")
        test_runtime = TestAtomRuntime()
        test_runtime.test_create_ephemeral()
        test_runtime.test_conversation_dir_parameter()
        test_runtime.test_smart_verbose_detection()
        test_runtime.test_creates_user_prompt_file()
        test_runtime.test_cleanup_removes_user_prompt()
        test_runtime.test_result_dict_structure()
        test_runtime.test_error_handling()
        test_runtime.test_max_iterations_reached()
        print()

        print("\n✅ All atom_core tests passed!")
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
