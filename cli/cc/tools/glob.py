"""Glob tool for finding files by pattern."""

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class GlobTool(BaseTool):
    """Tool for finding files using glob patterns."""

    name = "Glob"
    description = """Find files matching a glob pattern.

Supports patterns like "**/*.py" or "src/**/*.ts".
Returns file paths sorted by modification time (most recent first)."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize glob tool.

        Args:
            cwd: Working directory for search
        """
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Find files matching a pattern.

        Args:
            pattern: Glob pattern to match
            path: Directory to search in (defaults to cwd)

        Returns:
            ToolResult with matching file paths
        """
        pattern = kwargs.get("pattern", "")
        search_path = kwargs.get("path", self.cwd)

        if not pattern:
            return ToolResult(
                success=False,
                output="",
                error="No pattern provided",
            )

        # Resolve path
        if not os.path.isabs(search_path):
            search_path = os.path.join(self.cwd, search_path)

        if not os.path.exists(search_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Search path does not exist: {search_path}",
            )

        try:
            # Use pathlib for glob
            base_path = Path(search_path)
            matches: List[Path] = list(base_path.glob(pattern))

            # Filter to only files
            file_matches = [p for p in matches if p.is_file()]

            # Sort by modification time (most recent first)
            file_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Limit results
            max_results = 1000
            truncated = len(file_matches) > max_results
            file_matches = file_matches[:max_results]

            # Format output
            output_lines = [str(p) for p in file_matches]
            output = "\n".join(output_lines)

            if truncated:
                output += f"\n\n... (showing first {max_results} of {len(matches)} matches)"

            if not file_matches:
                output = f"No files matching pattern: {pattern}"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "match_count": len(file_matches),
                    "pattern": pattern,
                    "search_path": str(search_path),
                    "truncated": truncated,
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
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files (e.g., '**/*.py')",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in. Defaults to current directory.",
                },
            },
            required=["pattern"],
        )
