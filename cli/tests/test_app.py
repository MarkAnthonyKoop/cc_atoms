"""Tests for application module."""

import os
import tempfile
from pathlib import Path

import pytest

from cc.app import Application, AppConfig, create_app_from_args


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AppConfig()
        assert config.prompt is None
        assert config.continue_session is False
        assert config.print_mode is False
        assert config.output_format == "text"
        assert config.skip_permissions is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AppConfig(
            prompt="Hello",
            print_mode=True,
            model="opus",
            skip_permissions=True,
        )
        assert config.prompt == "Hello"
        assert config.print_mode is True
        assert config.model == "opus"
        assert config.skip_permissions is True


class TestApplication:
    """Tests for Application class."""

    def test_initialization(self, temp_dir, monkeypatch):
        """Test application initialization."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        app = Application()
        assert app.config is not None
        assert isinstance(app.config, AppConfig)

    def test_lazy_loading_settings(self, temp_dir, monkeypatch):
        """Test lazy loading of settings."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        app = Application()
        # Settings should not be loaded yet
        assert app._settings is None

        # Access settings
        settings = app.settings
        assert settings is not None
        # Now they should be loaded
        assert app._settings is not None

    def test_lazy_loading_renderer(self, monkeypatch):
        """Test lazy loading of renderer."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        app = Application()
        assert app._renderer is None

        renderer = app.renderer
        assert renderer is not None
        assert app._renderer is not None

    def test_lazy_loading_session_manager(self, monkeypatch):
        """Test lazy loading of session manager."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        app = Application()
        assert app._session_manager is None

        manager = app.session_manager
        assert manager is not None
        assert app._session_manager is not None

    def test_system_prompt_from_claude_md(self, temp_dir, monkeypatch):
        """Test building system prompt from CLAUDE.md."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.chdir(temp_dir)

        # Create CLAUDE.md
        claude_md = temp_dir / "CLAUDE.md"
        claude_md.write_text("Test instructions")

        app = Application()
        system_prompt = app.get_system_prompt()

        assert system_prompt is not None
        assert "Test instructions" in system_prompt

    def test_system_prompt_with_cli_override(self, monkeypatch):
        """Test system prompt with CLI override."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = AppConfig(system_prompt="Custom prompt")
        app = Application(config)

        system_prompt = app.get_system_prompt()
        assert "Custom prompt" in system_prompt

    def test_get_session_id_resume(self, monkeypatch):
        """Test getting session ID for resume."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = AppConfig(resume_session="session-123")
        app = Application(config)

        session_id = app.get_session_id()
        assert session_id == "session-123"

    def test_get_session_id_new(self, monkeypatch):
        """Test getting session ID for new session."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        app = Application()
        session_id = app.get_session_id()
        assert session_id is None

    def test_custom_commands_loading(self, temp_dir, monkeypatch):
        """Test loading custom commands."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.chdir(temp_dir)

        # Create custom commands directory
        commands_dir = temp_dir / ".cc" / "commands"
        commands_dir.mkdir(parents=True)

        # Create a custom command
        cmd_file = commands_dir / "test.md"
        cmd_file.write_text("Test command content")

        app = Application()
        commands = app.get_custom_commands()

        assert "test" in commands
        assert commands["test"] == "Test command content"

    def test_cwd_option(self, temp_dir, monkeypatch):
        """Test changing working directory."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        original_cwd = os.getcwd()
        # Create a unique test directory
        test_dir = temp_dir / "testcwd"
        test_dir.mkdir()
        config = AppConfig(cwd=str(test_dir))

        try:
            app = Application(config)
            # Check that we changed to the directory
            current = Path.cwd().resolve()
            expected = test_dir.resolve()
            assert current == expected
        finally:
            os.chdir(original_cwd)


class TestCreateAppFromArgs:
    """Tests for create_app_from_args function."""

    def test_create_from_namespace(self, monkeypatch):
        """Test creating app from argparse Namespace."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Create a mock args object
        class Args:
            prompt = "Test"
            continue_session = False
            resume = None
            print_mode = False
            output_format = "text"
            input_format = "text"
            verbose = False
            no_markdown = False
            model = "sonnet"
            max_tokens = None
            dangerously_skip_permissions = False
            allowedTools = []
            disallowedTools = []
            system_prompt = None
            append_system_prompt = None
            cwd = None
            mcp_config = None

        app = create_app_from_args(Args())
        assert app.config.prompt == "Test"
        assert app.config.model == "sonnet"
