"""Loading spinners for terminal output."""

import asyncio
import sys
import threading
from typing import Optional


class Spinner:
    """Animated loading spinner for the terminal."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    INTERVAL = 0.08  # seconds between frames

    def __init__(self, message: str = "Loading...", stream=None) -> None:
        """Initialize spinner.

        Args:
            message: Message to display next to spinner
            stream: Output stream (defaults to stderr)
        """
        self.message = message
        self.stream = stream or sys.stderr
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._thread: Optional[threading.Thread] = None
        self._frame_index = 0

    async def start_async(self) -> None:
        """Start the spinner animation asynchronously."""
        self._running = True
        self._task = asyncio.create_task(self._animate_async())

    async def stop_async(self) -> None:
        """Stop the spinner animation asynchronously."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._clear_line()

    async def _animate_async(self) -> None:
        """Animation loop for async spinner."""
        while self._running:
            frame = self.FRAMES[self._frame_index]
            self.stream.write(f"\r{frame} {self.message}")
            self.stream.flush()
            self._frame_index = (self._frame_index + 1) % len(self.FRAMES)
            await asyncio.sleep(self.INTERVAL)

    def start(self) -> None:
        """Start the spinner animation in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._animate_sync)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        self._clear_line()

    def _animate_sync(self) -> None:
        """Animation loop for sync spinner."""
        import time
        while self._running:
            frame = self.FRAMES[self._frame_index]
            self.stream.write(f"\r{frame} {self.message}")
            self.stream.flush()
            self._frame_index = (self._frame_index + 1) % len(self.FRAMES)
            time.sleep(self.INTERVAL)

    def _clear_line(self) -> None:
        """Clear the current line."""
        self.stream.write("\r" + " " * (len(self.message) + 10) + "\r")
        self.stream.flush()

    def update_message(self, message: str) -> None:
        """Update the spinner message.

        Args:
            message: New message to display
        """
        self.message = message

    def __enter__(self) -> "Spinner":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

    async def __aenter__(self) -> "Spinner":
        """Async context manager entry."""
        await self.start_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_async()
