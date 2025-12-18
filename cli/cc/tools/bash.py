"""Bash tool for executing shell commands."""

import asyncio
import os
import shlex
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class BashTool(BaseTool):
    """Tool for executing bash commands."""

    name = "Bash"
    description = """Execute a bash command in the shell.

Use this tool to run shell commands like git, npm, python, etc.
Commands run in the current working directory."""

    def __init__(
        self,
        timeout: int = 120,
        cwd: Optional[str] = None,
    ) -> None:
        """Initialize bash tool.

        Args:
            timeout: Command timeout in seconds
            cwd: Working directory for commands
        """
        self.timeout = timeout
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute a bash command.

        Args:
            command: The command to execute
            timeout: Optional timeout override in milliseconds

        Returns:
            ToolResult with command output
        """
        command = kwargs.get("command", "")
        if not command:
            return ToolResult(
                success=False,
                output="",
                error="No command provided",
            )

        # Get timeout (convert from ms to seconds if provided)
        timeout_ms = kwargs.get("timeout")
        timeout = (timeout_ms / 1000) if timeout_ms else self.timeout

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds",
                )

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # Combine stdout and stderr
            output = stdout_text
            if stderr_text:
                if output:
                    output += "\n"
                output += stderr_text

            # Truncate if too long
            max_length = 30000
            if len(output) > max_length:
                output = output[:max_length] + "\n... (output truncated)"

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output=output,
                    error=f"Command exited with code {process.returncode}",
                    metadata={"exit_code": process.returncode},
                )

            return ToolResult(
                success=True,
                output=output,
                metadata={"exit_code": 0},
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API."""
        return create_tool_definition(
            name=cls.name,
            description=cls.description,
            properties={
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in milliseconds (max 600000)",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this command does",
                },
            },
            required=["command"],
        )
