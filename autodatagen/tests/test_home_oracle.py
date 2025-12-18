#!/usr/bin/env python3
"""
Tests for Home Oracle

Run with: python -m pytest tests/test_home_oracle.py -v
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from home_oracle import (
    OracleConfig,
    OracleSearch,
    OracleAgent,
    SearchResult,
    RetrievalState
)


class TestOracleConfig:
    """Test OracleConfig defaults and customization."""

    def test_default_config(self):
        config = OracleConfig()
        assert config.max_search_iterations == 5
        assert config.confidence_threshold == 0.7
        assert config.generation_model == 'gemini-2.0-flash'
        assert 'home_index' in config.index_path

    def test_custom_config(self):
        config = OracleConfig(
            max_search_iterations=10,
            confidence_threshold=0.9
        )
        assert config.max_search_iterations == 10
        assert config.confidence_threshold == 0.9


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_search_result_creation(self):
        result = SearchResult(
            content="test content",
            source="/home/user/test.py",
            doc_type="code",
            score=0.85,
            relative_path="test.py"
        )
        assert result.content == "test content"
        assert result.score == 0.85


class TestRetrievalState:
    """Test RetrievalState tracking."""

    def test_add_results_deduplication(self):
        state = RetrievalState(original_query="test query")

        r1 = SearchResult(content="a", source="file1.py", doc_type="code", score=0.9, relative_path="file1.py")
        r2 = SearchResult(content="b", source="file2.py", doc_type="code", score=0.8, relative_path="file2.py")
        r3 = SearchResult(content="c", source="file1.py", doc_type="code", score=0.7, relative_path="file1.py")  # Duplicate source

        new_count = state.add_results("query1", [r1, r2])
        assert new_count == 2
        assert len(state.gathered_context) == 2

        new_count = state.add_results("query2", [r3])
        assert new_count == 0  # Duplicate, not added
        assert len(state.gathered_context) == 2

    def test_queries_tracked(self):
        state = RetrievalState(original_query="test")
        state.add_results("query1", [])
        state.add_results("query2", [])
        assert state.queries_executed == ["query1", "query2"]

    def test_context_summary(self):
        state = RetrievalState(original_query="test")
        r1 = SearchResult(content="content", source="/path/file.py", doc_type="code", score=0.85, relative_path="file.py")
        state.add_results("query", [r1])
        summary = state.get_context_summary()
        assert "code" in summary
        assert "file.py" in summary
        assert "0.85" in summary


class TestOracleAgent:
    """Test OracleAgent functionality."""

    @pytest.fixture
    def mock_config(self):
        return OracleConfig(
            gemini_api_key="test-key",
            verbose=False
        )

    def test_agent_creation(self, mock_config):
        with patch.object(OracleSearch, '_init_search'):
            agent = OracleAgent(mock_config)
            assert agent.config.gemini_api_key == "test-key"

    @pytest.mark.skipif(not os.getenv('GEMINI_API_KEY'), reason="GEMINI_API_KEY not set")
    def test_quick_answer_integration(self):
        """Integration test - requires GEMINI_API_KEY and home index."""
        agent = OracleAgent()
        result = agent.ask("What is Python?", quick=True)
        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result


class TestOracleSearch:
    """Test OracleSearch backend selection."""

    def test_search_backend_fallback(self):
        """Test that search falls back gracefully."""
        config = OracleConfig(
            index_path="/nonexistent/path",
            verbose=False
        )
        # Should not raise even with bad path
        search = OracleSearch(config)
        assert search is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
