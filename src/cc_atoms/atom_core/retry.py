"""Retry logic for network errors, session limits, etc."""
import re
from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

from cc_atoms.config import (
    NETWORK_ERROR_KEYWORDS, NETWORK_RETRY_BASE, NETWORK_RETRY_MAX,
    OTHER_RETRY_BASE, OTHER_RETRY_MAX, SESSION_LIMIT_BUFFER,
    DEFAULT_SESSION_LIMIT_WAIT
)


class RetryManager:
    """
    Handles retry logic with configurable logging.

    By default, prints retry messages to stdout. For embedded/quiet usage,
    pass a custom callback or None to suppress output.
    """

    def __init__(self, on_retry_message: Optional[Callable[[str, int], None]] = None):
        """
        Args:
            on_retry_message: Optional callback(message: str, wait_seconds: int)
                            Called when retry is needed. If None, uses print.
                            Pass lambda msg, sec: None to suppress output.
        """
        self.on_retry_message = on_retry_message or self._default_log

    def _default_log(self, message: str, wait_seconds: int):
        """Default logging implementation"""
        print(message)

    def check(self, stdout: str, returncode: int, attempt: int = 1) -> Tuple[bool, int]:
        """
        Check if we should retry.

        Args:
            stdout: Output from Claude Code
            returncode: Exit code from Claude Code
            attempt: Current attempt number (for exponential backoff)

        Returns:
            (should_retry: bool, wait_seconds: int)
        """
        # Success - no retry
        if returncode == 0:
            return False, 0

        # Session limit with specific reset time
        if "Session limit reached" in stdout:
            wait = self._parse_reset_time(stdout)
            if wait > 0:
                self.on_retry_message(
                    f"⏳ Session limit - waiting until reset ({wait//60} minutes)",
                    wait
                )
                return True, wait
            else:
                # Couldn't parse time, use default
                self.on_retry_message(
                    f"⏳ Session limit - waiting {DEFAULT_SESSION_LIMIT_WAIT//60} minutes",
                    DEFAULT_SESSION_LIMIT_WAIT
                )
                return True, DEFAULT_SESSION_LIMIT_WAIT

        # Network/transient errors
        if any(err in stdout.lower() for err in NETWORK_ERROR_KEYWORDS):
            wait = min(NETWORK_RETRY_BASE * (2 ** (attempt - 1)), NETWORK_RETRY_MAX)
            self.on_retry_message(
                f"⚠️  Network error - waiting {wait}s (attempt {attempt})",
                wait
            )
            return True, wait

        # Other errors - exponential backoff
        wait = min(OTHER_RETRY_BASE * (2 ** (attempt - 1)), OTHER_RETRY_MAX)
        self.on_retry_message(
            f"⚠️  Error (code {returncode}) - waiting {wait}s (attempt {attempt})",
            wait
        )
        return True, wait

    def _parse_reset_time(self, text: str) -> int:
        """
        Parse 'resets Xpm' message, return seconds to wait.

        Returns:
            Seconds to wait, or 0 if couldn't parse
        """
        match = re.search(r'resets (\d+)(am|pm)', text, re.IGNORECASE)
        if not match:
            return 0

        hour = int(match.group(1))
        period = match.group(2).lower()

        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0

        now = datetime.now()
        reset = now.replace(hour=hour, minute=0, second=0, microsecond=0)

        if reset <= now:
            reset += timedelta(days=1)

        return int((reset - now).total_seconds() + SESSION_LIMIT_BUFFER)
