# Task: Create Unit Tests for cc_atoms v3 TaskAnalyzer

Create comprehensive unit tests for the TaskAnalyzer class in `/Users/tonyjabroni/claude/cc/src/cc_atoms/atom_core/task_analyzer.py`.

## Requirements

1. Test `_is_trivially_simple()`:
   - "hello" should be simple
   - "Build a REST API with authentication" should NOT be simple

2. Test complexity detection:
   - Simple tasks get ComplexityLevel.SIMPLE
   - Tasks with "implement", "build" keywords get COMPLEX

3. Test `should_decompose()`:
   - DecompositionLevel.NONE should never decompose
   - DecompositionLevel.AGGRESSIVE should always decompose
   - DecompositionLevel.STANDARD should decompose COMPLEX but not SIMPLE

4. Test memory query generation

Put the tests in: `/Users/tonyjabroni/claude/cc/tests/test_task_analyzer.py`

Run the tests with pytest and ensure they pass.

When complete, output EXIT_LOOP_NOW
