"""CLI entry point and argument parsing for CC CLI."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all options."""
    parser = argparse.ArgumentParser(
        prog="cc",
        description="CC CLI - A Claude Code CLI clone for interactive AI conversations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cc                     Start interactive REPL
  cc -p "Hello"          One-shot prompt
  cc -c                  Continue last conversation
  cc -r SESSION_ID       Resume specific session
  cc --print             Non-interactive mode

For more information, run 'cc /help' in a session.
        """,
    )

    # Version
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"cc {__version__}",
    )

    # Main mode flags
    mode_group = parser.add_argument_group("Mode Options")
    mode_group.add_argument(
        "-p", "--prompt",
        metavar="PROMPT",
        type=str,
        help="Start with an initial prompt (one-shot mode if --print is used)",
    )
    mode_group.add_argument(
        "-c", "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue the most recent conversation",
    )
    mode_group.add_argument(
        "-r", "--resume",
        metavar="SESSION_ID",
        type=str,
        help="Resume a specific conversation by session ID",
    )
    mode_group.add_argument(
        "--print",
        dest="print_mode",
        action="store_true",
        help="Run in non-interactive print mode",
    )

    # Output format
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="Output format for print mode (default: text)",
    )
    output_group.add_argument(
        "--input-format",
        choices=["text", "stream-json"],
        default="text",
        help="Input format for print mode (default: text)",
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    output_group.add_argument(
        "--no-markdown",
        action="store_true",
        help="Disable markdown rendering in output",
    )

    # Model options
    model_group = parser.add_argument_group("Model Options")
    model_group.add_argument(
        "-m", "--model",
        type=str,
        help="Model to use (e.g., sonnet, opus, haiku, or full model ID)",
    )
    model_group.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum tokens in response",
    )

    # Permission mode
    perm_group = parser.add_argument_group("Permission Options")
    perm_group.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Skip all permission checks (use with caution)",
    )
    perm_group.add_argument(
        "--allowedTools",
        type=str,
        nargs="+",
        help="List of allowed tool patterns",
    )
    perm_group.add_argument(
        "--disallowedTools",
        type=str,
        nargs="+",
        help="List of disallowed tool patterns",
    )

    # System prompt
    parser.add_argument(
        "-s", "--system-prompt",
        type=str,
        help="Add additional system prompt content",
    )
    parser.add_argument(
        "-a", "--append-system-prompt",
        type=str,
        help="Append to the default system prompt",
    )

    # Working directory
    parser.add_argument(
        "-d", "--cwd",
        type=str,
        help="Working directory for the session",
    )

    # MCP configuration
    parser.add_argument(
        "--mcp-config",
        type=str,
        help="Path to MCP configuration file",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        title="Subcommands",
        dest="command",
        metavar="COMMAND",
    )

    # mcp subcommand
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="MCP server management",
    )
    mcp_subparsers = mcp_parser.add_subparsers(
        dest="mcp_command",
        metavar="SUBCOMMAND",
    )
    mcp_subparsers.add_parser("list", help="List MCP servers")
    mcp_add = mcp_subparsers.add_parser("add", help="Add MCP server")
    mcp_add.add_argument("name", help="Server name")
    mcp_add.add_argument("--command", dest="server_command", help="Server command")
    mcp_add.add_argument("--args", nargs="*", help="Server arguments")
    mcp_subparsers.add_parser("remove", help="Remove MCP server")

    # config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        metavar="SUBCOMMAND",
    )
    config_subparsers.add_parser("list", help="List configuration")
    config_set = config_subparsers.add_parser("set", help="Set configuration value")
    config_set.add_argument("key", help="Configuration key")
    config_set.add_argument("value", help="Configuration value")
    config_get = config_subparsers.add_parser("get", help="Get configuration value")
    config_get.add_argument("key", help="Configuration key")

    # sessions subcommand
    sessions_parser = subparsers.add_parser(
        "sessions",
        help="Session management",
    )
    sessions_subparsers = sessions_parser.add_subparsers(
        dest="sessions_command",
        metavar="SUBCOMMAND",
    )
    sessions_subparsers.add_parser("list", help="List sessions")
    sessions_export = sessions_subparsers.add_parser("export", help="Export session")
    sessions_export.add_argument("session_id", nargs="?", help="Session ID to export")
    sessions_delete = sessions_subparsers.add_parser("delete", help="Delete session")
    sessions_delete.add_argument("session_id", help="Session ID to delete")

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the cc command.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Handle subcommands
    if parsed_args.command == "mcp":
        return cmd_mcp(parsed_args)
    elif parsed_args.command == "config":
        return cmd_config(parsed_args)
    elif parsed_args.command == "sessions":
        return cmd_sessions(parsed_args)

    # Set working directory
    if parsed_args.cwd:
        try:
            os.chdir(parsed_args.cwd)
        except OSError as e:
            print(f"Error: Cannot change to directory '{parsed_args.cwd}': {e}", file=sys.stderr)
            return 1

    # Run the main application
    try:
        return asyncio.run(run_app(parsed_args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


async def run_app(args: argparse.Namespace) -> int:
    """Run the main application asynchronously.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from .app import create_app_from_args
    from .repl import REPL
    from .conversation import Conversation

    # Create application context with all integrated components
    app = create_app_from_args(args)

    # Determine session ID
    session_id = app.get_session_id()
    if args.continue_session and session_id is None:
        app.renderer.error("No previous session found to continue.")
        return 1

    # Create conversation with all integrated components
    conversation = Conversation(
        api_client=app.api_client,
        session_manager=app.session_manager,
        system_prompt=app.get_system_prompt(),
        session_id=session_id,
        tool_executor=app.tool_executor,
        skip_permissions=app.settings.get("skipPermissions", False),
        allowed_tools=app.settings.get("allowedTools", []),
        disallowed_tools=app.settings.get("disallowedTools", []),
    )

    # Print mode (non-interactive)
    if args.print_mode:
        if not args.prompt:
            # Read from stdin
            prompt = sys.stdin.read().strip()
            if not prompt:
                app.renderer.error("No prompt provided. Use -p PROMPT or pipe input.")
                return 1
        else:
            prompt = args.prompt

        from .print_mode import PrintMode
        print_mode = PrintMode(
            conversation=conversation,
            output_format=args.output_format,
            input_format=args.input_format,
        )
        return await print_mode.run(prompt)

    # Interactive REPL mode
    repl = REPL(
        conversation=conversation,
        settings=app.settings,
        session_manager=app.session_manager,
        renderer=app.renderer,
        hooks_manager=app.hooks_manager,
        custom_commands=app.get_custom_commands(),
    )

    # If prompt provided, send it first
    if args.prompt:
        await repl.process_input(args.prompt)

    # Run the REPL loop
    return await repl.run()


def cmd_mcp(args: argparse.Namespace) -> int:
    """Handle 'cc mcp' subcommand."""
    from .config.settings import Settings
    import json

    settings = Settings()
    settings.load()

    if args.mcp_command == "list":
        mcp_servers = settings.get("mcpServers", {})
        if not mcp_servers:
            print("No MCP servers configured.")
        else:
            print("MCP servers:")
            for name, config in mcp_servers.items():
                command = config.get("command", "")
                server_args = config.get("args", [])
                print(f"  {name}:")
                print(f"    command: {command}")
                if server_args:
                    print(f"    args: {' '.join(server_args)}")
        return 0
    elif args.mcp_command == "add":
        mcp_servers = settings.get("mcpServers", {})
        mcp_servers[args.name] = {
            "command": args.server_command or "",
            "args": args.args or [],
        }
        settings.set("mcpServers", mcp_servers)
        settings.save()
        print(f"Added MCP server: {args.name}")
        return 0
    elif args.mcp_command == "remove":
        mcp_servers = settings.get("mcpServers", {})
        if args.name in mcp_servers:
            del mcp_servers[args.name]
            settings.set("mcpServers", mcp_servers)
            settings.save()
            print(f"Removed MCP server: {args.name}")
        else:
            print(f"MCP server not found: {args.name}")
            return 1
        return 0
    else:
        print("Usage: cc mcp <list|add|remove>")
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """Handle 'cc config' subcommand."""
    from .config.settings import Settings
    import json

    settings = Settings()
    settings.load()

    if args.config_command == "list":
        print("Configuration:")
        for key, value in sorted(settings.all().items()):
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, indent=2)
                print(f"  {key}:")
                for line in value_str.split("\n"):
                    print(f"    {line}")
            else:
                print(f"  {key}: {value}")
        return 0
    elif args.config_command == "set":
        # Try to parse value as JSON for complex types
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value

        settings.set(args.key, value)
        settings.save()
        print(f"Set {args.key} = {args.value}")
        return 0
    elif args.config_command == "get":
        value = settings.get(args.key)
        if value is not None:
            if isinstance(value, (dict, list)):
                print(f"{args.key}:")
                print(json.dumps(value, indent=2))
            else:
                print(f"{args.key}: {value}")
        else:
            print(f"{args.key}: (not set)")
        return 0
    else:
        print("Usage: cc config <list|set|get>")
        return 1


def cmd_sessions(args: argparse.Namespace) -> int:
    """Handle 'cc sessions' subcommand."""
    from .session.manager import SessionManager
    import json

    session_manager = SessionManager(Path.cwd())

    if args.sessions_command == "list":
        sessions = session_manager.list_sessions()
        if not sessions:
            print("No sessions found.")
        else:
            print("Sessions:")
            for session in sessions:
                print(f"  {session.id[:8]}... - {session.last_modified} ({session.message_count} messages)")
        return 0
    elif args.sessions_command == "export":
        session_id = args.session_id
        if not session_id:
            # Export most recent
            session_id = session_manager.get_recent()
            if not session_id:
                print("No sessions to export.")
                return 1

        try:
            storage = session_manager.load(session_id)
            entries = storage.read()
            print(json.dumps(entries, indent=2))
            return 0
        except FileNotFoundError:
            print(f"Session not found: {session_id}")
            return 1
    elif args.sessions_command == "delete":
        if session_manager.delete(args.session_id):
            print(f"Deleted session: {args.session_id}")
            return 0
        else:
            print(f"Session not found: {args.session_id}")
            return 1
    else:
        print("Usage: cc sessions <list|export|delete>")
        return 1


if __name__ == "__main__":
    sys.exit(main())
