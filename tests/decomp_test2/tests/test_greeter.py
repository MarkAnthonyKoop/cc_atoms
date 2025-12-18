"""Tests for the greeter module.

This test file contains test cases for the greet() and farewell() functions
in the greeter module.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path so we can import greeter
sys.path.insert(0, str(Path(__file__).parent.parent))

from greeter import greet, farewell


class TestGreet:
    """Test cases for the greet() function."""

    def test_greet_basic(self):
        """Test greet with a simple name."""
        result = greet("Alice")
        assert result == "Hello, Alice!"

    def test_greet_empty_string(self):
        """Test greet with an empty string."""
        result = greet("")
        assert result == "Hello, !"

    def test_greet_with_spaces(self):
        """Test greet with a name containing spaces."""
        result = greet("John Doe")
        assert result == "Hello, John Doe!"

    def test_greet_special_characters(self):
        """Test greet with special characters in the name."""
        result = greet("O'Brien")
        assert result == "Hello, O'Brien!"


class TestFarewell:
    """Test cases for the farewell() function."""

    def test_farewell_basic(self):
        """Test farewell with a simple name."""
        result = farewell("Bob")
        assert result == "Goodbye, Bob!"

    def test_farewell_empty_string(self):
        """Test farewell with an empty string."""
        result = farewell("")
        assert result == "Goodbye, !"

    def test_farewell_with_spaces(self):
        """Test farewell with a name containing spaces."""
        result = farewell("Jane Smith")
        assert result == "Goodbye, Jane Smith!"

    def test_farewell_special_characters(self):
        """Test farewell with special characters in the name."""
        result = farewell("José")
        assert result == "Goodbye, José!"


class TestGreetEdgeCases:
    """Edge case tests for the greet() function."""

    def test_greet_unicode_characters(self):
        """Test greet with unicode characters."""
        result = greet("日本語")
        assert result == "Hello, 日本語!"

    def test_greet_emoji(self):
        """Test greet with emoji in name."""
        result = greet("Happy 😀")
        assert result == "Hello, Happy 😀!"

    def test_greet_numbers_in_name(self):
        """Test greet with numbers in the name."""
        result = greet("Agent 007")
        assert result == "Hello, Agent 007!"

    def test_greet_only_whitespace(self):
        """Test greet with only whitespace."""
        result = greet("   ")
        assert result == "Hello,    !"

    def test_greet_leading_trailing_spaces(self):
        """Test greet with leading and trailing spaces."""
        result = greet("  Alice  ")
        assert result == "Hello,   Alice  !"

    def test_greet_newline_in_name(self):
        """Test greet with newline character in name."""
        result = greet("Line1\nLine2")
        assert result == "Hello, Line1\nLine2!"

    def test_greet_tab_in_name(self):
        """Test greet with tab character in name."""
        result = greet("Name\tWith\tTabs")
        assert result == "Hello, Name\tWith\tTabs!"

    def test_greet_very_long_name(self):
        """Test greet with a very long name."""
        long_name = "A" * 1000
        result = greet(long_name)
        assert result == f"Hello, {long_name}!"
        assert len(result) == 1008  # "Hello, " (7) + 1000 + "!" (1)

    def test_greet_single_character(self):
        """Test greet with a single character name."""
        result = greet("X")
        assert result == "Hello, X!"

    def test_greet_html_characters(self):
        """Test greet with HTML-like characters."""
        result = greet("<script>alert('hi')</script>")
        assert result == "Hello, <script>alert('hi')</script>!"

    def test_greet_backslash(self):
        """Test greet with backslash in name."""
        result = greet("Path\\Name")
        assert result == "Hello, Path\\Name!"

    def test_greet_quotes(self):
        """Test greet with quotes in name."""
        result = greet('He said "Hello"')
        assert result == 'Hello, He said "Hello"!'


class TestFarewellEdgeCases:
    """Edge case tests for the farewell() function."""

    def test_farewell_unicode_characters(self):
        """Test farewell with unicode characters."""
        result = farewell("中文")
        assert result == "Goodbye, 中文!"

    def test_farewell_emoji(self):
        """Test farewell with emoji in name."""
        result = farewell("Sad 😢")
        assert result == "Goodbye, Sad 😢!"

    def test_farewell_numbers_in_name(self):
        """Test farewell with numbers in the name."""
        result = farewell("Room 101")
        assert result == "Goodbye, Room 101!"

    def test_farewell_only_whitespace(self):
        """Test farewell with only whitespace."""
        result = farewell("   ")
        assert result == "Goodbye,    !"

    def test_farewell_leading_trailing_spaces(self):
        """Test farewell with leading and trailing spaces."""
        result = farewell("  Bob  ")
        assert result == "Goodbye,   Bob  !"

    def test_farewell_newline_in_name(self):
        """Test farewell with newline character in name."""
        result = farewell("First\nLast")
        assert result == "Goodbye, First\nLast!"

    def test_farewell_tab_in_name(self):
        """Test farewell with tab character in name."""
        result = farewell("Col1\tCol2")
        assert result == "Goodbye, Col1\tCol2!"

    def test_farewell_very_long_name(self):
        """Test farewell with a very long name."""
        long_name = "B" * 1000
        result = farewell(long_name)
        assert result == f"Goodbye, {long_name}!"
        assert len(result) == 1010  # "Goodbye, " (9) + 1000 + "!" (1)

    def test_farewell_single_character(self):
        """Test farewell with a single character name."""
        result = farewell("Y")
        assert result == "Goodbye, Y!"

    def test_farewell_sql_injection_like(self):
        """Test farewell with SQL injection-like string."""
        result = farewell("'; DROP TABLE users;--")
        assert result == "Goodbye, '; DROP TABLE users;--!"


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_greet_none_raises_error(self):
        """Test that greet raises TypeError when passed None."""
        with pytest.raises(TypeError):
            greet(None)

    def test_farewell_none_raises_error(self):
        """Test that farewell raises TypeError when passed None."""
        with pytest.raises(TypeError):
            farewell(None)

    def test_greet_integer_raises_error(self):
        """Test that greet raises TypeError when passed an integer."""
        with pytest.raises(TypeError):
            greet(123)

    def test_farewell_integer_raises_error(self):
        """Test that farewell raises TypeError when passed an integer."""
        with pytest.raises(TypeError):
            farewell(456)

    def test_greet_list_raises_error(self):
        """Test that greet raises TypeError when passed a list."""
        with pytest.raises(TypeError):
            greet(["Alice", "Bob"])

    def test_farewell_list_raises_error(self):
        """Test that farewell raises TypeError when passed a list."""
        with pytest.raises(TypeError):
            farewell(["Charlie", "Dave"])

    def test_greet_dict_raises_error(self):
        """Test that greet raises TypeError when passed a dict."""
        with pytest.raises(TypeError):
            greet({"name": "Eve"})

    def test_farewell_dict_raises_error(self):
        """Test that farewell raises TypeError when passed a dict."""
        with pytest.raises(TypeError):
            farewell({"name": "Frank"})

    def test_greet_no_args_raises_error(self):
        """Test that greet raises TypeError when called with no arguments."""
        with pytest.raises(TypeError):
            greet()

    def test_farewell_no_args_raises_error(self):
        """Test that farewell raises TypeError when called with no arguments."""
        with pytest.raises(TypeError):
            farewell()

    def test_greet_too_many_args_raises_error(self):
        """Test that greet raises TypeError when called with too many arguments."""
        with pytest.raises(TypeError):
            greet("Alice", "extra")

    def test_farewell_too_many_args_raises_error(self):
        """Test that farewell raises TypeError when called with too many arguments."""
        with pytest.raises(TypeError):
            farewell("Bob", "extra")
