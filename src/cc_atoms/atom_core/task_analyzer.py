"""
Task Analyzer - Evaluates task complexity and forms intelligent queries

This module provides upfront AI-based analysis of tasks to:
1. Evaluate complexity (simple/moderate/complex)
2. Form optimized memory queries based on task semantics
3. Suggest decomposition strategy
4. Identify required meta-agents (critic, verifier, etc.)

The key insight: spend a small amount of compute upfront to make better
decisions about how to approach the task, rather than diving in blind.
"""

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ComplexityLevel(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"      # Single action, no decomposition needed
    MODERATE = "moderate"  # Few steps, light decomposition optional
    COMPLEX = "complex"    # Multi-step, decomposition recommended
    MASSIVE = "massive"    # Many components, forced decomposition


# Import DecompositionLevel from config to ensure single definition
# This avoids enum comparison issues
from cc_atoms.config import DecompositionLevel


@dataclass
class TaskAnalysis:
    """Result of analyzing a task"""
    complexity: ComplexityLevel
    memory_queries: List[str]  # Optimized queries for memory lookup
    suggested_decomposition: List[str]  # Suggested sub-tasks if complex
    meta_agents_needed: List[str]  # Which meta-agents to spawn (critic, verifier, etc.)
    reasoning: str  # Why this analysis was made
    estimated_iterations: int  # Rough estimate of iterations needed

    # Flags
    needs_tests: bool = False
    needs_docs: bool = False
    needs_review: bool = False
    is_refactor: bool = False


@dataclass
class AnalyzerConfig:
    """Configuration for task analysis"""
    decomposition_level: DecompositionLevel = DecompositionLevel.STANDARD
    force_complex: bool = False  # For testing: treat all tasks as complex
    min_iterations_for_review: int = 3  # Spawn critic if estimated iterations >= this
    always_verify: bool = False  # Always run verifier before exit
    verbose: bool = False


# System prompt for the analyzer
ANALYZER_SYSTEM_PROMPT = """You are a task complexity analyzer. Given a task description, analyze it and return a JSON object.

Your job is to:
1. Assess complexity (simple/moderate/complex/massive)
2. Generate 1-3 optimized search queries for retrieving relevant context from a memory system
3. If complex, suggest how to decompose the task
4. Determine which meta-agents are needed

Complexity guidelines:
- SIMPLE: Single action, trivial (e.g., "print hello", "rename variable", "add comment")
- MODERATE: Few clear steps (e.g., "add a function", "fix this bug", "update config")
- COMPLEX: Multiple components, needs planning (e.g., "add authentication", "refactor module")
- MASSIVE: Large scope, many subsystems (e.g., "build REST API", "rewrite the app")

Meta-agents available:
- "planner": Creates detailed execution plan (for complex+)
- "critic": Reviews work for issues (for moderate+)
- "verifier": Runs tests and checks (when tests exist or should)
- "documenter": Updates documentation (when docs needed)

Return ONLY valid JSON in this format:
{
  "complexity": "simple|moderate|complex|massive",
  "memory_queries": ["query1", "query2"],
  "suggested_decomposition": ["step1", "step2"],
  "meta_agents_needed": ["critic", "verifier"],
  "reasoning": "Brief explanation",
  "estimated_iterations": 3,
  "needs_tests": false,
  "needs_docs": false,
  "needs_review": true,
  "is_refactor": false
}"""


class TaskAnalyzer:
    """
    Analyzes tasks to determine complexity and optimal execution strategy.

    Uses a quick AI call to evaluate the task before main execution begins.
    This allows for:
    - Smarter memory queries (not just the raw prompt)
    - Appropriate decomposition decisions
    - Meta-agent spawning when needed

    Example:
        >>> analyzer = TaskAnalyzer()
        >>> analysis = analyzer.analyze("Build a REST API with user authentication")
        >>> print(analysis.complexity)  # ComplexityLevel.COMPLEX
        >>> print(analysis.memory_queries)  # ['REST API patterns', 'authentication implementation']
    """

    def __init__(self, config: Optional[AnalyzerConfig] = None):
        self.config = config or AnalyzerConfig()

    def analyze(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskAnalysis:
        """
        Analyze a task to determine complexity and execution strategy.

        Args:
            task: The task description
            context: Optional additional context (file paths, project info, etc.)

        Returns:
            TaskAnalysis with complexity, queries, decomposition, etc.
        """
        # Short-circuit for force_complex mode (testing)
        if self.config.force_complex:
            return self._force_complex_analysis(task)

        # Quick heuristic check for trivial tasks
        if self._is_trivially_simple(task):
            return self._simple_analysis(task)

        # Use AI for non-trivial analysis
        try:
            return self._ai_analyze(task, context)
        except Exception as e:
            if self.config.verbose:
                print(f"[TaskAnalyzer] AI analysis failed: {e}, using heuristics")
            return self._heuristic_analysis(task)

    def _is_trivially_simple(self, task: str) -> bool:
        """Quick check for obviously simple tasks"""
        task_lower = task.lower().strip()

        # Very short tasks are usually simple
        if len(task_lower) < 30:
            simple_patterns = [
                "hello", "hi", "test", "print", "echo",
                "show", "list", "what is", "where is",
            ]
            return any(pattern in task_lower for pattern in simple_patterns)

        return False

    def _simple_analysis(self, task: str) -> TaskAnalysis:
        """Return analysis for trivially simple tasks"""
        return TaskAnalysis(
            complexity=ComplexityLevel.SIMPLE,
            memory_queries=[],  # No memory needed for simple tasks
            suggested_decomposition=[],
            meta_agents_needed=[],
            reasoning="Trivially simple task - direct execution",
            estimated_iterations=1,
        )

    def _force_complex_analysis(self, task: str) -> TaskAnalysis:
        """Force complex analysis for testing decomposition flow"""
        # Generate a meaningful memory query from the task
        # Extract key terms rather than just taking first 100 chars
        words = task.split()
        important_words = [w for w in words if len(w) > 4 and w.lower() not in
                         ['that', 'this', 'with', 'have', 'from', 'should', 'would', 'could',
                          'task', 'create', 'make', 'build', 'write', 'step']]
        memory_query = ' '.join(important_words[:15]) if important_words else task[:100]

        # Don't provide generic decomposition - let runtime generate specific steps
        # based on the actual task content
        return TaskAnalysis(
            complexity=ComplexityLevel.COMPLEX,
            memory_queries=[memory_query],
            suggested_decomposition=[],  # Empty = runtime will generate specific steps
            meta_agents_needed=["critic", "verifier"],  # Removed planner - not needed with good decomposition
            reasoning="Force complex mode enabled for testing",
            estimated_iterations=10,
            needs_tests=True,
            needs_docs=True,
            needs_review=True,
        )

    def _ai_analyze(self, task: str, context: Optional[Dict[str, Any]]) -> TaskAnalysis:
        """Use AI to analyze task complexity"""
        # Build the prompt
        prompt = f"Analyze this task:\n\n{task}"
        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        # Call claude with minimal context (fast, cheap)
        result = self._quick_claude_call(prompt)

        # Parse the JSON response
        return self._parse_analysis(result)

    def _quick_claude_call(self, prompt: str) -> str:
        """Make a quick Claude call for analysis (no context accumulation)"""
        import tempfile

        with tempfile.TemporaryDirectory(prefix="task_analyzer_") as tmpdir:
            # Call claude with system prompt and user prompt as positional arg
            cmd = [
                "claude",
                "-p", ANALYZER_SYSTEM_PROMPT,
                "--dangerously-skip-permissions",
                prompt,  # Pass the prompt as positional argument
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=60  # Quick timeout
            )

            return result.stdout

    def _parse_analysis(self, response: str) -> TaskAnalysis:
        """Parse AI response into TaskAnalysis"""
        import re

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not json_match:
            # Try multiline JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group())

                # Map complexity string to enum
                complexity_map = {
                    "simple": ComplexityLevel.SIMPLE,
                    "moderate": ComplexityLevel.MODERATE,
                    "complex": ComplexityLevel.COMPLEX,
                    "massive": ComplexityLevel.MASSIVE,
                }

                return TaskAnalysis(
                    complexity=complexity_map.get(data.get("complexity", "moderate"), ComplexityLevel.MODERATE),
                    memory_queries=data.get("memory_queries", []),
                    suggested_decomposition=data.get("suggested_decomposition", []),
                    meta_agents_needed=data.get("meta_agents_needed", []),
                    reasoning=data.get("reasoning", "AI analysis"),
                    estimated_iterations=data.get("estimated_iterations", 5),
                    needs_tests=data.get("needs_tests", False),
                    needs_docs=data.get("needs_docs", False),
                    needs_review=data.get("needs_review", False),
                    is_refactor=data.get("is_refactor", False),
                )
            except json.JSONDecodeError:
                pass

        # Fallback to heuristics if parsing fails
        return self._heuristic_analysis(response)

    def _heuristic_analysis(self, task: str) -> TaskAnalysis:
        """Fallback heuristic-based analysis"""
        task_lower = task.lower()

        # Keywords that suggest complexity
        complex_keywords = [
            "implement", "build", "create", "develop", "design",
            "refactor", "migrate", "integrate", "authentication",
            "api", "database", "system", "architecture",
        ]

        moderate_keywords = [
            "add", "update", "modify", "change", "fix", "improve",
            "function", "method", "class", "feature",
        ]

        # Count matches
        complex_count = sum(1 for kw in complex_keywords if kw in task_lower)
        moderate_count = sum(1 for kw in moderate_keywords if kw in task_lower)

        # Determine complexity
        if complex_count >= 2 or len(task) > 200:
            complexity = ComplexityLevel.COMPLEX
            meta_agents = ["critic", "verifier"]
            estimated = 8
        elif moderate_count >= 1 or len(task) > 100:
            complexity = ComplexityLevel.MODERATE
            meta_agents = ["critic"] if len(task) > 150 else []
            estimated = 4
        else:
            complexity = ComplexityLevel.SIMPLE
            meta_agents = []
            estimated = 2

        # Generate memory queries from task
        # Extract key terms (simple heuristic)
        words = task.split()
        important_words = [w for w in words if len(w) > 4 and w.lower() not in
                         ['that', 'this', 'with', 'have', 'from', 'should', 'would', 'could']]
        memory_query = ' '.join(important_words[:10]) if important_words else task[:100]

        return TaskAnalysis(
            complexity=complexity,
            memory_queries=[memory_query] if complexity != ComplexityLevel.SIMPLE else [],
            suggested_decomposition=[],
            meta_agents_needed=meta_agents,
            reasoning=f"Heuristic analysis: {complex_count} complex, {moderate_count} moderate keywords",
            estimated_iterations=estimated,
            needs_tests="test" in task_lower,
            needs_docs="doc" in task_lower or "readme" in task_lower,
            needs_review=complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.MASSIVE],
        )

    def should_decompose(self, analysis: TaskAnalysis) -> bool:
        """Determine if task should be decomposed based on analysis and config"""
        level = self.config.decomposition_level

        if level == DecompositionLevel.NONE:
            return False
        elif level == DecompositionLevel.AGGRESSIVE:
            return True  # Always decompose
        elif level == DecompositionLevel.STANDARD:
            return analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.MASSIVE]
        else:  # LIGHT
            return analysis.complexity == ComplexityLevel.MASSIVE

    def get_memory_queries(self, analysis: TaskAnalysis, task: str) -> List[str]:
        """Get optimized memory queries from analysis, with fallback to task"""
        if analysis.memory_queries:
            return analysis.memory_queries
        elif analysis.complexity != ComplexityLevel.SIMPLE:
            # Use task itself as query for non-simple tasks
            return [task[:200]]
        return []
