"""Terminal colors and styling."""

from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def colorize(text: str, *styles: str) -> str:
    """Apply color/style codes to text.

    Args:
        text: Text to colorize
        *styles: Color/style codes to apply

    Returns:
        Colorized text with reset at end
    """
    if not styles:
        return text
    return "".join(styles) + text + Colors.RESET


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    Args:
        text: Text potentially containing ANSI codes

    Returns:
        Text without ANSI codes
    """
    import re
    ansi_pattern = re.compile(r'\033\[[0-9;]*m')
    return ansi_pattern.sub('', text)


def supports_color() -> bool:
    """Check if the terminal supports color output.

    Returns:
        True if color is supported
    """
    import os
    import sys

    # Check NO_COLOR environment variable
    if os.environ.get("NO_COLOR"):
        return False

    # Check FORCE_COLOR environment variable
    if os.environ.get("FORCE_COLOR"):
        return True

    # Check if stdout is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Check TERM environment variable
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False

    return True
