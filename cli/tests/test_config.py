"""Tests for configuration module."""

import json
import pytest
from pathlib import Path

from cc.config.settings import Settings, DEFAULTS
from cc.config.paths import (
    get_config_dir,
    get_project_dir,
    find_claude_md,
)


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self, temp_dir):
        """Test that default settings are loaded."""
        settings = Settings(project_path=temp_dir)
        settings.load()

        assert settings.get("model") == DEFAULTS["model"]
        assert settings.get("maxTokens") == DEFAULTS["maxTokens"]
        assert settings.get("markdown") == DEFAULTS["markdown"]

    def test_set_and_get(self, temp_dir):
        """Test setting and getting values."""
        settings = Settings(project_path=temp_dir)
        settings.load()

        settings.set("model", "opus", scope="cli")
        assert settings.get("model") == "opus"

    def test_nested_key(self, temp_dir):
        """Test dot notation for nested keys."""
        settings = Settings(project_path=temp_dir)
        settings.load()

        settings.set("hooks.PreToolUse", "echo test", scope="cli")
        assert settings.get("hooks.PreToolUse") == "echo test"

    def test_default_fallback(self, temp_dir):
        """Test default value fallback."""
        settings = Settings(project_path=temp_dir)
        settings.load()

        assert settings.get("nonexistent", "default_value") == "default_value"

    def test_all_settings(self, temp_dir):
        """Test getting all settings."""
        settings = Settings(project_path=temp_dir)
        settings.load()

        all_settings = settings.all()
        assert "model" in all_settings
        assert "maxTokens" in all_settings

    def test_permission_mode(self, temp_dir):
        """Test permission_mode property."""
        settings = Settings(project_path=temp_dir)
        settings.load()

        assert settings.permission_mode == "ask"

        settings.set("skipPermissions", True, scope="cli")
        assert settings.permission_mode == "never"

    def test_save_and_load(self, temp_dir):
        """Test saving and loading settings."""
        # Create user settings directory
        config_dir = temp_dir / ".cc"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"

        # Write initial settings
        with open(settings_file, "w") as f:
            json.dump({"model": "opus"}, f)

        # Patch the config dir function
        import cc.config.paths
        original_func = cc.config.paths.get_config_dir
        cc.config.paths.get_config_dir = lambda: config_dir

        try:
            settings = Settings(project_path=temp_dir)
            settings.load()
            assert settings.get("model") == "opus"
        finally:
            cc.config.paths.get_config_dir = original_func


class TestPaths:
    """Tests for path utilities."""

    def test_get_config_dir(self):
        """Test getting config directory."""
        config_dir = get_config_dir()
        assert config_dir.name == ".cc"
        assert config_dir.parent.name == Path.home().name

    def test_get_project_dir(self, temp_dir):
        """Test getting project directory."""
        project_dir = get_project_dir(temp_dir)
        # Should be under ~/.cc/projects/
        assert "projects" in str(project_dir)

    def test_find_claude_md_not_found(self, temp_dir):
        """Test finding CLAUDE.md when it doesn't exist."""
        result = find_claude_md(temp_dir)
        assert result is None

    def test_find_claude_md_found(self, temp_dir):
        """Test finding CLAUDE.md when it exists."""
        claude_md = temp_dir / "CLAUDE.md"
        claude_md.write_text("# Project Instructions")

        result = find_claude_md(temp_dir)
        assert result == claude_md

    def test_find_claude_md_parent(self, temp_dir):
        """Test finding CLAUDE.md in parent directory."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        claude_md = temp_dir / "CLAUDE.md"
        claude_md.write_text("# Project Instructions")

        result = find_claude_md(subdir)
        assert result == claude_md
