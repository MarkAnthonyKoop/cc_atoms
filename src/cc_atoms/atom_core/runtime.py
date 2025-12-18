"""
Core atom orchestration engine - embeddable in any project

This module provides the main AtomRuntime class that orchestrates Claude Code
sessions with:
- Task analysis for complexity evaluation
- Smart memory queries based on task semantics
- Conditional decomposition based on complexity
- Meta-agent spawning (critic, verifier, planner)
- Quality gates before accepting completion
"""

import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from .retry import RetryManager
from .context import IterationHistory
from .claude_runner import ClaudeRunner
from .memory import MemoryProvider, check_memory_available
from .task_analyzer import (
    TaskAnalyzer, TaskAnalysis, AnalyzerConfig,
    ComplexityLevel, DecompositionLevel
)


class AtomRuntime:
    """
    Embeddable atom orchestration engine.

    Provides iteration, retry, and context accumulation for Claude Code sessions
    without CLI overhead. Can be embedded in any tool or project.

    New in v3:
    - Task analysis phase determines complexity upfront
    - Memory queries are AI-optimized based on task semantics
    - Meta-agents (critic, verifier) spawned for complex tasks
    - Quality gates check for red flags before accepting EXIT_LOOP_NOW

    Example:
        >>> runtime = AtomRuntime(
        ...     system_prompt="You are a helpful assistant",
        ...     conversation_dir=Path("/tmp/my-task")
        ... )
        >>> result = runtime.run("Solve my problem")
        >>> if result["success"]:
        ...     print("Task complete!")
    """

    def __init__(
        self,
        system_prompt: str,
        conversation_dir: Path,
        max_iterations: int = 25,
        exit_signal: str = "EXIT_LOOP_NOW",
        verbose: Optional[bool] = None,
        cleanup: bool = False,
        use_memory: Optional[bool] = None,
        memory_threshold: float = 0.45,
        # New v3 options
        use_task_analyzer: bool = True,
        decomposition_level: DecompositionLevel = DecompositionLevel.STANDARD,
        force_complex: bool = False,
        use_meta_agents: bool = True,
        quality_check: bool = True,
    ):
        """
        Create an atom runtime for orchestrated Claude Code execution.

        Args:
            system_prompt: System prompt for Claude (can include {max_iterations})
            conversation_dir: Directory where 'claude -c' runs.
            max_iterations: Maximum iterations before giving up
            exit_signal: String that signals task completion
            verbose: Whether to print iteration progress.
            cleanup: If True, delete USER_PROMPT.md after completion.
            use_memory: Whether to use memory context from home index.
            memory_threshold: Relevance threshold (0-1) for memory context.

            # New v3 options
            use_task_analyzer: Enable AI-based task analysis upfront
            decomposition_level: How aggressively to decompose tasks
            force_complex: For testing: treat all tasks as complex
            use_meta_agents: Enable critic, verifier, planner agents
            quality_check: Check for red flags before accepting EXIT
        """
        self.system_prompt = system_prompt
        self.conversation_dir = Path(conversation_dir)
        self.max_iterations = max_iterations
        self.exit_signal = exit_signal
        self.cleanup = cleanup

        # Smart default for verbose: True if terminal, False if piped
        if verbose is None:
            self.verbose = sys.stdout.isatty()
        else:
            self.verbose = verbose

        # v3 settings
        self.use_task_analyzer = use_task_analyzer
        self.decomposition_level = decomposition_level
        self.force_complex = force_complex
        self.use_meta_agents = use_meta_agents
        self.quality_check = quality_check

        # Initialize task analyzer
        if self.use_task_analyzer:
            analyzer_config = AnalyzerConfig(
                decomposition_level=decomposition_level,
                force_complex=force_complex,
                verbose=self.verbose,
            )
            self.task_analyzer = TaskAnalyzer(analyzer_config)
        else:
            self.task_analyzer = None

        # Initialize memory provider
        if use_memory is None:
            use_memory = check_memory_available()

        if use_memory:
            self.memory_provider = MemoryProvider(
                relevance_threshold=memory_threshold,
                enabled=True,
                verbose=self.verbose
            )
        else:
            self.memory_provider = None

        # Initialize components
        if self.verbose:
            self.retry_manager = RetryManager()
        else:
            self.retry_manager = RetryManager(on_retry_message=lambda msg, sec: None)

        self.history = IterationHistory()
        self.claude_runner = ClaudeRunner()

        # State
        self._task_analysis: Optional[TaskAnalysis] = None
        self._active_system_prompt: Optional[str] = None

    @classmethod
    def create_ephemeral(
        cls,
        system_prompt: str,
        max_iterations: int = 25,
        **kwargs
    ) -> 'AtomRuntime':
        """
        Create runtime with temporary conversation (auto-deleted after completion).
        """
        tmpdir = tempfile.mkdtemp(prefix="atom_session_")
        kwargs.setdefault('cleanup', True)
        kwargs.setdefault('verbose', False)
        # Ephemeral sessions usually don't need full analysis
        kwargs.setdefault('use_task_analyzer', False)
        kwargs.setdefault('use_meta_agents', False)
        return cls(
            system_prompt=system_prompt,
            conversation_dir=Path(tmpdir),
            max_iterations=max_iterations,
            **kwargs
        )

    def run(self, user_prompt: str) -> Dict[str, Any]:
        """
        Run atom iterations until complete or max iterations.

        The execution flow is:
        1. Analyze task complexity (if enabled)
        2. Form smart memory queries based on analysis
        3. Inject relevant memory context
        4. Run main iteration loop
        5. Spawn meta-agents if needed (critic, verifier)
        6. Quality gate check before accepting completion

        Returns:
            {
                "success": bool,
                "iterations": int,
                "output": str,
                "context": List[dict],
                "duration": float,
                "reason": str,  # If failed
                "error": Optional[str],
                "memory_used": bool,
                "task_analysis": Optional[dict],  # v3
                "meta_agents_run": List[str],     # v3
            }
        """
        start_time = time.time()
        result = {}
        memory_used = False
        meta_agents_run = []

        try:
            # Setup
            self._create_user_prompt(user_prompt)

            # Phase 1: Task Analysis
            if self.task_analyzer:
                if self.verbose:
                    print(f"{'='*60}\nPhase 1: Task Analysis\n{'='*60}\n")

                self._task_analysis = self.task_analyzer.analyze(user_prompt)

                if self.verbose:
                    print(f"Complexity: {self._task_analysis.complexity.value}")
                    print(f"Estimated iterations: {self._task_analysis.estimated_iterations}")
                    if self._task_analysis.memory_queries:
                        print(f"Memory queries: {self._task_analysis.memory_queries}")
                    if self._task_analysis.meta_agents_needed:
                        print(f"Meta-agents: {self._task_analysis.meta_agents_needed}")
                    print()

            # Phase 2: Memory Context (with smart queries)
            if self.memory_provider:
                memory_queries = self._get_memory_queries(user_prompt)

                if memory_queries:
                    if self.verbose:
                        print(f"{'='*60}\nPhase 2: Memory Lookup\n{'='*60}\n")

                    # Use the first (best) query for memory lookup
                    enhanced_prompt = self.memory_provider.enhance_prompt(
                        self.system_prompt, memory_queries[0]
                    )
                    if enhanced_prompt != self.system_prompt:
                        memory_used = True
                        if self.verbose:
                            print("[Memory] Relevant context found and injected\n")
                    self._active_system_prompt = enhanced_prompt
                else:
                    self._active_system_prompt = self.system_prompt
            else:
                self._active_system_prompt = self.system_prompt

            # Phase 3: Decomposition (if needed)
            should_decompose = self._should_decompose()
            if should_decompose:
                if self.verbose:
                    print(f"{'='*60}\nPhase 3: Task Decomposition\n{'='*60}\n")
                result = self._run_decomposed(user_prompt)
                result["memory_used"] = memory_used
                result["meta_agents_run"] = meta_agents_run
                result["task_analysis"] = self._analysis_to_dict()
                return result

            # Phase 4: Main Iteration Loop
            if self.verbose:
                phase_num = 4 if self.task_analyzer else 1
                print(f"{'='*60}\nPhase {phase_num}: Main Execution\n{'='*60}\n")

            main_result = self._run_iteration_loop()

            # Phase 5: Meta-agents (if enabled and task warrants)
            if self.use_meta_agents and self._should_run_meta_agents(main_result):
                if self.verbose:
                    print(f"\n{'='*60}\nPhase 5: Meta-Agent Review\n{'='*60}\n")
                meta_agents_run = self._run_meta_agents(main_result)

                # If critic found issues and we have iterations left, continue
                if self._critic_found_issues() and main_result.get("iterations", 0) < self.max_iterations - 2:
                    if self.verbose:
                        print("\n[Meta] Critic found issues, continuing iteration...\n")
                    # Resume iteration loop with remaining iterations
                    continue_result = self._continue_iteration_loop(
                        main_result.get("iterations", 0) + 1
                    )
                    main_result = continue_result

            # Phase 6: Quality Gate
            if self.quality_check and main_result.get("success"):
                if self.verbose:
                    print(f"\n{'='*60}\nPhase 6: Quality Gate\n{'='*60}\n")
                passes, issues = self._quality_gate_check(main_result.get("output", ""))

                if not passes:
                    if self.verbose:
                        print(f"[Quality] Red flags detected: {issues}")
                        print("[Quality] Continuing iteration to address issues...\n")

                    # Continue iterating if we have room
                    if main_result.get("iterations", 0) < self.max_iterations - 1:
                        continue_result = self._continue_iteration_loop(
                            main_result.get("iterations", 0) + 1
                        )
                        main_result = continue_result

            # Build final result
            main_result["memory_used"] = memory_used
            main_result["meta_agents_run"] = meta_agents_run
            main_result["task_analysis"] = self._analysis_to_dict()
            main_result["duration"] = time.time() - start_time

            return main_result

        except FileNotFoundError as e:
            return self._error_result("file_not_found", str(e), start_time, memory_used, meta_agents_run)

        except PermissionError as e:
            return self._error_result("permission_denied", str(e), start_time, memory_used, meta_agents_run)

        except Exception as e:
            return self._error_result("unexpected_error", f"{type(e).__name__}: {str(e)}", start_time, memory_used, meta_agents_run)

        finally:
            if self.cleanup:
                prompt_file = self.conversation_dir / "USER_PROMPT.md"
                prompt_file.unlink(missing_ok=True)

    def _get_memory_queries(self, user_prompt: str) -> List[str]:
        """Get optimized memory queries from task analysis or fallback to prompt"""
        if self._task_analysis:
            queries = self.task_analyzer.get_memory_queries(self._task_analysis, user_prompt)
            if queries:
                return queries

        # Fallback: use the prompt itself if not trivially simple
        if self._task_analysis and self._task_analysis.complexity != ComplexityLevel.SIMPLE:
            return [user_prompt[:200]]

        return []

    def _should_decompose(self) -> bool:
        """Determine if task should be decomposed"""
        if not self._task_analysis:
            return False
        return self.task_analyzer.should_decompose(self._task_analysis)

    def _run_decomposed(self, user_prompt: str) -> Dict[str, Any]:
        """Run task with decomposition into sub-atoms"""
        start_time = time.time()

        if self.verbose:
            print("Decomposing task into sub-atoms...\n")

        # Get suggested decomposition - must be specific, not generic
        steps = self._task_analysis.suggested_decomposition
        if not steps or steps == ["Plan and design", "Implement", "Test", "Document"]:
            # Generate specific steps based on the actual task
            steps = self._generate_specific_steps(user_prompt)

        completed_steps = []
        failed_steps = []
        step_errors = []

        for i, step in enumerate(steps):
            step_name = step[:50].lower().replace(' ', '_').replace('/', '_')
            step_dir = self.conversation_dir / f"step_{i+1}_{step_name}"
            step_dir.mkdir(parents=True, exist_ok=True)

            if self.verbose:
                print(f"\n--- Sub-atom {i+1}/{len(steps)}: {step} ---\n")

            # Create SPECIFIC sub-atom prompt with clear expectations
            sub_prompt = self._create_specific_sub_prompt(
                step=step,
                step_num=i+1,
                total_steps=len(steps),
                main_task=user_prompt,
                completed_steps=completed_steps,
                working_dir=str(self.conversation_dir),
            )

            # Write sub-prompt
            (step_dir / "USER_PROMPT.md").write_text(sub_prompt)

            # Run sub-atom (recursive, but with reduced settings)
            sub_runtime = AtomRuntime(
                system_prompt=self._active_system_prompt,
                conversation_dir=step_dir,
                max_iterations=max(5, self.max_iterations // len(steps)),
                exit_signal=self.exit_signal,
                verbose=self.verbose,
                use_task_analyzer=False,  # Don't re-analyze
                use_meta_agents=False,    # Meta-agents only at top level
                quality_check=False,      # Quality check only at top level
            )

            try:
                sub_result = sub_runtime.run(sub_prompt)

                if sub_result.get("success"):
                    completed_steps.append({
                        "step": step,
                        "output": sub_result.get("output", "")[:1000],
                        "dir": str(step_dir),
                    })
                    if self.verbose:
                        print(f"[Decompose] Step '{step}' completed successfully\n")
                else:
                    failed_steps.append(step)
                    error_info = sub_result.get("error") or sub_result.get("reason") or "Unknown error"
                    step_errors.append(f"{step}: {error_info}")
                    if self.verbose:
                        print(f"[Decompose] Step '{step}' failed: {error_info}\n")
                        if sub_result.get("output"):
                            print(f"[Decompose] Last output: {sub_result['output'][:200]}...\n")

            except Exception as e:
                failed_steps.append(step)
                step_errors.append(f"{step}: {type(e).__name__}: {str(e)}")
                if self.verbose:
                    print(f"[Decompose] Step '{step}' raised exception: {e}\n")

        # All steps done - create integration summary
        if completed_steps and not failed_steps:
            self._create_integration_summary(completed_steps, user_prompt)

        return {
            "success": len(failed_steps) == 0,
            "iterations": len(completed_steps),
            "output": self._format_decomposition_result(completed_steps, failed_steps),
            "context": self.history.get_all_iterations(),
            "duration": time.time() - start_time,
            "reason": f"Failed steps: {step_errors}" if failed_steps else None,
            "decomposition": {
                "steps": steps,
                "completed": [s["step"] for s in completed_steps],
                "failed": failed_steps,
                "errors": step_errors,
            }
        }

    def _generate_specific_steps(self, user_prompt: str) -> List[str]:
        """Generate specific decomposition steps based on the task.

        IMPORTANT: The order of checks matters - more specific patterns first.
        """
        prompt_lower = user_prompt.lower()

        # Check for BUILD/CREATE/CLONE tasks first (large implementation projects)
        # These take priority over simpler patterns
        build_keywords = ["build", "clone", "replicate", "create a complete", "create a full",
                         "implement a complete", "implement a full", "develop a"]
        is_large_build = any(kw in prompt_lower for kw in build_keywords) and len(user_prompt) > 200

        if is_large_build or ("cli" in prompt_lower and "build" in prompt_lower):
            # IMPORTANT: Each step must produce WORKING code that can be tested
            # Steps are ordered to build incrementally with verification
            return [
                "Phase 1 - Research: Thoroughly analyze the target system (run --help, explore all features, document every capability)",
                "Phase 2 - MVP: Create minimal working version that does ONE thing end-to-end (e.g., make an API call and print response). MUST BE RUNNABLE.",
                "Phase 3 - Core Loop: Implement the main execution loop (if agentic: tool call -> execute -> continue). Test with a real example.",
                "Phase 4 - First Feature: Implement ONE complete feature with tests. Verify it works by running it.",
                "Phase 5 - Expand Features: Add remaining features ONE AT A TIME. Run integration test after each.",
                "Phase 6 - Full Integration Test: Run a real end-to-end test that exercises the complete system. Fix ALL issues found.",
                "Phase 7 - Polish: Only after everything works - add docs, error handling, edge cases.",
            ]

        # API/REST projects
        if "api" in prompt_lower or "rest" in prompt_lower:
            return [
                "Design API endpoints and data models",
                "Implement route handlers and request validation",
                "Add database/storage integration",
                "Implement authentication and error handling",
                "Write API tests and documentation",
            ]

        # Refactoring tasks
        if "refactor" in prompt_lower:
            return [
                "Analyze current code structure and identify issues",
                "Create new module/class structure",
                "Migrate functionality to new structure",
                "Update imports and dependencies",
                "Verify tests pass and document changes",
            ]

        # Feature implementation (medium-sized)
        if "feature" in prompt_lower or "implement" in prompt_lower:
            return [
                "Understand requirements and design approach",
                "Implement core feature logic",
                "Add error handling and edge cases",
                "Write tests for the feature",
                "Document usage and update README",
            ]

        # Test-writing tasks (check AFTER build tasks to avoid false positives)
        # Only match if the PRIMARY intent is testing
        test_primary = ("write test" in prompt_lower or "create test" in prompt_lower or
                       "add test" in prompt_lower or prompt_lower.startswith("test"))
        if test_primary and not is_large_build:
            return [
                "Analyze the target code/module to understand what needs testing",
                "Create test file with imports and test class structure",
                "Write unit tests for core functionality",
                "Write edge case and error handling tests",
                "Run tests and fix any failures",
            ]

        # Generic decomposition for other tasks
        return [
            "Analyze: Read and understand the requirements in the main task",
            "Design: Plan the implementation approach and file structure",
            "Implement: Write the core code to accomplish the task",
            "Test: Verify the implementation works correctly",
            "Document: Update README and add any necessary documentation",
        ]

    def _create_specific_sub_prompt(
        self,
        step: str,
        step_num: int,
        total_steps: int,
        main_task: str,
        completed_steps: List[Dict],
        working_dir: str,
    ) -> str:
        """Create a specific, actionable sub-prompt with verification requirements"""
        context_section = self._format_completed_steps(completed_steps)

        # Determine if this is a verification-critical step
        requires_verification = any(kw in step.lower() for kw in
            ["mvp", "implement", "core", "feature", "integration", "test", "loop"])

        verification_section = ""
        if requires_verification:
            verification_section = """
## CRITICAL: Verification Required
Before signaling completion, you MUST:
1. Actually RUN the code you created
2. Verify it produces the expected output
3. If it fails, fix it before continuing
4. Include the actual output/test results in your completion report

DO NOT mark this step complete if the code doesn't work.
"""

        return f"""# Step {step_num} of {total_steps}: {step}

## Main Task (for context)
{main_task}

## Your Specific Task This Step
{step}

## What You Must Do
1. Focus ONLY on this specific step: "{step}"
2. Work in the parent directory: {working_dir}
3. Create/modify files as needed to complete this step
4. Be thorough but stay focused on this step only
{verification_section}
## Previous Steps Completed
{context_section}

## Expected Output
- Complete the specific task described above
- Create any necessary files in {working_dir} (not in this subdirectory)
- Provide a brief summary of what you accomplished
- If verification was required, include test/run output

## Completion
When this step is done AND verified (if required), output a summary of what you created/modified, then:

EXIT_LOOP_NOW
"""

    def _format_decomposition_result(self, completed: List[Dict], failed: List[str]) -> str:
        """Format the decomposition result as a readable summary"""
        parts = [f"Decomposition completed: {len(completed)}/{len(completed) + len(failed)} steps"]

        if completed:
            parts.append("\n## Completed Steps:")
            for step in completed:
                parts.append(f"- {step['step']}")
                if step.get('output'):
                    # Include first 200 chars of output
                    output_preview = step['output'][:200].replace('\n', ' ')
                    parts.append(f"  Output: {output_preview}...")

        if failed:
            parts.append("\n## Failed Steps:")
            for step in failed:
                parts.append(f"- {step}")

        return "\n".join(parts)

    def _create_integration_summary(self, completed_steps: List[Dict], main_task: str):
        """Create a summary of all completed work"""
        summary_file = self.conversation_dir / "DECOMPOSITION_SUMMARY.md"

        content = f"""# Decomposition Summary

## Original Task
{main_task}

## Completed Steps

"""
        for i, step in enumerate(completed_steps, 1):
            content += f"""### Step {i}: {step['step']}
{step.get('output', 'No output captured')[:500]}

"""

        content += """## Integration Notes
All steps completed. Review the outputs above and verify the work is correct.
"""
        summary_file.write_text(content)

    def _format_completed_steps(self, completed_steps: List[Dict]) -> str:
        """Format completed steps as context"""
        if not completed_steps:
            return "None yet."

        parts = []
        for step in completed_steps:
            parts.append(f"### {step['step']}\n{step['output'][:300]}...")
        return "\n\n".join(parts)

    def _run_iteration_loop(self) -> Dict[str, Any]:
        """Run the main iteration loop"""
        start_time = time.time()
        result = {}

        for iteration in range(1, self.max_iterations + 1):
            if self.verbose:
                print(f"{'='*60}\nIteration {iteration}/{self.max_iterations}\n{'='*60}\n")

            result = self._run_iteration_with_retry(iteration)

            if self._is_complete(result):
                return {
                    "success": True,
                    "iterations": iteration,
                    "output": result["stdout"],
                    "context": self.history.get_all_iterations(),
                    "duration": time.time() - start_time,
                }

            self.history.add_iteration(iteration, result)

        return {
            "success": False,
            "reason": "max_iterations",
            "iterations": self.max_iterations,
            "output": result.get("stdout", ""),
            "context": self.history.get_all_iterations(),
            "duration": time.time() - start_time,
        }

    def _continue_iteration_loop(self, start_iteration: int) -> Dict[str, Any]:
        """Continue iteration loop from a specific iteration"""
        start_time = time.time()
        result = {}

        for iteration in range(start_iteration, self.max_iterations + 1):
            if self.verbose:
                print(f"{'='*60}\nIteration {iteration}/{self.max_iterations} (continued)\n{'='*60}\n")

            result = self._run_iteration_with_retry(iteration)

            if self._is_complete(result):
                return {
                    "success": True,
                    "iterations": iteration,
                    "output": result["stdout"],
                    "context": self.history.get_all_iterations(),
                    "duration": time.time() - start_time,
                }

            self.history.add_iteration(iteration, result)

        return {
            "success": False,
            "reason": "max_iterations",
            "iterations": self.max_iterations,
            "output": result.get("stdout", ""),
            "context": self.history.get_all_iterations(),
            "duration": time.time() - start_time,
        }

    def _run_iteration_with_retry(self, iteration: int) -> Dict[str, Any]:
        """Run single iteration with infinite retry on errors."""
        base_prompt = getattr(self, '_active_system_prompt', self.system_prompt)
        # Use replace() instead of format() to avoid issues with curly braces in memory content
        prompt = base_prompt.replace('{max_iterations}', str(self.max_iterations))

        attempt = 0
        while True:
            attempt += 1
            stdout, returncode = self.claude_runner.run(prompt, self.conversation_dir)

            if self.verbose:
                print(stdout)

            should_retry, wait_seconds = self.retry_manager.check(
                stdout, returncode, attempt
            )

            if not should_retry:
                return {"stdout": stdout, "returncode": returncode}

            time.sleep(wait_seconds)

    def _is_complete(self, result: Dict[str, Any]) -> bool:
        """Check if task is complete"""
        return self.exit_signal in result.get("stdout", "")

    def _should_run_meta_agents(self, result: Dict[str, Any]) -> bool:
        """Determine if meta-agents should run"""
        if not result.get("success"):
            return False

        if self._task_analysis:
            # Run meta-agents if analysis recommends it
            return bool(self._task_analysis.meta_agents_needed)

        # Default: run for tasks that took multiple iterations
        return result.get("iterations", 0) >= 3

    def _run_meta_agents(self, main_result: Dict[str, Any]) -> List[str]:
        """Run meta-agents (critic, verifier, etc.)"""
        agents_run = []

        agents_needed = []
        if self._task_analysis:
            agents_needed = self._task_analysis.meta_agents_needed

        # If no specific agents recommended, use defaults for complex tasks
        if not agents_needed and self._task_analysis:
            if self._task_analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.MASSIVE]:
                agents_needed = ["critic"]
            if self._task_analysis.needs_tests:
                agents_needed.append("verifier")

        for agent in agents_needed:
            if self.verbose:
                print(f"\n[Meta] Running {agent} agent...\n")

            success = self._run_meta_agent(agent)
            if success:
                agents_run.append(agent)

        return agents_run

    def _run_meta_agent(self, agent_name: str) -> bool:
        """Run a specific meta-agent"""
        # Create meta-agent directory
        agent_dir = self.conversation_dir / f".meta_{agent_name}"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Load agent prompt
        agent_prompt = self._load_meta_agent_prompt(agent_name)
        if not agent_prompt:
            if self.verbose:
                print(f"[Meta] Could not load prompt for {agent_name}")
            return False

        # Copy context to agent dir
        user_prompt = (self.conversation_dir / "USER_PROMPT.md").read_text()
        (agent_dir / "USER_PROMPT.md").write_text(user_prompt)

        # Run agent
        sub_runtime = AtomRuntime(
            system_prompt=agent_prompt,
            conversation_dir=agent_dir,
            max_iterations=5,  # Meta-agents are quick
            exit_signal=self.exit_signal,
            verbose=self.verbose,
            use_task_analyzer=False,
            use_meta_agents=False,
            quality_check=False,
        )
        result = sub_runtime.run(f"Review the work in {self.conversation_dir}")

        return result.get("success", False)

    def _load_meta_agent_prompt(self, agent_name: str) -> Optional[str]:
        """Load meta-agent prompt from prompts directory"""
        from cc_atoms.config import PACKAGE_PROMPTS_DIR, PROMPTS_DIR

        # Check package prompts first, then global
        search_paths = [
            PACKAGE_PROMPTS_DIR / "meta_agents" / f"{agent_name.upper()}.md",
            PROMPTS_DIR / "meta_agents" / f"{agent_name.upper()}.md",
        ]

        for path in search_paths:
            if path.exists():
                return path.read_text()

        return None

    def _critic_found_issues(self) -> bool:
        """Check if critic agent found issues that need addressing"""
        critique_file = self.conversation_dir / ".meta_critic" / "CRITIQUE.md"
        if not critique_file.exists():
            return False

        content = critique_file.read_text().lower()
        return "needs_work" in content or "critical" in content

    def _quality_gate_check(self, output: str) -> tuple:
        """Check output for red flags before accepting completion"""
        from cc_atoms.config import RED_FLAG_PATTERNS

        output_lower = output.lower()
        issues = []

        for pattern in RED_FLAG_PATTERNS:
            if pattern.lower() in output_lower:
                issues.append(pattern)

        return (len(issues) == 0, issues)

    def _analysis_to_dict(self) -> Optional[Dict[str, Any]]:
        """Convert task analysis to dict for result"""
        if not self._task_analysis:
            return None

        return {
            "complexity": self._task_analysis.complexity.value,
            "estimated_iterations": self._task_analysis.estimated_iterations,
            "memory_queries": self._task_analysis.memory_queries,
            "meta_agents_needed": self._task_analysis.meta_agents_needed,
            "needs_tests": self._task_analysis.needs_tests,
            "needs_docs": self._task_analysis.needs_docs,
            "reasoning": self._task_analysis.reasoning,
        }

    def _error_result(self, reason: str, error: str, start_time: float,
                      memory_used: bool, meta_agents_run: List[str]) -> Dict[str, Any]:
        """Build error result dict"""
        return {
            "success": False,
            "reason": reason,
            "error": error,
            "iterations": len(self.history.get_all_iterations()),
            "output": "",
            "context": self.history.get_all_iterations(),
            "duration": time.time() - start_time,
            "memory_used": memory_used,
            "meta_agents_run": meta_agents_run,
            "task_analysis": self._analysis_to_dict(),
        }

    def _create_user_prompt(self, user_prompt: str):
        """Create USER_PROMPT.md in conversation directory"""
        self.conversation_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = self.conversation_dir / "USER_PROMPT.md"
        prompt_file.write_text(user_prompt)
