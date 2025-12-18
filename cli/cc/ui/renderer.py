"""Output rendering with markdown support."""

import sys
from typing import Optional, TextIO

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from .colors import Colors, colorize, supports_color


class Renderer:
    """Renders output to terminal with optional markdown support."""

    def __init__(
        self,
        console: Optional[Console] = None,
        use_markdown: bool = True,
        stream: Optional[TextIO] = None,
    ) -> None:
        """Initialize renderer.

        Args:
            console: Rich console instance (created if not provided)
            use_markdown: Whether to render markdown
            stream: Output stream (defaults to stdout)
        """
        self.use_markdown = use_markdown
        self.stream = stream or sys.stdout
        self._console = console or Console(force_terminal=supports_color())
        self._streaming_text = ""

    def markdown(self, text: str) -> None:
        """Render markdown text.

        Args:
            text: Markdown text to render
        """
        if self.use_markdown:
            md = Markdown(text)
            self._console.print(md)
        else:
            self._console.print(text)

    def text(self, text: str, end: str = "\n") -> None:
        """Render plain text.

        Args:
            text: Text to render
            end: String to append at end
        """
        self._console.print(text, end=end)

    def code(self, code: str, language: str = "") -> None:
        """Render code block with syntax highlighting.

        Args:
            code: Code to render
            language: Programming language for syntax highlighting
        """
        if language and self.use_markdown:
            syntax = Syntax(code, language, theme="monokai", line_numbers=False)
            self._console.print(syntax)
        else:
            self._console.print(code)

    def error(self, message: str) -> None:
        """Render error message.

        Args:
            message: Error message to display
        """
        text = Text(f"Error: {message}", style="bold red")
        # Rich Console doesn't support file parameter in the same way
        # So we just print to the console (which can be configured to stderr if needed)
        self._console.print(text, style="bold red")

    def warning(self, message: str) -> None:
        """Render warning message.

        Args:
            message: Warning message to display
        """
        text = Text(f"Warning: {message}", style="yellow")
        self._console.print(text)

    def success(self, message: str) -> None:
        """Render success message.

        Args:
            message: Success message to display
        """
        text = Text(message, style="bold green")
        self._console.print(text)

    def info(self, message: str) -> None:
        """Render info message.

        Args:
            message: Info message to display
        """
        text = Text(message, style="blue")
        self._console.print(text)

    def dim(self, message: str) -> None:
        """Render dimmed text.

        Args:
            message: Message to display
        """
        text = Text(message, style="dim")
        self._console.print(text)

    def panel(self, content: str, title: Optional[str] = None) -> None:
        """Render content in a panel.

        Args:
            content: Content to display in panel
            title: Optional panel title
        """
        panel = Panel(content, title=title)
        self._console.print(panel)

    def stream_text(self, text: str) -> None:
        """Stream text without newline (for streaming responses).

        Args:
            text: Text chunk to stream
        """
        self._streaming_text += text
        self._console.print(text, end="")

    def stream_end(self) -> None:
        """End streaming and reset state."""
        if self._streaming_text:
            self._console.print()  # Add newline
            self._streaming_text = ""

    def tool_use_start(self, tool_name: str, description: Optional[str] = None) -> None:
        """Render tool use start indicator.

        Args:
            tool_name: Name of the tool being used
            description: Optional description of the tool operation
        """
        tool_text = Text()
        tool_text.append("  ", style="dim")
        tool_text.append(tool_name, style="bold cyan")
        if description:
            tool_text.append(f" {description}", style="dim")
        self._console.print(tool_text)

    def tool_use_result(self, result: str, success: bool = True) -> None:
        """Render tool use result.

        Args:
            result: Tool result text
            success: Whether the tool succeeded
        """
        style = "green" if success else "red"
        text = Text()
        text.append("  → ", style=style)
        # Truncate long results
        if len(result) > 500:
            result = result[:500] + "..."
        text.append(result, style="dim")
        self._console.print(text)

    def prompt_indicator(self, cwd: Optional[str] = None) -> None:
        """Render the input prompt indicator.

        Args:
            cwd: Current working directory to display
        """
        if cwd:
            self._console.print(f"[dim]{cwd}[/dim]")
        self._console.print("[bold blue]>[/bold blue] ", end="")

    def clear(self) -> None:
        """Clear the console."""
        self._console.clear()

    def rule(self, title: str = "") -> None:
        """Render a horizontal rule.

        Args:
            title: Optional title for the rule
        """
        self._console.rule(title)

    def newline(self, count: int = 1) -> None:
        """Print newlines.

        Args:
            count: Number of newlines
        """
        for _ in range(count):
            self._console.print()
