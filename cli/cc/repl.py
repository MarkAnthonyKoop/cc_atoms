"""Interactive REPL for conversation mode."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .conversation import Conversation
from .config.settings import Settings
from .session.manager import SessionManager
from .hooks.hooks import HooksManager, HookEvent
from .ui.renderer import Renderer
from .ui.prompt import InputPrompt


class REPL:
    """Interactive Read-Eval-Print Loop for Claude conversations."""

    # Built-in slash commands
    SLASH_COMMANDS = {
        "help": "Show help information",
        "clear": "Clear conversation history",
        "compact": "Compact conversation to reduce tokens",
        "config": "View or modify configuration",
        "cost": "Show token usage and cost",
        "doctor": "Check system health and configuration",
        "exit": "Exit the REPL",
        "init": "Initialize project configuration",
        "memory": "Show memory/context information",
        "model": "View or change the model",
        "permissions": "View or modify permissions",
        "quit": "Exit the REPL",
        "review": "Review code changes",
        "status": "Show session status",
        "terminal-setup": "Show terminal setup instructions",
        "vim": "Toggle vim mode",
        "bug": "Report a bug",
        "hooks": "Show configured hooks",
        "sessions": "List recent sessions",
    }

    def __init__(
        self,
        conversation: Conversation,
        settings: Settings,
        session_manager: SessionManager,
        renderer: Renderer,
        hooks_manager: Optional[HooksManager] = None,
        custom_commands: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize REPL with dependencies.

        Args:
            conversation: Conversation manager
            settings: Settings manager
            session_manager: Session manager
            renderer: Output renderer
            hooks_manager: Hooks manager (optional)
            custom_commands: Custom slash commands (optional)
        """
        self.conversation = conversation
        self.settings = settings
        self.session_manager = session_manager
        self.renderer = renderer
        self.hooks_manager = hooks_manager or HooksManager()

        # Set up input prompt
        self.prompt = InputPrompt(multiline=True)
        self.prompt.set_commands(list(self.SLASH_COMMANDS.keys()))

        # Custom commands from .claude/commands/ or .cc/commands/
        self._custom_commands: Dict[str, str] = custom_commands or {}
        if not custom_commands:
            self._load_custom_commands()

        # Add custom commands to prompt completion
        if self._custom_commands:
            self.prompt.set_commands(
                list(self.SLASH_COMMANDS.keys()) + list(self._custom_commands.keys())
            )

        # State
        self._running = False
        self._vim_mode = False

    def _load_custom_commands(self) -> None:
        """Load custom commands from .claude/commands/ or .cc/commands/ directory."""
        command_dirs = [
            Path.cwd() / ".claude" / "commands",
            Path.cwd() / ".cc" / "commands",
        ]
        for commands_dir in command_dirs:
            if commands_dir.exists():
                for cmd_file in commands_dir.glob("*.md"):
                    cmd_name = cmd_file.stem
                    try:
                        content = cmd_file.read_text()
                        self._custom_commands[cmd_name] = content
                    except Exception:
                        pass  # Skip invalid command files

    async def run(self) -> int:
        """Run the interactive REPL loop.

        Returns:
            Exit code
        """
        self._running = True
        self._show_welcome()

        while self._running:
            try:
                user_input = await self._get_input()
                if not user_input:
                    continue

                should_continue = await self.process_input(user_input)
                if not should_continue:
                    break

            except EOFError:
                # Ctrl+D
                self.renderer.newline()
                break
            except KeyboardInterrupt:
                # Ctrl+C during input - just show new prompt
                self.renderer.newline()
                continue

        return 0

    async def _get_input(self) -> str:
        """Get user input.

        Returns:
            User input string
        """
        try:
            prompt_str = "> "
            return await self.prompt.get_input(prompt_str)
        except EOFError:
            raise
        except KeyboardInterrupt:
            raise

    def _show_welcome(self) -> None:
        """Show welcome message."""
        self.renderer.dim(f"CC CLI v0.1.0 - Type /help for commands, /exit to quit")
        self.renderer.dim(f"Session: {self.conversation.session_id[:8]}...")
        self.renderer.dim(f"Model: {self.conversation.api_client.model}")
        self.renderer.newline()

    async def process_input(self, user_input: str) -> bool:
        """Process a single user input.

        Args:
            user_input: Raw user input string

        Returns:
            True to continue, False to exit
        """
        user_input = user_input.strip()
        if not user_input:
            return True

        # Execute user prompt submit hook
        if self.hooks_manager.has_hooks(HookEvent.USER_PROMPT_SUBMIT):
            results = await self.hooks_manager.execute(
                HookEvent.USER_PROMPT_SUBMIT,
                {"prompt": user_input}
            )
            # Check if hook wants to block
            for result in results:
                if result.should_block:
                    self.renderer.warning(f"Prompt blocked by hook: {result.output}")
                    return True

        # Handle slash commands
        if user_input.startswith("/"):
            return await self.handle_slash_command(user_input[1:])

        # Send message to Claude
        try:
            await self._send_message(user_input)
        except KeyboardInterrupt:
            # Ctrl+C during response - stop streaming
            self.renderer.stream_end()
            self.renderer.dim("\n(interrupted)")
        except Exception as e:
            self.renderer.error(str(e))

        return True

    async def _send_message(self, content: str) -> None:
        """Send a message to Claude and stream the response.

        Args:
            content: Message content
        """
        self.renderer.newline()

        async for event in self.conversation.send_message(content):
            event_type = event.get("type")

            if event_type == "text":
                text = event.get("text", "")
                self.renderer.stream_text(text)

            elif event_type == "tool_use":
                tool_name = event.get("tool_name", "")
                tool_input = event.get("tool_input", {})
                self.renderer.stream_end()
                self.renderer.tool_use_start(
                    tool_name,
                    self._format_tool_input(tool_name, tool_input)
                )

            elif event_type == "tool_executing":
                tool_name = event.get("tool_name", "")
                self.renderer.dim(f"  Executing {tool_name}...")

            elif event_type == "tool_result":
                tool_name = event.get("tool_name", "")
                result = event.get("result", "")
                is_error = event.get("is_error", False)

                if is_error:
                    self.renderer.error(f"  {result[:200]}")
                else:
                    # Show truncated result
                    preview = result[:100].replace("\n", " ")
                    if len(result) > 100:
                        preview += "..."
                    self.renderer.dim(f"  {preview}")

                self.renderer.newline()

            elif event_type == "stop":
                self.renderer.stream_end()

        self.renderer.newline()

    def _format_tool_input(self, tool_name: str, tool_input: dict) -> str:
        """Format tool input for display.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Formatted string
        """
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            return cmd[:80] + ("..." if len(cmd) > 80 else "")
        elif tool_name in ("Read", "Write", "Edit"):
            return tool_input.get("file_path", "")[:60]
        elif tool_name == "Glob":
            return tool_input.get("pattern", "")
        elif tool_name == "Grep":
            return tool_input.get("pattern", "")[:40]
        else:
            return ""

    async def handle_slash_command(self, command: str) -> bool:
        """Handle slash command input.

        Args:
            command: Command string (without leading /)

        Returns:
            True to continue, False to exit
        """
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("exit", "quit"):
            self.renderer.dim("Goodbye!")
            return False

        elif cmd == "help":
            self._show_help()

        elif cmd == "clear":
            self.conversation.clear()
            self.renderer.success("Conversation cleared.")

        elif cmd == "compact":
            self.conversation.compact()
            self.renderer.success("Conversation compacted.")

        elif cmd == "cost":
            self._show_cost()

        elif cmd == "status":
            self._show_status()

        elif cmd == "model":
            if args:
                self.conversation.api_client.set_model(args)
                self.renderer.success(f"Model changed to: {self.conversation.api_client.model}")
            else:
                self.renderer.text(f"Current model: {self.conversation.api_client.model}")

        elif cmd == "config":
            self._show_config(args)

        elif cmd == "doctor":
            await self._run_doctor()

        elif cmd == "init":
            self._run_init()

        elif cmd == "memory":
            self._show_memory()

        elif cmd == "permissions":
            self._show_permissions(args)

        elif cmd == "review":
            await self._run_review()

        elif cmd == "terminal-setup":
            self._show_terminal_setup()

        elif cmd == "vim":
            self._toggle_vim()

        elif cmd == "bug":
            self.renderer.text("Report bugs at: https://github.com/anthropics/claude-code/issues")

        elif cmd == "hooks":
            self._show_hooks()

        elif cmd == "sessions":
            self._show_sessions()

        elif cmd in self._custom_commands:
            # Execute custom command
            prompt = self._custom_commands[cmd]
            if args:
                prompt = prompt.replace("$ARGS", args)
                prompt = prompt.replace("{{ARGS}}", args)
            await self._send_message(prompt)

        else:
            self.renderer.warning(f"Unknown command: /{cmd}")
            self.renderer.dim("Type /help for available commands.")

        return True

    def _show_help(self) -> None:
        """Show help information."""
        self.renderer.text("Available commands:\n")
        for cmd, desc in sorted(self.SLASH_COMMANDS.items()):
            self.renderer.text(f"  /{cmd:16} - {desc}")

        # Show custom commands
        if self._custom_commands:
            self.renderer.newline()
            self.renderer.text("Custom commands:")
            for cmd in sorted(self._custom_commands.keys()):
                self.renderer.text(f"  /{cmd}")

        self.renderer.newline()
        self.renderer.dim("Keyboard shortcuts:")
        self.renderer.dim("  Ctrl+C      - Cancel current operation")
        self.renderer.dim("  Ctrl+D      - Exit (same as /exit)")
        self.renderer.dim("  Esc+Enter   - Submit multiline input")

    def _show_cost(self) -> None:
        """Show token usage and cost."""
        usage = self.conversation.token_count
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cache_creation = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)

        # Cost estimates (Claude 3.5 Sonnet pricing)
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        total_cost = input_cost + output_cost

        self.renderer.text("Token Usage:")
        self.renderer.text(f"  Input tokens:  {input_tokens:,}")
        self.renderer.text(f"  Output tokens: {output_tokens:,}")
        self.renderer.text(f"  Total tokens:  {total_tokens:,}")
        if cache_creation or cache_read:
            self.renderer.text(f"  Cache creation: {cache_creation:,}")
            self.renderer.text(f"  Cache read:     {cache_read:,}")
        self.renderer.newline()
        self.renderer.text(f"Estimated cost: ${total_cost:.4f}")

    def _show_status(self) -> None:
        """Show session status."""
        self.renderer.text("Session Status:")
        self.renderer.text(f"  Session ID: {self.conversation.session_id}")
        self.renderer.text(f"  Messages:   {self.conversation.message_count}")
        self.renderer.text(f"  Model:      {self.conversation.api_client.model}")
        self.renderer.text(f"  CWD:        {os.getcwd()}")

        # Show CLAUDE.md status
        claude_md = Path.cwd() / "CLAUDE.md"
        if claude_md.exists():
            self.renderer.text(f"  CLAUDE.md:  Found")
        else:
            self.renderer.dim(f"  CLAUDE.md:  Not found")

        # Show .cc directory status
        cc_dir = Path.cwd() / ".cc"
        if cc_dir.exists():
            self.renderer.text(f"  .cc/:       Found")
        else:
            self.renderer.dim(f"  .cc/:       Not found")

    def _show_config(self, args: str) -> None:
        """Show or modify configuration.

        Args:
            args: Optional config key or key=value
        """
        if not args:
            # Show all config
            self.renderer.text("Configuration:")
            for key, value in self.settings.all().items():
                self.renderer.text(f"  {key}: {value}")
        elif "=" in args:
            # Set config
            key, value = args.split("=", 1)
            self.settings.set(key.strip(), value.strip())
            self.renderer.success(f"Set {key.strip()} = {value.strip()}")
        else:
            # Get specific config
            value = self.settings.get(args.strip())
            self.renderer.text(f"{args.strip()}: {value}")

    async def _run_doctor(self) -> None:
        """Run health check."""
        self.renderer.text("Running health check...\n")

        checks = []

        # Check API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            checks.append(("API Key", True, "Set"))
        else:
            checks.append(("API Key", False, "Not set (ANTHROPIC_API_KEY)"))

        # Check config directory
        config_dir = Path.home() / ".cc"
        if config_dir.exists():
            checks.append(("Config Directory", True, str(config_dir)))
        else:
            checks.append(("Config Directory", False, "Not created yet"))

        # Check for CLAUDE.md
        claude_md = Path.cwd() / "CLAUDE.md"
        if claude_md.exists():
            checks.append(("CLAUDE.md", True, "Found in current directory"))
        else:
            checks.append(("CLAUDE.md", True, "Not present (optional)"))

        # Check for .cc directory
        cc_dir = Path.cwd() / ".cc"
        if cc_dir.exists():
            checks.append((".cc Directory", True, "Found"))
        else:
            checks.append((".cc Directory", True, "Not present (optional)"))

        # Check for .claude directory (also valid)
        claude_dir = Path.cwd() / ".claude"
        if claude_dir.exists():
            checks.append((".claude Directory", True, "Found"))

        # Check hooks configuration
        hooks_config = self.settings.get("hooks", {})
        if hooks_config:
            hook_count = sum(len(v) if isinstance(v, list) else 1 for v in hooks_config.values())
            checks.append(("Hooks", True, f"{hook_count} hook(s) configured"))
        else:
            checks.append(("Hooks", True, "No hooks configured (optional)"))

        # Check MCP servers
        mcp_servers = self.settings.get("mcpServers", {})
        if mcp_servers:
            checks.append(("MCP Servers", True, f"{len(mcp_servers)} server(s) configured"))
        else:
            checks.append(("MCP Servers", True, "No MCP servers configured (optional)"))

        # Display results
        for name, passed, message in checks:
            status = "OK" if passed else "FAIL"
            if passed:
                self.renderer.text(f"  [{status}] {name}: {message}")
            else:
                self.renderer.warning(f"  [{status}] {name}: {message}")

    def _run_init(self) -> None:
        """Initialize project configuration."""
        cc_dir = Path.cwd() / ".cc"
        commands_dir = cc_dir / "commands"

        if not cc_dir.exists():
            cc_dir.mkdir()
            self.renderer.success(f"Created {cc_dir}")

        if not commands_dir.exists():
            commands_dir.mkdir()
            self.renderer.success(f"Created {commands_dir}")

        settings_file = cc_dir / "settings.local.json"
        if not settings_file.exists():
            settings_file.write_text("{}\n")
            self.renderer.success(f"Created {settings_file}")

        claude_md = Path.cwd() / "CLAUDE.md"
        if not claude_md.exists():
            claude_md.write_text("# Project Instructions\n\nAdd project-specific instructions here.\n")
            self.renderer.success(f"Created {claude_md}")

        self.renderer.text("\nProject initialized. Edit CLAUDE.md to add custom instructions.")

    def _show_memory(self) -> None:
        """Show memory/context information."""
        self.renderer.text("Memory/Context:")
        self.renderer.text(f"  Messages in context: {self.conversation.message_count}")
        self.renderer.text(f"  Total tokens used: {self.conversation.token_count.get('total_tokens', 0):,}")

        # Show CLAUDE.md if present
        claude_md = Path.cwd() / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            lines = content.splitlines()
            self.renderer.newline()
            self.renderer.text(f"CLAUDE.md ({len(lines)} lines):")
            for line in lines[:5]:
                self.renderer.dim(f"  {line[:60]}")
            if len(lines) > 5:
                self.renderer.dim(f"  ... ({len(lines) - 5} more lines)")

    def _show_permissions(self, args: str) -> None:
        """Show or modify permissions.

        Args:
            args: Optional permission command
        """
        if not args:
            self.renderer.text("Permission Modes:")
            self.renderer.text("  default      - Ask for each tool use")
            self.renderer.text("  dontAsk      - Don't ask for confirmations")
            self.renderer.text("  acceptEdits  - Auto-accept file edits")
            self.renderer.text("  plan         - Read-only mode")
            self.renderer.newline()

            mode = self.settings.get("permissions.defaultMode", "default")
            self.renderer.text(f"Current mode: {mode}")
        else:
            if args in ("default", "dontAsk", "acceptEdits", "plan"):
                self.settings.set("permissions.defaultMode", args)
                self.renderer.success(f"Permission mode set to: {args}")
            else:
                self.renderer.error(f"Unknown permission mode: {args}")

    async def _run_review(self) -> None:
        """Run code review."""
        # Check for uncommitted changes
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )
            if result.stdout.strip():
                self.renderer.text("Uncommitted changes:")
                self.renderer.dim(result.stdout[:500])

                # Send to Claude for review
                await self._send_message(
                    "Please review the following git diff and provide feedback:\n\n"
                    f"```\n{result.stdout[:4000]}\n```"
                )
            else:
                self.renderer.text("No uncommitted changes to review.")
        except Exception as e:
            self.renderer.error(f"Failed to get git diff: {e}")

    def _show_terminal_setup(self) -> None:
        """Show terminal setup instructions."""
        self.renderer.text("Terminal Setup")
        self.renderer.newline()
        self.renderer.text("For best experience, ensure your terminal supports:")
        self.renderer.text("  - Unicode characters")
        self.renderer.text("  - ANSI color codes")
        self.renderer.text("  - 256 colors or true color")
        self.renderer.newline()
        self.renderer.text("Recommended terminals:")
        self.renderer.text("  - iTerm2 (macOS)")
        self.renderer.text("  - Windows Terminal (Windows)")
        self.renderer.text("  - Alacritty, Kitty (cross-platform)")
        self.renderer.newline()
        self.renderer.text("Shell integration:")
        self.renderer.dim("  Add to ~/.bashrc or ~/.zshrc:")
        self.renderer.dim("    export ANTHROPIC_API_KEY='your-api-key'")

    def _toggle_vim(self) -> None:
        """Toggle vim mode."""
        self._vim_mode = not self._vim_mode
        if self._vim_mode:
            self.renderer.success("Vim mode enabled")
            self.renderer.dim("  Press 'i' to enter insert mode, Esc to exit")
        else:
            self.renderer.success("Vim mode disabled")

    def _show_hooks(self) -> None:
        """Show configured hooks."""
        hooks_config = self.settings.get("hooks", {})

        if not hooks_config:
            self.renderer.text("No hooks configured.")
            self.renderer.newline()
            self.renderer.dim("To configure hooks, add to settings.json:")
            self.renderer.dim('  "hooks": {')
            self.renderer.dim('    "PreToolUse": [{"command": "...", "matchers": ["Bash"]}],')
            self.renderer.dim('    "PostToolUse": [...],')
            self.renderer.dim('    "UserPromptSubmit": [...]')
            self.renderer.dim('  }')
            return

        self.renderer.text("Configured Hooks:")
        for event_name, hooks in hooks_config.items():
            self.renderer.text(f"\n  {event_name}:")
            if isinstance(hooks, list):
                for hook in hooks:
                    if isinstance(hook, dict):
                        cmd = hook.get("command", "")
                        matchers = hook.get("matchers", [])
                        self.renderer.dim(f"    - {cmd}")
                        if matchers:
                            self.renderer.dim(f"      matchers: {', '.join(matchers)}")
                    else:
                        self.renderer.dim(f"    - {hook}")

    def _show_sessions(self) -> None:
        """Show recent sessions."""
        sessions = self.session_manager.list_sessions()

        if not sessions:
            self.renderer.text("No sessions found.")
            return

        self.renderer.text("Recent Sessions:")
        for session in sessions[:10]:  # Show last 10
            current = " (current)" if session.id == self.conversation.session_id else ""
            self.renderer.text(
                f"  {session.id[:8]}... - {session.last_modified} "
                f"({session.message_count} messages){current}"
            )

        if len(sessions) > 10:
            self.renderer.dim(f"\n  ... and {len(sessions) - 10} more sessions")
