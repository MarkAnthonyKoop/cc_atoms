"""Grep tool for searching file contents."""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class GrepTool(BaseTool):
    """Tool for searching file contents with regex."""

    name = "Grep"
    description = """Search for patterns in files using regex.

Supports full regex syntax. Can filter by file type or glob pattern.
Output modes: 'content' shows matching lines, 'files_with_matches' shows paths only."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize grep tool.

        Args:
            cwd: Working directory for search
        """
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Search for a pattern in files.

        Args:
            pattern: Regex pattern to search for
            path: File or directory to search in
            glob: Glob pattern to filter files
            type: File type (e.g., 'py', 'js')
            output_mode: 'content', 'files_with_matches', or 'count'
            case_insensitive: Case insensitive search (-i)

        Returns:
            ToolResult with search results
        """
        pattern = kwargs.get("pattern", "")
        search_path = kwargs.get("path", self.cwd)
        glob_pattern = kwargs.get("glob")
        file_type = kwargs.get("type")
        output_mode = kwargs.get("output_mode", "files_with_matches")
        case_insensitive = kwargs.get("-i", False)
        context_before = kwargs.get("-B", 0)
        context_after = kwargs.get("-A", 0)
        context = kwargs.get("-C", 0)
        show_line_numbers = kwargs.get("-n", True)
        head_limit = kwargs.get("head_limit", 100)

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

        # Use context if specified
        if context > 0:
            context_before = context
            context_after = context

        try:
            # Try to use ripgrep if available, otherwise fall back to Python
            rg_available = self._check_ripgrep()

            if rg_available:
                return await self._search_ripgrep(
                    pattern=pattern,
                    search_path=search_path,
                    glob_pattern=glob_pattern,
                    file_type=file_type,
                    output_mode=output_mode,
                    case_insensitive=case_insensitive,
                    context_before=context_before,
                    context_after=context_after,
                    show_line_numbers=show_line_numbers,
                    head_limit=head_limit,
                )
            else:
                return await self._search_python(
                    pattern=pattern,
                    search_path=search_path,
                    glob_pattern=glob_pattern,
                    file_type=file_type,
                    output_mode=output_mode,
                    case_insensitive=case_insensitive,
                    head_limit=head_limit,
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    def _check_ripgrep(self) -> bool:
        """Check if ripgrep is available."""
        try:
            subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    async def _search_ripgrep(
        self,
        pattern: str,
        search_path: str,
        glob_pattern: Optional[str],
        file_type: Optional[str],
        output_mode: str,
        case_insensitive: bool,
        context_before: int,
        context_after: int,
        show_line_numbers: bool,
        head_limit: int,
    ) -> ToolResult:
        """Search using ripgrep."""
        cmd = ["rg"]

        # Output mode
        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")

        # Case insensitive
        if case_insensitive:
            cmd.append("-i")

        # Line numbers
        if show_line_numbers and output_mode == "content":
            cmd.append("-n")

        # Context
        if context_before > 0:
            cmd.extend(["-B", str(context_before)])
        if context_after > 0:
            cmd.extend(["-A", str(context_after)])

        # File type
        if file_type:
            cmd.extend(["--type", file_type])

        # Glob pattern
        if glob_pattern:
            cmd.extend(["--glob", glob_pattern])

        # Pattern and path
        cmd.extend([pattern, search_path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout
            if result.returncode == 1:
                # No matches found
                return ToolResult(
                    success=True,
                    output="No matches found.",
                    metadata={"match_count": 0},
                )
            elif result.returncode != 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=result.stderr or f"ripgrep exited with code {result.returncode}",
                )

            # Apply head limit
            lines = output.splitlines()
            if len(lines) > head_limit:
                lines = lines[:head_limit]
                output = "\n".join(lines) + f"\n\n... (showing first {head_limit} results)"
            else:
                output = "\n".join(lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "match_count": len(lines),
                    "pattern": pattern,
                },
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error="Search timed out after 60 seconds",
            )

    async def _search_python(
        self,
        pattern: str,
        search_path: str,
        glob_pattern: Optional[str],
        file_type: Optional[str],
        output_mode: str,
        case_insensitive: bool,
        head_limit: int,
    ) -> ToolResult:
        """Search using pure Python (fallback)."""
        flags = re.IGNORECASE if case_insensitive else 0

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid regex pattern: {e}",
            )

        results: List[str] = []
        match_count = 0
        base_path = Path(search_path)

        # Get files to search
        if base_path.is_file():
            files = [base_path]
        else:
            if glob_pattern:
                files = list(base_path.rglob(glob_pattern))
            elif file_type:
                files = list(base_path.rglob(f"*.{file_type}"))
            else:
                files = list(base_path.rglob("*"))

            files = [f for f in files if f.is_file()]

        for file_path in files:
            if len(results) >= head_limit:
                break

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (PermissionError, OSError):
                continue

            if output_mode == "files_with_matches":
                if regex.search(content):
                    results.append(str(file_path))
                    match_count += 1
            elif output_mode == "count":
                count = len(regex.findall(content))
                if count > 0:
                    results.append(f"{file_path}:{count}")
                    match_count += count
            else:
                # content mode
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        results.append(f"{file_path}:{i}:{line}")
                        match_count += 1
                        if len(results) >= head_limit:
                            break

        output = "\n".join(results)
        if not results:
            output = "No matches found."

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "match_count": match_count,
                "pattern": pattern,
            },
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
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.js')",
                },
                "type": {
                    "type": "string",
                    "description": "File type to search (e.g., 'py', 'js')",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output mode: content, files_with_matches, or count",
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search",
                },
                "-n": {
                    "type": "boolean",
                    "description": "Show line numbers",
                },
                "-B": {
                    "type": "number",
                    "description": "Lines of context before match",
                },
                "-A": {
                    "type": "number",
                    "description": "Lines of context after match",
                },
                "-C": {
                    "type": "number",
                    "description": "Lines of context before and after",
                },
                "head_limit": {
                    "type": "number",
                    "description": "Limit number of results",
                },
            },
            required=["pattern"],
        )
