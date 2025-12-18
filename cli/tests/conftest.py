"""Pytest fixtures for CC CLI tests."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_api_key(monkeypatch):
    """Set a mock API key for tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")


@pytest.fixture
def temp_config_dir(temp_dir: Path, monkeypatch):
    """Create a temporary config directory."""
    config_dir = temp_dir / ".cc"
    config_dir.mkdir()
    monkeypatch.setattr("cc.config.paths.get_config_dir", lambda: config_dir)
    return config_dir


@pytest.fixture
def temp_project_dir(temp_dir: Path):
    """Create a temporary project directory."""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    return project_dir
