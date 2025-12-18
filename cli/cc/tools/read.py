"""Read tool for reading file contents."""

import os
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class ReadTool(BaseTool):
    """Tool for reading file contents."""

    name = "Read"
    description = """Read a file from the filesystem.

Returns the file contents with line numbers. Supports offset and limit
for reading specific portions of large files."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize read tool.

        Args:
            cwd: Working directory for relative paths
        """
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Read a file.

        Args:
            file_path: Path to the file to read
            offset: Line number to start from (1-based)
            limit: Number of lines to read

        Returns:
            ToolResult with file contents
        """
        file_path = kwargs.get("file_path", "")
        if not file_path:
            return ToolResult(
                success=False,
                output="",
                error="No file path provided",
            )

        # Resolve path
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.cwd, file_path)

        if not os.path.exists(file_path):
            return ToolResult(
                success=False,
                output="",
                error=f"File does not exist: {file_path}",
            )

        if os.path.isdir(file_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Cannot read directory: {file_path}. Use Bash with ls instead.",
            )

        offset = kwargs.get("offset", 0)
        limit = kwargs.get("limit", 2000)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            # Validate offset and limit
            if offset < 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid offset: {offset}. Offset must be >= 0.",
                )

            if limit and limit < 1:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid limit: {limit}. Limit must be > 0.",
                )

            # Handle empty file
            if not lines:
                return ToolResult(
                    success=True,
                    output="(empty file)",
                    metadata={
                        "total_lines": 0,
                        "lines_read": 0,
                        "start_line": 0,
                    },
                )

            # Apply offset and limit
            start_line = offset if offset > 0 else 0

            # Check if offset is beyond file length
            if start_line >= len(lines):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Offset {offset} exceeds file length ({len(lines)} lines)",
                )

            end_line = start_line + limit if limit else len(lines)
            selected_lines = lines[start_line:end_line]

            # Format with line numbers (1-based)
            output_lines = []
            max_line_num = start_line + len(selected_lines)
            line_num_width = len(str(max_line_num))

            for i, line in enumerate(selected_lines, start=start_line + 1):
                # Truncate long lines
                line = line.rstrip("\n\r")
                if len(line) > 2000:
                    line = line[:2000] + "..."
                output_lines.append(f"{i:>{line_num_width}}\t{line}")

            output = "\n".join(output_lines)

            # Add info about truncation if applicable
            if len(lines) > end_line:
                remaining = len(lines) - end_line
                output += f"\n\n... ({remaining} more lines)"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "total_lines": len(lines),
                    "lines_read": len(selected_lines),
                    "start_line": start_line + 1,
                },
            )

        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied reading file: {file_path}",
            )
        except UnicodeDecodeError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"File contains invalid UTF-8: {file_path}. This might be a binary file.",
            )
        except OSError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"OS error reading file: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Unexpected error reading file: {e}",
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
                    "description": "The absolute path to the file to read",
                },
                "offset": {
                    "type": "number",
                    "description": "Line number to start from (0-based). Optional.",
                },
                "limit": {
                    "type": "number",
                    "description": "Number of lines to read. Defaults to 2000.",
                },
            },
            required=["file_path"],
        )
