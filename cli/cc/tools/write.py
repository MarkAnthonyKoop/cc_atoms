"""Write tool for writing file contents."""

import os
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class WriteTool(BaseTool):
    """Tool for writing file contents."""

    name = "Write"
    description = """Write content to a file.

Creates the file if it doesn't exist, or overwrites if it does.
Creates parent directories as needed."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize write tool.

        Args:
            cwd: Working directory for relative paths
        """
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Write content to a file.

        Args:
            file_path: Path to the file to write
            content: Content to write

        Returns:
            ToolResult with status
        """
        file_path = kwargs.get("file_path", "")
        content = kwargs.get("content", "")

        if not file_path:
            return ToolResult(
                success=False,
                output="",
                error="No file path provided",
            )

        # Resolve path
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.cwd, file_path)

        try:
            # Check if trying to write to a directory
            if os.path.exists(file_path) and os.path.isdir(file_path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Cannot write to directory: {file_path}. Specify a file path.",
                )

            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except PermissionError:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Permission denied creating directory: {parent_dir}",
                    )

            # Check if file exists for reporting
            file_existed = os.path.exists(file_path)

            # Validate content (warn about very large files)
            content_size = len(content.encode("utf-8"))
            if content_size > 10 * 1024 * 1024:  # 10MB
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Content too large ({content_size / 1024 / 1024:.1f} MB). "
                          f"Maximum 10MB per write operation.",
                )

            # Write content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            action = "Updated" if file_existed else "Created"
            line_count = len(content.splitlines())

            return ToolResult(
                success=True,
                output=f"{action} {file_path} ({line_count} lines, {content_size:,} bytes)",
                metadata={
                    "file_path": file_path,
                    "action": action.lower(),
                    "lines": line_count,
                    "bytes": content_size,
                },
            )

        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied writing to file: {file_path}",
            )
        except OSError as e:
            if e.errno == 28:  # No space left on device
                return ToolResult(
                    success=False,
                    output="",
                    error=f"No space left on device when writing: {file_path}",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"OS error writing file: {e}",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Unexpected error writing file: {e}",
            )

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API."""
        return create_tool_definition(
            name=cls.name,
            description=cls.description,
            properties={
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            required=["file_path", "content"],
        )
