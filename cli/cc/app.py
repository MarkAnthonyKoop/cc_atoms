"""Application context and integration for CC CLI.

This module provides the central application context that integrates
all components: settings, session management, API client, tool execution,
hooks, and the REPL.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .api import APIClient
from .config.settings import Settings
from .config.paths import (
    find_all_claude_md,
    get_local_config_dir,
    ensure_config_dirs,
)
from .session.manager import SessionManager
from .tools import ToolExecutor, PermissionChecker, ToolRegistry
from .hooks.hooks import HooksManager, HookEvent
from .ui.renderer import Renderer


@dataclass
class AppConfig:
    """Application configuration from CLI arguments."""
    # Mode options
    prompt: Optional[str] = None
    continue_session: bool = False
    resume_session: Optional[str] = None
    print_mode: bool = False

    # Output options
    output_format: str = "text"
    input_format: str = "text"
    verbose: bool = False
    no_markdown: bool = False

    # Model options
    model: Optional[str] = None
    max_tokens: Optional[int] = None

    # Permission options
    skip_permissions: bool = False
    allowed_tools: List[str] = field(default_factory=list)
    disallowed_tools: List[str] = field(default_factory=list)

    # System prompt options
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None

    # Working directory
    cwd: Optional[str] = None

    # MCP
    mcp_config: Optional[str] = None


class Application:
    """Central application context integrating all components.

    This class provides dependency injection and lifecycle management
    for all application components.
    """

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        """Initialize application with configuration.

        Args:
            config: Application configuration (uses defaults if None)
        """
        self.config = config or AppConfig()

        # Ensure config directories exist
        ensure_config_dirs()

        # Set working directory if specified
        if self.config.cwd:
            os.chdir(self.config.cwd)

        self._project_path = Path.cwd()

        # Initialize components (lazy loading pattern)
        self._settings: Optional[Settings] = None
        self._session_manager: Optional[SessionManager] = None
        self._api_client: Optional[APIClient] = None
        self._tool_executor: Optional[ToolExecutor] = None
        self._hooks_manager: Optional[HooksManager] = None
        self._renderer: Optional[Renderer] = None

    @property
    def settings(self) -> Settings:
        """Get settings manager, lazily initialized."""
        if self._settings is None:
            self._settings = Settings(project_path=self._project_path)
            self._settings.load()
            self._apply_cli_config_to_settings()
        return self._settings

    def _apply_cli_config_to_settings(self) -> None:
        """Apply CLI configuration overrides to settings."""
        if self._settings is None:
            return

        if self.config.model:
            self._settings.set("model", self.config.model, scope="cli")
        if self.config.max_tokens:
            self._settings.set("maxTokens", self.config.max_tokens, scope="cli")
        if self.config.skip_permissions:
            self._settings.set("skipPermissions", True, scope="cli")
        if self.config.allowed_tools:
            self._settings.set("allowedTools", self.config.allowed_tools, scope="cli")
        if self.config.disallowed_tools:
            self._settings.set("disallowedTools", self.config.disallowed_tools, scope="cli")

    @property
    def renderer(self) -> Renderer:
        """Get output renderer, lazily initialized."""
        if self._renderer is None:
            self._renderer = Renderer(use_markdown=not self.config.no_markdown)
        return self._renderer

    @property
    def session_manager(self) -> SessionManager:
        """Get session manager, lazily initialized."""
        if self._session_manager is None:
            self._session_manager = SessionManager(self._project_path)
        return self._session_manager

    @property
    def hooks_manager(self) -> HooksManager:
        """Get hooks manager, lazily initialized."""
        if self._hooks_manager is None:
            self._hooks_manager = HooksManager()
            # Load hooks from settings
            self._hooks_manager.load_from_settings(self.settings.all())
        return self._hooks_manager

    @property
    def tool_executor(self) -> ToolExecutor:
        """Get tool executor, lazily initialized."""
        if self._tool_executor is None:
            # Create permission checker
            permission_checker = PermissionChecker(
                allow_patterns=self.settings.get("allowedTools", []),
                deny_patterns=self.settings.get("disallowedTools", []),
                skip_permissions=self.settings.get("skipPermissions", False),
            )

            # Create tool registry
            registry = ToolRegistry()
            registry.set_cwd(str(self._project_path))

            # Create executor
            self._tool_executor = ToolExecutor(
                registry=registry,
                permission_checker=permission_checker,
            )

            # Connect hooks to tool executor
            self._connect_hooks_to_executor()

        return self._tool_executor

    def _connect_hooks_to_executor(self) -> None:
        """Connect hooks manager to tool executor."""
        if self._tool_executor is None:
            return

        async def pre_tool_hook(tool_name: str, tool_input: Dict[str, Any], tool_id: str) -> None:
            """Execute pre-tool hooks."""
            if self.hooks_manager.has_hooks(HookEvent.PRE_TOOL_USE):
                results = await self.hooks_manager.execute(
                    HookEvent.PRE_TOOL_USE,
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_id": tool_id,
                    }
                )
                # Check for blocking hooks
                for result in results:
                    if result.should_block:
                        raise PermissionError(f"Tool blocked by hook: {result.output}")

        async def post_tool_hook(
            tool_name: str,
            tool_input: Dict[str, Any],
            tool_id: str,
            result: Any
        ) -> None:
            """Execute post-tool hooks."""
            if self.hooks_manager.has_hooks(HookEvent.POST_TOOL_USE):
                await self.hooks_manager.execute(
                    HookEvent.POST_TOOL_USE,
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_id": tool_id,
                        "result": str(result),
                    }
                )

        self._tool_executor.add_pre_hook(pre_tool_hook)
        self._tool_executor.add_post_hook(post_tool_hook)

    @property
    def api_client(self) -> APIClient:
        """Get API client, lazily initialized."""
        if self._api_client is None:
            model = self.settings.get("model", "claude-sonnet-4-5-20250929")
            self._api_client = APIClient(model=model)
        return self._api_client

    def get_system_prompt(self) -> Optional[str]:
        """Build the system prompt from various sources.

        Combines:
        1. CLAUDE.md files (from cwd up to root)
        2. Custom system prompt from CLI
        3. Appended system prompt from CLI

        Returns:
            Combined system prompt or None
        """
        parts: List[str] = []

        # Load all CLAUDE.md files (closest first, then up the tree)
        claude_md_files = find_all_claude_md(self._project_path)
        for claude_md_path in reversed(claude_md_files):  # Process from root down
            try:
                content = claude_md_path.read_text()
                relative_path = claude_md_path.relative_to(Path.home()) \
                    if claude_md_path.is_relative_to(Path.home()) else claude_md_path
                parts.append(f"# Instructions from {relative_path}\n\n{content}")
            except Exception:
                pass

        # Add custom system prompt
        if self.config.system_prompt:
            parts.append(self.config.system_prompt)

        # Add appended system prompt
        if self.config.append_system_prompt:
            parts.append(self.config.append_system_prompt)

        if parts:
            return "\n\n".join(parts)
        return None

    def get_session_id(self) -> Optional[str]:
        """Determine session ID based on configuration.

        Returns:
            Session ID to resume, or None for new session
        """
        if self.config.resume_session:
            return self.config.resume_session
        elif self.config.continue_session:
            return self.session_manager.get_recent()
        return None

    def get_mcp_servers(self) -> Dict[str, Any]:
        """Get MCP server configuration.

        Returns:
            Dictionary of MCP server configurations
        """
        # Load from settings
        mcp_servers = self.settings.get("mcpServers", {})

        # Load from separate config file if specified
        if self.config.mcp_config:
            import json
            try:
                mcp_path = Path(self.config.mcp_config)
                if mcp_path.exists():
                    with open(mcp_path, "r") as f:
                        file_config = json.load(f)
                        mcp_servers.update(file_config.get("mcpServers", {}))
            except (json.JSONDecodeError, IOError):
                pass

        return mcp_servers

    def get_custom_commands(self) -> Dict[str, str]:
        """Load custom slash commands from .claude/commands/ or .cc/commands/.

        Returns:
            Dictionary mapping command name to command content
        """
        commands: Dict[str, str] = {}

        # Check both .claude and .cc directories
        command_dirs = [
            self._project_path / ".claude" / "commands",
            self._project_path / ".cc" / "commands",
        ]

        for commands_dir in command_dirs:
            if commands_dir.exists():
                for cmd_file in commands_dir.glob("*.md"):
                    cmd_name = cmd_file.stem
                    try:
                        content = cmd_file.read_text()
                        commands[cmd_name] = content
                    except Exception:
                        pass

        return commands


def create_app_from_args(args: Any) -> Application:
    """Create Application instance from parsed CLI arguments.

    Args:
        args: argparse.Namespace from CLI argument parser

    Returns:
        Configured Application instance
    """
    config = AppConfig(
        prompt=getattr(args, 'prompt', None),
        continue_session=getattr(args, 'continue_session', False),
        resume_session=getattr(args, 'resume', None),
        print_mode=getattr(args, 'print_mode', False),
        output_format=getattr(args, 'output_format', 'text'),
        input_format=getattr(args, 'input_format', 'text'),
        verbose=getattr(args, 'verbose', False),
        no_markdown=getattr(args, 'no_markdown', False),
        model=getattr(args, 'model', None),
        max_tokens=getattr(args, 'max_tokens', None),
        skip_permissions=getattr(args, 'dangerously_skip_permissions', False),
        allowed_tools=getattr(args, 'allowedTools', None) or [],
        disallowed_tools=getattr(args, 'disallowedTools', None) or [],
        system_prompt=getattr(args, 'system_prompt', None),
        append_system_prompt=getattr(args, 'append_system_prompt', None),
        cwd=getattr(args, 'cwd', None),
        mcp_config=getattr(args, 'mcp_config', None),
    )

    return Application(config)
