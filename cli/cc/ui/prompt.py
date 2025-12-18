"""Input prompt handling with history and completion."""

import os
from pathlib import Path
from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style


class SlashCommandCompleter(Completer):
    """Completer for slash commands."""

    def __init__(self, commands: Optional[List[str]] = None) -> None:
        """Initialize with list of available commands.

        Args:
            commands: List of slash command names (without leading /)
        """
        self.commands = commands or []

    def get_completions(self, document, complete_event):
        """Generate completions for slash commands."""
        text = document.text_before_cursor

        # Only complete at start of line with /
        if text.startswith("/"):
            word = text[1:]  # Remove leading /
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=f"/{cmd}",
                        display_meta="command",
                    )

    def set_commands(self, commands: List[str]) -> None:
        """Update available commands.

        Args:
            commands: New list of command names
        """
        self.commands = commands


class InputPrompt:
    """Handles user input with history, completion, and key bindings."""

    # Default slash commands
    DEFAULT_COMMANDS = [
        "help",
        "clear",
        "compact",
        "config",
        "cost",
        "doctor",
        "init",
        "memory",
        "model",
        "permissions",
        "review",
        "status",
        "terminal-setup",
        "vim",
        "bug",
        "quit",
        "exit",
    ]

    def __init__(
        self,
        history_file: Optional[str] = None,
        multiline: bool = True,
    ) -> None:
        """Initialize input prompt.

        Args:
            history_file: Path to history file (uses in-memory if not provided)
            multiline: Whether to support multiline input
        """
        # Set up history
        if history_file:
            history_path = Path(history_file)
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(history_path))
        else:
            history = InMemoryHistory()

        # Set up completer
        self.completer = SlashCommandCompleter(self.DEFAULT_COMMANDS)

        # Set up style
        style = Style.from_dict({
            "prompt": "bold blue",
            "input": "",
        })

        # Set up key bindings
        bindings = KeyBindings()

        @bindings.add("escape", "enter")
        def _(event):
            """Submit on Escape+Enter for multiline mode."""
            event.current_buffer.validate_and_handle()

        # Create session
        self.session: PromptSession = PromptSession(
            history=history,
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            style=style,
            key_bindings=bindings,
            multiline=multiline,
            prompt_continuation=lambda width, line_number, wrap_count: "... ",
        )

        self.multiline = multiline

    async def get_input(self, prompt: str = "> ") -> str:
        """Get user input with prompt.

        Args:
            prompt: Prompt string to display

        Returns:
            User input string

        Raises:
            EOFError: If user presses Ctrl+D
            KeyboardInterrupt: If user presses Ctrl+C
        """
        try:
            result = await self.session.prompt_async(prompt)
            return result.strip()
        except EOFError:
            raise
        except KeyboardInterrupt:
            raise

    def get_input_sync(self, prompt: str = "> ") -> str:
        """Get user input synchronously.

        Args:
            prompt: Prompt string to display

        Returns:
            User input string
        """
        result = self.session.prompt(prompt)
        return result.strip()

    def set_commands(self, commands: List[str]) -> None:
        """Set available slash commands for completion.

        Args:
            commands: List of command names (without leading /)
        """
        self.completer.set_commands(commands)

    def add_to_history(self, text: str) -> None:
        """Add text to history.

        Args:
            text: Text to add to history
        """
        if text and text.strip():
            self.session.history.append_string(text)


def get_confirmation(prompt: str = "Continue?", default: bool = True) -> bool:
    """Get yes/no confirmation from user.

    Args:
        prompt: Prompt to display
        default: Default value if user just presses Enter

    Returns:
        True for yes, False for no
    """
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(prompt + suffix).strip().lower()

    if not response:
        return default

    return response in ("y", "yes", "true", "1")


def get_choice(prompt: str, choices: List[str], default: int = 0) -> int:
    """Get user choice from a list of options.

    Args:
        prompt: Prompt to display
        choices: List of choices
        default: Default choice index

    Returns:
        Index of selected choice
    """
    print(prompt)
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {choice}")

    while True:
        response = input(f"Enter choice [1-{len(choices)}] (default: {default + 1}): ").strip()

        if not response:
            return default

        try:
            choice = int(response) - 1
            if 0 <= choice < len(choices):
                return choice
        except ValueError:
            pass

        print(f"Invalid choice. Please enter a number between 1 and {len(choices)}.")
