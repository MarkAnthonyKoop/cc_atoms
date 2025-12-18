"""Tests for API module."""

import pytest
from cc.api.models import (
    resolve_model,
    validate_model,
    get_model_info,
    MODEL_ALIASES,
)


class TestModels:
    """Tests for model resolution and validation."""

    def test_resolve_sonnet_alias(self):
        """Test resolving 'sonnet' alias."""
        result = resolve_model("sonnet")
        assert result == "claude-sonnet-4-5-20250929"

    def test_resolve_opus_alias(self):
        """Test resolving 'opus' alias."""
        result = resolve_model("opus")
        assert result == "claude-opus-4-5-20251101"

    def test_resolve_haiku_alias(self):
        """Test resolving 'haiku' alias."""
        result = resolve_model("haiku")
        assert result == "claude-haiku-3-5-20241022"

    def test_resolve_full_model_name(self):
        """Test that full model names are returned as-is."""
        full_name = "claude-sonnet-4-5-20250929"
        result = resolve_model(full_name)
        assert result == full_name

    def test_resolve_case_insensitive(self):
        """Test case-insensitive alias resolution."""
        assert resolve_model("SONNET") == MODEL_ALIASES["sonnet"]
        assert resolve_model("Opus") == MODEL_ALIASES["opus"]

    def test_validate_alias(self):
        """Test validating model alias."""
        assert validate_model("sonnet") is True
        assert validate_model("opus") is True
        assert validate_model("haiku") is True

    def test_validate_full_name(self):
        """Test validating full model name."""
        assert validate_model("claude-sonnet-4-5-20250929") is True
        assert validate_model("claude-opus-4-5-20251101") is True

    def test_validate_invalid(self):
        """Test validation of invalid model name."""
        assert validate_model("gpt-4") is False
        assert validate_model("invalid-model") is False

    def test_get_model_info_alias(self):
        """Test getting model info from alias."""
        info = get_model_info("sonnet")
        assert info["name"] == "claude-sonnet-4-5-20250929"
        assert info["alias"] == "sonnet"
        assert info["family"] == "sonnet"

    def test_get_model_info_full_name(self):
        """Test getting model info from full name."""
        info = get_model_info("claude-opus-4-5-20251101")
        assert info["name"] == "claude-opus-4-5-20251101"
        assert info["alias"] is None
        assert info["family"] == "opus"
