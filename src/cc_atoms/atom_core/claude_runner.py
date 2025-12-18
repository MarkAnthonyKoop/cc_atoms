"""Execute Claude Code with proper flags"""
import subprocess
from pathlib import Path
from typing import Tuple


class ClaudeRunner:
    """
    Execute Claude Code with proper flags.

    Handles the actual subprocess call to 'claude -c' with appropriate
    parameters for context accumulation and permissions.
    """

    def run(
        self,
        prompt: str,
        conversation_dir: Path,
        use_context: bool = True,
        dangerous_skip: bool = True
    ) -> Tuple[str, int]:
        """
        Run Claude Code and return (stdout, returncode).

        Args:
            prompt: System prompt (passed via -p)
            conversation_dir: Where to run claude -c
                            **Critical:** This determines which conversation is used!
                            - Same dir = resume existing conversation
                            - New dir = start fresh conversation
            use_context: Use -c flag for context accumulation
            dangerous_skip: Use --dangerously-skip-permissions

        Returns:
            (stdout, returncode)

        Raises:
            FileNotFoundError: If claude command not found
            PermissionError: If conversation_dir not accessible
        """
        # Validate conversation_dir exists
        if not conversation_dir.exists():
            raise FileNotFoundError(
                f"Conversation directory does not exist: {conversation_dir}"
            )

        # Build command
        cmd = ["claude"]

        if use_context:
            cmd.append("-c")

        cmd.extend(["-p", prompt])

        if dangerous_skip:
            cmd.append("--dangerously-skip-permissions")

        # Execute
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=conversation_dir
        )

        return result.stdout, result.returncode
