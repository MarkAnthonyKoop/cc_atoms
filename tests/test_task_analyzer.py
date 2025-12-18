"""
Unit tests for TaskAnalyzer class

Tests cover:
1. _is_trivially_simple() - detecting trivially simple tasks
2. Complexity detection via heuristics
3. should_decompose() - decomposition decisions based on level
4. Memory query generation
"""

import pytest
from cc_atoms.atom_core.task_analyzer import (
    TaskAnalyzer,
    TaskAnalysis,
    AnalyzerConfig,
    ComplexityLevel,
    DecompositionLevel,
)


class TestIsTriviallySimple:
    """Tests for _is_trivially_simple() method"""

    def test_hello_is_simple(self):
        """'hello' should be detected as trivially simple"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("hello") is True

    def test_hi_is_simple(self):
        """'hi' should be detected as trivially simple"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("hi") is True

    def test_test_is_simple(self):
        """'test' should be detected as trivially simple"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("test") is True

    def test_print_hello_is_simple(self):
        """'print hello world' should be simple"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("print hello world") is True

    def test_show_files_is_simple(self):
        """'show files' should be simple"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("show files") is True

    def test_what_is_question_is_simple(self):
        """'what is this?' should be simple"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("what is this?") is True

    def test_rest_api_is_not_simple(self):
        """'Build a REST API with authentication' should NOT be simple"""
        analyzer = TaskAnalyzer()
        task = "Build a REST API with authentication"
        assert analyzer._is_trivially_simple(task) is False

    def test_complex_task_is_not_simple(self):
        """Complex implementation tasks should not be simple"""
        analyzer = TaskAnalyzer()
        task = "Implement a full authentication system with OAuth2"
        assert analyzer._is_trivially_simple(task) is False

    def test_long_task_is_not_simple(self):
        """Tasks longer than 30 characters without simple patterns are not simple"""
        analyzer = TaskAnalyzer()
        task = "Create a new module for handling user authentication"
        assert analyzer._is_trivially_simple(task) is False

    def test_case_insensitive(self):
        """Simple pattern matching should be case-insensitive"""
        analyzer = TaskAnalyzer()
        assert analyzer._is_trivially_simple("HELLO") is True
        assert analyzer._is_trivially_simple("Hello") is True
        assert analyzer._is_trivially_simple("HeLLo ThErE") is True


class TestComplexityDetection:
    """Tests for complexity level detection via heuristic analysis"""

    def test_simple_task_gets_simple_complexity(self):
        """Simple tasks should get ComplexityLevel.SIMPLE"""
        analyzer = TaskAnalyzer()
        # Use analyze() which will short-circuit to _simple_analysis for trivial tasks
        analysis = analyzer.analyze("hello")
        assert analysis.complexity == ComplexityLevel.SIMPLE

    def test_complex_keywords_trigger_complex(self):
        """Tasks with 'implement', 'build' keywords should get COMPLEX"""
        analyzer = TaskAnalyzer()
        # This task has multiple complex keywords and is long
        analysis = analyzer._heuristic_analysis("implement a build system for api")
        assert analysis.complexity == ComplexityLevel.COMPLEX

    def test_single_complex_keyword_with_moderate(self):
        """Single complex keyword might get moderate without other signals"""
        analyzer = TaskAnalyzer()
        analysis = analyzer._heuristic_analysis("add a function")
        assert analysis.complexity == ComplexityLevel.MODERATE

    def test_build_keyword_in_context(self):
        """'build' keyword should contribute to complexity"""
        analyzer = TaskAnalyzer()
        analysis = analyzer._heuristic_analysis("build an authentication system")
        assert analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.MODERATE]

    def test_implement_keyword(self):
        """'implement' keyword should contribute to complexity when combined with other signals"""
        analyzer = TaskAnalyzer()
        # Single complex keyword alone may not be enough (needs 2+ complex keywords
        # or 1+ moderate keywords for elevation)
        # Use a longer task or add a moderate keyword
        analysis = analyzer._heuristic_analysis("implement a new user registration feature")
        assert analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.MODERATE]

    def test_multiple_complex_keywords(self):
        """Multiple complex keywords should definitely be COMPLEX"""
        analyzer = TaskAnalyzer()
        analysis = analyzer._heuristic_analysis(
            "design and implement a database migration system with authentication"
        )
        assert analysis.complexity == ComplexityLevel.COMPLEX

    def test_long_task_is_complex(self):
        """Very long tasks (>200 chars) should be COMPLEX"""
        analyzer = TaskAnalyzer()
        long_task = "a" * 201
        analysis = analyzer._heuristic_analysis(long_task)
        assert analysis.complexity == ComplexityLevel.COMPLEX

    def test_force_complex_mode(self):
        """force_complex config should force COMPLEX analysis"""
        config = AnalyzerConfig(force_complex=True)
        analyzer = TaskAnalyzer(config=config)
        analysis = analyzer.analyze("hello")  # Would normally be simple
        assert analysis.complexity == ComplexityLevel.COMPLEX


class TestShouldDecompose:
    """Tests for should_decompose() method"""

    def test_none_level_never_decomposes(self):
        """DecompositionLevel.NONE should never decompose"""
        config = AnalyzerConfig(decomposition_level=DecompositionLevel.NONE)
        analyzer = TaskAnalyzer(config=config)

        # Even MASSIVE complexity should not decompose with NONE level
        massive_analysis = TaskAnalysis(
            complexity=ComplexityLevel.MASSIVE,
            memory_queries=[],
            suggested_decomposition=["step1", "step2"],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=10,
        )
        assert analyzer.should_decompose(massive_analysis) is False

        # COMPLEX should not decompose
        complex_analysis = TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=5,
        )
        assert analyzer.should_decompose(complex_analysis) is False

        # SIMPLE should not decompose
        simple_analysis = TaskAnalysis(
            complexity=ComplexityLevel.SIMPLE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=1,
        )
        assert analyzer.should_decompose(simple_analysis) is False

    def test_aggressive_level_always_decomposes(self):
        """DecompositionLevel.AGGRESSIVE should always decompose"""
        config = AnalyzerConfig(decomposition_level=DecompositionLevel.AGGRESSIVE)
        analyzer = TaskAnalyzer(config=config)

        # Even SIMPLE should decompose with AGGRESSIVE level
        simple_analysis = TaskAnalysis(
            complexity=ComplexityLevel.SIMPLE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=1,
        )
        assert analyzer.should_decompose(simple_analysis) is True

        # MODERATE should decompose
        moderate_analysis = TaskAnalysis(
            complexity=ComplexityLevel.MODERATE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=3,
        )
        assert analyzer.should_decompose(moderate_analysis) is True

        # COMPLEX should decompose
        complex_analysis = TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=5,
        )
        assert analyzer.should_decompose(complex_analysis) is True

    def test_standard_level_decomposes_complex_not_simple(self):
        """DecompositionLevel.STANDARD should decompose COMPLEX but not SIMPLE"""
        config = AnalyzerConfig(decomposition_level=DecompositionLevel.STANDARD)
        analyzer = TaskAnalyzer(config=config)

        # SIMPLE should NOT decompose
        simple_analysis = TaskAnalysis(
            complexity=ComplexityLevel.SIMPLE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=1,
        )
        assert analyzer.should_decompose(simple_analysis) is False

        # MODERATE should NOT decompose with STANDARD
        moderate_analysis = TaskAnalysis(
            complexity=ComplexityLevel.MODERATE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=3,
        )
        assert analyzer.should_decompose(moderate_analysis) is False

        # COMPLEX should decompose
        complex_analysis = TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=5,
        )
        assert analyzer.should_decompose(complex_analysis) is True

        # MASSIVE should decompose
        massive_analysis = TaskAnalysis(
            complexity=ComplexityLevel.MASSIVE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=10,
        )
        assert analyzer.should_decompose(massive_analysis) is True

    def test_light_level_only_decomposes_massive(self):
        """DecompositionLevel.LIGHT should only decompose MASSIVE"""
        config = AnalyzerConfig(decomposition_level=DecompositionLevel.LIGHT)
        analyzer = TaskAnalyzer(config=config)

        # SIMPLE should NOT decompose
        simple_analysis = TaskAnalysis(
            complexity=ComplexityLevel.SIMPLE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=1,
        )
        assert analyzer.should_decompose(simple_analysis) is False

        # MODERATE should NOT decompose
        moderate_analysis = TaskAnalysis(
            complexity=ComplexityLevel.MODERATE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=3,
        )
        assert analyzer.should_decompose(moderate_analysis) is False

        # COMPLEX should NOT decompose with LIGHT
        complex_analysis = TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=5,
        )
        assert analyzer.should_decompose(complex_analysis) is False

        # Only MASSIVE should decompose
        massive_analysis = TaskAnalysis(
            complexity=ComplexityLevel.MASSIVE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=10,
        )
        assert analyzer.should_decompose(massive_analysis) is True


class TestMemoryQueryGeneration:
    """Tests for memory query generation"""

    def test_get_memory_queries_returns_analysis_queries(self):
        """get_memory_queries should return queries from analysis if present"""
        analyzer = TaskAnalyzer()
        analysis = TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=["query1", "query2"],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=5,
        )
        queries = analyzer.get_memory_queries(analysis, "some task")
        assert queries == ["query1", "query2"]

    def test_get_memory_queries_falls_back_to_task_for_non_simple(self):
        """For non-simple tasks without queries, use task as fallback"""
        analyzer = TaskAnalyzer()
        analysis = TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=[],  # Empty queries
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=5,
        )
        task = "Build a REST API"
        queries = analyzer.get_memory_queries(analysis, task)
        assert queries == [task]

    def test_get_memory_queries_truncates_long_task(self):
        """Long tasks should be truncated to 200 chars when used as fallback"""
        analyzer = TaskAnalyzer()
        analysis = TaskAnalysis(
            complexity=ComplexityLevel.MODERATE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=3,
        )
        long_task = "x" * 300
        queries = analyzer.get_memory_queries(analysis, long_task)
        assert len(queries) == 1
        assert len(queries[0]) == 200

    def test_get_memory_queries_empty_for_simple(self):
        """Simple tasks should return empty queries if none provided"""
        analyzer = TaskAnalyzer()
        analysis = TaskAnalysis(
            complexity=ComplexityLevel.SIMPLE,
            memory_queries=[],
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="test",
            estimated_iterations=1,
        )
        queries = analyzer.get_memory_queries(analysis, "hello")
        assert queries == []

    def test_heuristic_generates_memory_query_for_complex(self):
        """Heuristic analysis should generate memory query for complex tasks"""
        analyzer = TaskAnalyzer()
        analysis = analyzer._heuristic_analysis(
            "implement authentication system with database"
        )
        assert len(analysis.memory_queries) > 0

    def test_heuristic_no_memory_query_for_simple(self):
        """Heuristic analysis should not generate memory query for simple tasks"""
        analyzer = TaskAnalyzer()
        # A truly simple task by heuristics
        analysis = analyzer._heuristic_analysis("ok")
        assert analysis.complexity == ComplexityLevel.SIMPLE
        assert analysis.memory_queries == []


class TestAnalyzerIntegration:
    """Integration tests for the full analyze() flow"""

    def test_analyze_simple_task_returns_simple(self):
        """Simple tasks via analyze() should return SIMPLE complexity"""
        analyzer = TaskAnalyzer()
        analysis = analyzer.analyze("hello")
        assert analysis.complexity == ComplexityLevel.SIMPLE
        assert analysis.estimated_iterations == 1
        assert analysis.meta_agents_needed == []

    def test_analyze_returns_task_analysis_object(self):
        """analyze() should return a TaskAnalysis object"""
        analyzer = TaskAnalyzer()
        analysis = analyzer.analyze("test")
        assert isinstance(analysis, TaskAnalysis)

    def test_simple_analysis_has_no_decomposition(self):
        """Simple analysis should have no suggested decomposition"""
        analyzer = TaskAnalyzer()
        analysis = analyzer.analyze("hello")
        assert analysis.suggested_decomposition == []

    def test_force_complex_enables_meta_agents(self):
        """force_complex should enable meta agents"""
        config = AnalyzerConfig(force_complex=True)
        analyzer = TaskAnalyzer(config=config)
        analysis = analyzer.analyze("hello")
        assert "critic" in analysis.meta_agents_needed or "verifier" in analysis.meta_agents_needed

    def test_force_complex_allows_runtime_decomposition(self):
        """force_complex returns empty decomposition so runtime generates specific steps"""
        config = AnalyzerConfig(force_complex=True)
        analyzer = TaskAnalyzer(config=config)
        analysis = analyzer.analyze("hello")
        # Empty decomposition = runtime will generate task-specific steps
        assert analysis.suggested_decomposition == []
        assert analysis.complexity == ComplexityLevel.COMPLEX

    def test_default_config(self):
        """Default config should be STANDARD decomposition"""
        analyzer = TaskAnalyzer()
        assert analyzer.config.decomposition_level == DecompositionLevel.STANDARD
        assert analyzer.config.force_complex is False


class TestTaskAnalysisFlags:
    """Tests for TaskAnalysis boolean flags"""

    def test_heuristic_detects_needs_tests(self):
        """Heuristic should set needs_tests when 'test' in task"""
        analyzer = TaskAnalyzer()
        analysis = analyzer._heuristic_analysis("add unit tests for the module")
        assert analysis.needs_tests is True

    def test_heuristic_detects_needs_docs(self):
        """Heuristic should set needs_docs when 'doc' or 'readme' in task"""
        analyzer = TaskAnalyzer()
        analysis1 = analyzer._heuristic_analysis("update the documentation")
        assert analysis1.needs_docs is True

        analysis2 = analyzer._heuristic_analysis("update readme file")
        assert analysis2.needs_docs is True

    def test_heuristic_detects_needs_review_for_complex(self):
        """Complex tasks should set needs_review"""
        analyzer = TaskAnalyzer()
        analysis = analyzer._heuristic_analysis(
            "implement and build a system for api integration"
        )
        assert analysis.complexity == ComplexityLevel.COMPLEX
        assert analysis.needs_review is True
