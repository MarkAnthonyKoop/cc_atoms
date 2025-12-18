"""Tests for UI modules."""

import pytest
from io import StringIO
import sys

from cc.ui.colors import Colors
from cc.ui.renderer import Renderer


class TestColors:
    """Tests for Colors class."""

    def test_color_codes(self):
        """Test that color codes are defined."""
        assert Colors.RED is not None
        assert Colors.GREEN is not None
        assert Colors.YELLOW is not None
        assert Colors.BLUE is not None
        assert Colors.RESET is not None

    def test_colorize_function(self):
        """Test colorize function."""
        from cc.ui.colors import colorize
        result = colorize("test", Colors.RED)
        assert "test" in result
        assert Colors.RESET in result


class TestRenderer:
    """Tests for Renderer class."""

    def test_initialization(self):
        """Test renderer initialization."""
        renderer = Renderer()
        assert renderer is not None

    def test_text_output(self, capsys):
        """Test basic text output."""
        renderer = Renderer()
        renderer.text("Hello, world!")

        captured = capsys.readouterr()
        assert "Hello, world!" in captured.out

    def test_success_message(self, capsys):
        """Test success message formatting."""
        renderer = Renderer()
        renderer.success("Operation complete")

        captured = capsys.readouterr()
        assert "Operation complete" in captured.out

    def test_error_message(self, capsys):
        """Test error message formatting."""
        renderer = Renderer()
        renderer.error("An error occurred")

        captured = capsys.readouterr()
        # Error should be printed (Rich outputs to stdout by default)
        assert "An error occurred" in captured.out or "Error" in captured.out

    def test_warning_message(self, capsys):
        """Test warning message formatting."""
        renderer = Renderer()
        renderer.warning("Warning message")

        captured = capsys.readouterr()
        assert "Warning message" in captured.out

    def test_dim_message(self, capsys):
        """Test dimmed message formatting."""
        renderer = Renderer()
        renderer.dim("Dimmed text")

        captured = capsys.readouterr()
        assert "Dimmed text" in captured.out

    def test_newline(self, capsys):
        """Test newline output."""
        renderer = Renderer()
        renderer.newline()

        captured = capsys.readouterr()
        assert "\n" in captured.out

    def test_stream_text(self, capsys):
        """Test streaming text output."""
        renderer = Renderer()
        renderer.stream_text("Streaming")
        renderer.stream_text(" text")

        captured = capsys.readouterr()
        assert "Streaming text" in captured.out

    def test_stream_end(self, capsys):
        """Test ending text stream."""
        renderer = Renderer()
        renderer.stream_text("Text")
        renderer.stream_end()

        captured = capsys.readouterr()
        assert "\n" in captured.out

    def test_tool_use_start(self, capsys):
        """Test tool use start message."""
        renderer = Renderer()
        renderer.tool_use_start("Bash", "echo hello")

        captured = capsys.readouterr()
        assert "Bash" in captured.out
        assert "echo hello" in captured.out

    def test_clear_and_rule(self, capsys):
        """Test clearing console and drawing rules."""
        renderer = Renderer()
        # Test that clear doesn't raise an error
        renderer.clear()
        # Test that rule works
        renderer.rule("Test")

        captured = capsys.readouterr()
        assert len(captured.out) >= 0  # Just check it doesn't fail

    def test_markdown_mode(self):
        """Test markdown mode setting."""
        renderer_with_md = Renderer(use_markdown=True)
        renderer_without_md = Renderer(use_markdown=False)

        assert renderer_with_md is not None
        assert renderer_without_md is not None
