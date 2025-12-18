#!/usr/bin/env python3
"""
Simple test runner for Home Oracle (no pytest required)
"""
import os
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from home_oracle import (
    OracleConfig,
    OracleSearch,
    OracleAgent,
    SearchResult,
    RetrievalState
)


def test_oracle_config():
    """Test OracleConfig defaults."""
    print("Testing OracleConfig...")
    config = OracleConfig()
    assert config.max_search_iterations == 5, "max_search_iterations should be 5"
    assert config.confidence_threshold == 0.7, "confidence_threshold should be 0.7"
    assert config.generation_model == 'gemini-2.0-flash', "generation_model should be gemini-2.0-flash"
    print("  ✓ Default config values correct")

    config2 = OracleConfig(max_search_iterations=10, confidence_threshold=0.9)
    assert config2.max_search_iterations == 10
    assert config2.confidence_threshold == 0.9
    print("  ✓ Custom config values work")


def test_search_result():
    """Test SearchResult dataclass."""
    print("Testing SearchResult...")
    result = SearchResult(
        content="test content",
        source="/home/user/test.py",
        doc_type="code",
        score=0.85,
        relative_path="test.py"
    )
    assert result.content == "test content"
    assert result.score == 0.85
    assert result.doc_type == "code"
    print("  ✓ SearchResult created correctly")


def test_retrieval_state():
    """Test RetrievalState tracking."""
    print("Testing RetrievalState...")

    state = RetrievalState(original_query="test query")
    assert state.original_query == "test query"
    assert state.iteration == 0
    assert len(state.gathered_context) == 0
    print("  ✓ Initial state correct")

    # Test deduplication
    r1 = SearchResult(content="a", source="file1.py", doc_type="code", score=0.9, relative_path="file1.py")
    r2 = SearchResult(content="b", source="file2.py", doc_type="code", score=0.8, relative_path="file2.py")
    r3 = SearchResult(content="c", source="file1.py", doc_type="code", score=0.7, relative_path="file1.py")

    new_count = state.add_results("query1", [r1, r2])
    assert new_count == 2, f"Expected 2 new results, got {new_count}"
    assert len(state.gathered_context) == 2
    print("  ✓ Added 2 unique results")

    new_count = state.add_results("query2", [r3])
    assert new_count == 0, "Duplicate should not be added"
    assert len(state.gathered_context) == 2
    print("  ✓ Deduplication working")

    assert len(state.queries_executed) == 2
    print("  ✓ Queries tracked")

    summary = state.get_context_summary()
    assert "code" in summary
    assert "file1.py" in summary
    print("  ✓ Context summary generated")


def test_oracle_search():
    """Test OracleSearch initialization."""
    print("Testing OracleSearch...")
    config = OracleConfig(
        index_path="/nonexistent/path",
        verbose=False
    )
    # Should not raise even with bad path
    try:
        search = OracleSearch(config)
        print("  ✓ Search backend initialized (with fallback)")
    except Exception as e:
        print(f"  ✗ Search initialization failed: {e}")
        raise


def test_oracle_agent():
    """Test OracleAgent creation."""
    print("Testing OracleAgent...")
    config = OracleConfig(verbose=False)
    agent = OracleAgent(config)
    assert agent.config is not None
    print("  ✓ Agent created")


def test_integration():
    """Integration test - requires GEMINI_API_KEY and home index."""
    print("Testing Integration (if GEMINI_API_KEY set)...")

    if not os.getenv('GEMINI_API_KEY'):
        print("  ⊘ Skipped (GEMINI_API_KEY not set)")
        return

    agent = OracleAgent(OracleConfig(verbose=False))
    result = agent.ask("What is Python?", quick=True)

    assert "answer" in result, "Result should have 'answer'"
    assert "sources" in result, "Result should have 'sources'"
    assert "confidence" in result, "Result should have 'confidence'"
    assert len(result["answer"]) > 0, "Answer should not be empty"

    print(f"  ✓ Got answer with {len(result['sources'])} sources")
    print(f"  ✓ Confidence: {result['confidence']:.0%}")


def main():
    print("\n" + "="*60)
    print("Home Oracle Test Suite")
    print("="*60 + "\n")

    tests = [
        test_oracle_config,
        test_search_result,
        test_retrieval_state,
        test_oracle_search,
        test_oracle_agent,
        test_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "-"*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("-"*60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
