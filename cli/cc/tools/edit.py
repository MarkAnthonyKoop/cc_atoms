"""Edit tool for making precise file edits."""

import os
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class EditTool(BaseTool):
    """Tool for making precise string replacements in files."""

    name = "Edit"
    description = """Perform exact string replacements in files.

Replaces occurrences of old_string with new_string in the specified file.
Use replace_all=true to replace all occurrences, otherwise only the first match."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize edit tool.

        Args:
            cwd: Working directory for relative paths
        """
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Edit a file by replacing text.

        Args:
            file_path: Path to the file to edit
            old_string: Text to find and replace
            new_string: Text to replace with
            replace_all: Whether to replace all occurrences

        Returns:
            ToolResult with status
        """
        file_path = kwargs.get("file_path", "")
        old_string = kwargs.get("old_string", "")
        new_string = kwargs.get("new_string", "")
        replace_all = kwargs.get("replace_all", False)

        if not file_path:
            return ToolResult(
                success=False,
                output="",
                error="No file path provided",
            )

        if not old_string:
            return ToolResult(
                success=False,
                output="",
                error="No old_string provided",
            )

        if old_string == new_string:
            return ToolResult(
                success=False,
                output="",
                error="old_string and new_string are identical",
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

        try:
            # Read current content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Count occurrences
            count = content.count(old_string)

            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error="old_string not found in file",
                )

            if count > 1 and not replace_all:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"old_string appears {count} times. Use replace_all=true to replace all, or provide more context to make it unique.",
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                success=True,
                output=f"Edited {file_path}: {replacements} replacement(s) made",
                metadata={
                    "file_path": file_path,
                    "replacements": replacements,
                    "bytes_removed": len(old_string) * replacements,
                    "bytes_added": len(new_string) * replacements,
                },
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
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace old_string with",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false)",
                    "default": False,
                },
            },
            required=["file_path", "old_string", "new_string"],
        )
