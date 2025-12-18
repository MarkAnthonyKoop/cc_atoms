"""Tests for main entry point."""

import pytest
from cc.main import create_parser, main


class TestParser:
    """Tests for argument parser."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "cc"

    def test_version_flag(self):
        """Test --version flag."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_prompt_flag(self):
        """Test -p/--prompt flag."""
        parser = create_parser()
        args = parser.parse_args(["-p", "Hello, Claude!"])
        assert args.prompt == "Hello, Claude!"

    def test_continue_flag(self):
        """Test -c/--continue flag."""
        parser = create_parser()
        args = parser.parse_args(["-c"])
        assert args.continue_session is True

    def test_resume_flag(self):
        """Test -r/--resume flag."""
        parser = create_parser()
        args = parser.parse_args(["-r", "session-123"])
        assert args.resume == "session-123"

    def test_print_flag(self):
        """Test --print flag."""
        parser = create_parser()
        args = parser.parse_args(["--print"])
        assert args.print_mode is True

    def test_output_format(self):
        """Test --output-format flag."""
        parser = create_parser()
        args = parser.parse_args(["--output-format", "json"])
        assert args.output_format == "json"

    def test_model_flag(self):
        """Test -m/--model flag."""
        parser = create_parser()
        args = parser.parse_args(["-m", "opus"])
        assert args.model == "opus"

    def test_cwd_flag(self):
        """Test -d/--cwd flag."""
        parser = create_parser()
        args = parser.parse_args(["-d", "/tmp"])
        assert args.cwd == "/tmp"

    def test_mcp_subcommand(self):
        """Test mcp subcommand."""
        parser = create_parser()
        args = parser.parse_args(["mcp", "list"])
        assert args.command == "mcp"
        assert args.mcp_command == "list"

    def test_config_subcommand(self):
        """Test config subcommand."""
        parser = create_parser()
        args = parser.parse_args(["config", "get", "model"])
        assert args.command == "config"
        assert args.config_command == "get"
        assert args.key == "model"

    def test_sessions_subcommand(self):
        """Test sessions subcommand."""
        parser = create_parser()
        args = parser.parse_args(["sessions", "list"])
        assert args.command == "sessions"
        assert args.sessions_command == "list"

    def test_skip_permissions_flag(self):
        """Test --dangerously-skip-permissions flag."""
        parser = create_parser()
        args = parser.parse_args(["--dangerously-skip-permissions"])
        assert args.dangerously_skip_permissions is True


class TestMain:
    """Tests for main function."""

    def test_main_with_help(self):
        """Test main with --help."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_main_mcp_list(self):
        """Test main with mcp list subcommand."""
        result = main(["mcp", "list"])
        assert result == 0
