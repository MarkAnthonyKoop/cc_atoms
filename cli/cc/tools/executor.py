"""Tool executor with permission checking and registry."""

import fnmatch
import os
from typing import Any, Dict, List, Optional, Type

from .base import BaseTool, ToolResult
from .bash import BashTool
from .read import ReadTool
from .write import WriteTool
from .edit import EditTool
from .glob import GlobTool
from .grep import GrepTool


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        """Initialize tool registry."""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}
        self._cwd: str = os.getcwd()

        # Register built-in tools
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """Register all built-in tools."""
        builtin_tools = [
            BashTool,
            ReadTool,
            WriteTool,
            EditTool,
            GlobTool,
            GrepTool,
        ]
        for tool_class in builtin_tools:
            self._tools[tool_class.name] = tool_class

    def set_cwd(self, cwd: str) -> None:
        """Set working directory for tools.

        Args:
            cwd: Working directory path
        """
        self._cwd = cwd
        # Clear instances so they get recreated with new cwd
        self._instances.clear()

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool instance by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None
        """
        if name not in self._tools:
            return None

        if name not in self._instances:
            tool_class = self._tools[name]
            if name == "Bash":
                self._instances[name] = tool_class(cwd=self._cwd)
            else:
                self._instances[name] = tool_class(cwd=self._cwd)

        return self._instances[name]

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions.

        Returns:
            List of tool definitions for the API
        """
        return [tool_class.get_definition() for tool_class in self._tools.values()]

    def list_tools(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())


class PermissionChecker:
    """Check permissions for tool usage."""

    def __init__(
        self,
        allow_patterns: Optional[List[str]] = None,
        deny_patterns: Optional[List[str]] = None,
        skip_permissions: bool = False,
    ) -> None:
        """Initialize permission checker.

        Args:
            allow_patterns: Patterns for allowed tools
            deny_patterns: Patterns for denied tools
            skip_permissions: Skip all permission checks
        """
        self.allow_patterns = allow_patterns or []
        self.deny_patterns = deny_patterns or []
        self.skip_permissions = skip_permissions

    def is_allowed(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """Check if a tool use is allowed.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            True if allowed, False if denied
        """
        if self.skip_permissions:
            return True

        # Build tool signature for matching
        signature = self._build_signature(tool_name, tool_input)

        # Check deny patterns first
        for pattern in self.deny_patterns:
            if self._matches_pattern(signature, pattern):
                return False

        # If allow patterns exist, must match one
        if self.allow_patterns:
            for pattern in self.allow_patterns:
                if self._matches_pattern(signature, pattern):
                    return True
            return False

        # Default: allow
        return True

    def _build_signature(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Build a signature string for permission matching.

        Args:
            tool_name: Tool name
            tool_input: Tool parameters

        Returns:
            Signature string like "Bash(git:status)"
        """
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            # Extract first word as command name
            parts = command.split()
            if parts:
                cmd = parts[0]
                args = ":".join(parts[1:3]) if len(parts) > 1 else ""
                return f"Bash({cmd}:{args})" if args else f"Bash({cmd})"
            return "Bash"
        elif tool_name in ("Read", "Write", "Edit"):
            path = tool_input.get("file_path", "")
            return f"{tool_name}({path})"
        else:
            return tool_name

    def _matches_pattern(self, signature: str, pattern: str) -> bool:
        """Check if a signature matches a pattern.

        Patterns can include wildcards like:
        - "Bash" - matches all Bash commands
        - "Bash(git:*)" - matches all git commands
        - "Bash(git:status)" - matches specific command

        Args:
            signature: Tool signature
            pattern: Permission pattern

        Returns:
            True if matches
        """
        # Convert pattern to regex-like matching
        if pattern == signature:
            return True

        # Handle wildcard patterns
        if "*" in pattern:
            # Convert to fnmatch pattern
            return fnmatch.fnmatch(signature, pattern)

        # Handle prefix matching (e.g., "Bash" matches "Bash(git:status)")
        if "(" not in pattern:
            return signature.startswith(pattern + "(") or signature == pattern

        return False


class ToolExecutor:
    """Execute tools with permission checking."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_checker: Optional[PermissionChecker] = None,
    ) -> None:
        """Initialize tool executor.

        Args:
            registry: Tool registry
            permission_checker: Permission checker
        """
        self.registry = registry or ToolRegistry()
        self.permission_checker = permission_checker or PermissionChecker()

        # Hooks callbacks
        self._pre_tool_hooks: List[Any] = []
        self._post_tool_hooks: List[Any] = []

    def set_cwd(self, cwd: str) -> None:
        """Set working directory for all tools.

        Args:
            cwd: Working directory path
        """
        self.registry.set_cwd(cwd)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for the API.

        Returns:
            List of tool definitions
        """
        return self.registry.get_definitions()

    async def execute(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_id: str = "",
    ) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool
            tool_input: Tool parameters
            tool_id: Tool use ID (for hooks)

        Returns:
            ToolResult with output or error
        """
        # Check permissions
        if not self.permission_checker.is_allowed(tool_name, tool_input):
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied for {tool_name}",
            )

        # Get tool
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}",
            )

        # Run pre-tool hooks
        for hook in self._pre_tool_hooks:
            try:
                await hook(tool_name, tool_input, tool_id)
            except Exception:
                pass  # Hooks should not block execution

        # Execute tool
        try:
            result = await tool.execute(**tool_input)
        except Exception as e:
            result = ToolResult(
                success=False,
                output="",
                error=f"Tool execution error: {e}",
            )

        # Run post-tool hooks
        for hook in self._post_tool_hooks:
            try:
                await hook(tool_name, tool_input, tool_id, result)
            except Exception:
                pass

        return result

    def add_pre_hook(self, hook: Any) -> None:
        """Add a pre-tool execution hook.

        Args:
            hook: Async function(tool_name, tool_input, tool_id)
        """
        self._pre_tool_hooks.append(hook)

    def add_post_hook(self, hook: Any) -> None:
        """Add a post-tool execution hook.

        Args:
            hook: Async function(tool_name, tool_input, tool_id, result)
        """
        self._post_tool_hooks.append(hook)
