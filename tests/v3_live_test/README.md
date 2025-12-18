# TaskAnalyzer Unit Tests

## Overview
Comprehensive unit tests for the `TaskAnalyzer` class in cc_atoms v3.

## Status
COMPLETE

## Progress
- [x] Created test file at `/Users/tonyjabroni/claude/cc/tests/test_task_analyzer.py`
- [x] Implemented 37 unit tests covering all requirements
- [x] All tests pass with pytest

## Test Coverage

### TestIsTriviallySimple (10 tests)
- "hello" correctly detected as simple
- "Build a REST API with authentication" correctly NOT simple
- Case insensitivity verification
- Various simple patterns (hi, test, print, show, what is)

### TestComplexityDetection (8 tests)
- Simple tasks get ComplexityLevel.SIMPLE
- Tasks with "implement", "build" keywords get COMPLEX when combined with other signals
- Multiple complex keywords trigger COMPLEX
- force_complex mode testing

### TestShouldDecompose (4 tests)
- DecompositionLevel.NONE never decomposes (verified with SIMPLE, COMPLEX, MASSIVE)
- DecompositionLevel.AGGRESSIVE always decomposes (verified with SIMPLE, MODERATE, COMPLEX)
- DecompositionLevel.STANDARD decomposes COMPLEX/MASSIVE but not SIMPLE/MODERATE
- DecompositionLevel.LIGHT only decomposes MASSIVE

### TestMemoryQueryGeneration (6 tests)
- Returns queries from analysis when present
- Falls back to task for non-simple tasks
- Truncates long tasks to 200 chars
- Returns empty for simple tasks

### TestAnalyzerIntegration (6 tests)
- Full analyze() flow tests
- force_complex integration

### TestTaskAnalysisFlags (3 tests)
- needs_tests, needs_docs, needs_review flag detection

## How to Run

```bash
cd /Users/tonyjabroni/claude/cc
python3 -m pytest tests/test_task_analyzer.py -v
```

## Notes
- Tests use the heuristic path to avoid external AI calls
- All 37 tests pass
