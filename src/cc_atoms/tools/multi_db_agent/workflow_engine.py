#!/usr/bin/env python3
"""
Workflow Engine: Intelligent Capability Composition

This is the NEXT LEVEL abstraction above the CapabilityRegistry.

While CapabilityRegistry provides:
- Discovery: Finding what capabilities exist
- Tracking: Recording usage and performance
- Basic Composition: Sequential step execution

The Workflow Engine provides:
- DAG Execution: Parallel execution where possible
- Conditional Branching: if/then/else based on outputs
- Smart Retry: Retry failed steps with alternative capabilities
- Resource Sharing: Shared context across all steps
- Self-Optimization: Learn from execution history to improve
- Dynamic Composition: Build workflows at runtime from task analysis

Architecture:
    ┌────────────────────────────────────────────────────────────────┐
    │                       Workflow Engine                          │
    ├────────────────────────────────────────────────────────────────┤
    │  • DAG Builder      → Constructs execution graph               │
    │  • Parallel Runner  → Executes independent steps concurrently  │
    │  • Branch Handler   → Evaluates conditions, routes execution   │
    │  • Context Manager  → Shares state across steps                │
    │  • Optimizer        → Learns from history, suggests changes    │
    │  • Auto-Composer    → Builds workflows from natural language   │
    └────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
            ┌──────────────┐              ┌──────────────┐
            │  Capability  │              │   Workflow   │
            │   Registry   │              │    Store     │
            └──────────────┘              └──────────────┘

Usage:
    from cc_atoms.tools.multi_db_agent.workflow_engine import WorkflowEngine

    engine = WorkflowEngine()

    # Create a workflow programmatically
    wf = engine.create_workflow("analyze-and-report")
    wf.add_step("search", capability="data-agent", params={"query": "{input}"})
    wf.add_step("analyze", capability="atom_runtime", params={"task": "Analyze: {search.output}"})
    wf.add_step("report", capability="atom_runtime", params={"task": "Generate report from: {analyze.output}"})
    wf.add_edge("search", "analyze")  # analyze depends on search
    wf.add_edge("analyze", "report")  # report depends on analyze

    # Or compose from natural language
    wf = engine.compose("search for auth code, analyze for vulnerabilities, generate report")

    # Execute with parallel optimization
    result = engine.execute(wf, input="authentication")

    # Get optimization suggestions
    suggestions = engine.optimize(wf)

Example - Parallel Execution:
    wf = engine.create_workflow("multi-search")
    wf.add_step("search_code", capability="data-agent", params={"query": "{input}", "type": "code"})
    wf.add_step("search_docs", capability="data-agent", params={"query": "{input}", "type": "document"})
    wf.add_step("combine", capability="atom_runtime", params={"task": "Combine results"})
    wf.add_edge("search_code", "combine")
    wf.add_edge("search_docs", "combine")
    # search_code and search_docs will run in PARALLEL, then combine runs

Example - Conditional Branching:
    wf = engine.create_workflow("smart-handler")
    wf.add_step("classify", capability="classify_query")
    wf.add_branch("classify",
        conditions=[
            ("output.type == 'code'", "code_handler"),
            ("output.type == 'doc'", "doc_handler"),
            ("default", "generic_handler")
        ])
"""
import os
import sys
import json
import time
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Callable, Set, Union
from enum import Enum
from collections import defaultdict


class StepStatus(Enum):
    """Status of a workflow step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeType(Enum):
    """Type of node in workflow DAG"""
    STEP = "step"           # Execute a capability
    BRANCH = "branch"       # Conditional routing
    MERGE = "merge"         # Join parallel branches
    PARALLEL = "parallel"   # Fork into parallel execution
    LOOP = "loop"           # Repeat until condition


@dataclass
class StepResult:
    """Result of executing a workflow step"""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    attempts: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    id: str
    node_type: NodeType = NodeType.STEP
    capability: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)

    # Execution config
    timeout_seconds: float = 300.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Fallback capability if primary fails
    fallback_capability: Optional[str] = None

    # For branch nodes
    conditions: List[Tuple[str, str]] = field(default_factory=list)  # (condition, target_step)

    # For loop nodes
    loop_condition: Optional[str] = None
    max_iterations: int = 10


@dataclass
class WorkflowContext:
    """Shared context across all workflow steps"""
    input: Any = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    start_time: Optional[datetime] = None

    def resolve(self, template: str) -> str:
        """Resolve template variables like {step.output} or {input}"""
        if not isinstance(template, str):
            return template

        result = template

        # Resolve {input}
        if "{input}" in result:
            result = result.replace("{input}", str(self.input or ""))

        # Resolve {step.output} patterns
        for step_id, output in self.outputs.items():
            placeholder = f"{{{step_id}.output}}"
            if placeholder in result:
                result = result.replace(placeholder, str(output or ""))

            # Also support {step.field} for dict outputs
            if isinstance(output, dict):
                for key, value in output.items():
                    placeholder = f"{{{step_id}.{key}}}"
                    if placeholder in result:
                        result = result.replace(placeholder, str(value))

        # Resolve {var.name} patterns
        for var_name, var_value in self.variables.items():
            placeholder = f"{{var.{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))

        return result


class Workflow:
    """
    A workflow is a directed acyclic graph (DAG) of steps.

    Steps can be:
    - Capability executions
    - Conditional branches
    - Parallel forks
    - Loops
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)  # step -> [dependencies]
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)  # step -> [dependents]
        self.entry_points: List[str] = []
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}

    def add_step(
        self,
        step_id: str,
        capability: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        node_type: NodeType = NodeType.STEP,
        **kwargs
    ) -> "Workflow":
        """Add a step to the workflow."""
        step = WorkflowStep(
            id=step_id,
            node_type=node_type,
            capability=capability,
            params=params or {},
            **kwargs
        )
        self.steps[step_id] = step
        return self

    def add_edge(self, from_step: str, to_step: str) -> "Workflow":
        """Add a dependency edge: to_step depends on from_step."""
        if from_step not in self.steps:
            raise ValueError(f"Unknown step: {from_step}")
        if to_step not in self.steps:
            raise ValueError(f"Unknown step: {to_step}")

        self.edges[to_step].append(from_step)
        self.reverse_edges[from_step].append(to_step)
        return self

    def add_branch(
        self,
        step_id: str,
        conditions: List[Tuple[str, str]],
    ) -> "Workflow":
        """
        Add conditional branching after a step.

        Args:
            step_id: The step that produces the value to branch on
            conditions: List of (condition, target_step) tuples
                       Use "default" as condition for fallback
        """
        if step_id not in self.steps:
            raise ValueError(f"Unknown step: {step_id}")

        branch_id = f"{step_id}_branch"
        self.add_step(
            branch_id,
            node_type=NodeType.BRANCH,
            conditions=conditions,
        )
        self.add_edge(step_id, branch_id)

        # Add edges to branch targets
        for _, target in conditions:
            if target in self.steps:
                self.add_edge(branch_id, target)

        return self

    def set_entry_points(self, steps: List[str]) -> "Workflow":
        """Set the entry point steps (those with no dependencies)."""
        self.entry_points = steps
        return self

    def get_entry_points(self) -> List[str]:
        """Get steps with no dependencies (starting points)."""
        if self.entry_points:
            return self.entry_points

        # Auto-detect: steps with no incoming edges
        all_steps = set(self.steps.keys())
        steps_with_deps = set(s for s, deps in self.edges.items() if deps)
        return list(all_steps - steps_with_deps)

    def get_dependencies(self, step_id: str) -> List[str]:
        """Get steps that must complete before this step."""
        return self.edges.get(step_id, [])

    def get_dependents(self, step_id: str) -> List[str]:
        """Get steps that depend on this step."""
        return self.reverse_edges.get(step_id, [])

    def get_parallel_groups(self) -> List[List[str]]:
        """
        Topologically sort steps into groups that can run in parallel.

        Returns list of lists, where each inner list contains steps
        that can run concurrently.
        """
        # Kahn's algorithm for topological sort with grouping
        in_degree = {s: len(self.edges.get(s, [])) for s in self.steps}
        groups = []
        remaining = set(self.steps.keys())

        while remaining:
            # Find all steps with no remaining dependencies
            ready = [s for s in remaining if in_degree.get(s, 0) == 0]

            if not ready:
                # Cycle detected or orphaned nodes
                break

            groups.append(ready)

            # Remove these steps and update in-degrees
            for step in ready:
                remaining.remove(step)
                for dependent in self.get_dependents(step):
                    in_degree[dependent] = in_degree.get(dependent, 1) - 1

        return groups

    def validate(self) -> List[str]:
        """Validate the workflow and return list of errors."""
        errors = []

        # Check for cycles
        visited = set()
        rec_stack = set()

        def has_cycle(step: str) -> bool:
            visited.add(step)
            rec_stack.add(step)

            for dep in self.get_dependents(step):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(step)
            return False

        for step in self.steps:
            if step not in visited:
                if has_cycle(step):
                    errors.append(f"Cycle detected involving step: {step}")
                    break

        # Check for dangling references
        for step_id, step in self.steps.items():
            if step.node_type == NodeType.BRANCH:
                for _, target in step.conditions:
                    if target not in self.steps and target != "END":
                        errors.append(f"Branch target '{target}' not found in step {step_id}")

        # Check entry points exist
        if not self.get_entry_points():
            errors.append("No entry points found (all steps have dependencies)")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": {
                sid: {
                    "id": s.id,
                    "node_type": s.node_type.value,
                    "capability": s.capability,
                    "params": s.params,
                    "conditions": s.conditions,
                    "timeout_seconds": s.timeout_seconds,
                    "max_retries": s.max_retries,
                }
                for sid, s in self.steps.items()
            },
            "edges": dict(self.edges),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """Deserialize workflow from dictionary."""
        wf = cls(name=data["name"], description=data.get("description", ""))

        for sid, step_data in data.get("steps", {}).items():
            wf.add_step(
                step_id=sid,
                capability=step_data.get("capability"),
                params=step_data.get("params", {}),
                node_type=NodeType(step_data.get("node_type", "step")),
                conditions=step_data.get("conditions", []),
                timeout_seconds=step_data.get("timeout_seconds", 300),
                max_retries=step_data.get("max_retries", 3),
            )

        for to_step, from_steps in data.get("edges", {}).items():
            for from_step in from_steps:
                wf.edges[to_step].append(from_step)
                wf.reverse_edges[from_step].append(to_step)

        wf.metadata = data.get("metadata", {})

        return wf


@dataclass
class WorkflowResult:
    """Result of executing a complete workflow"""
    workflow_name: str
    success: bool
    outputs: Dict[str, Any]
    step_results: Dict[str, StepResult]
    duration_seconds: float
    steps_completed: int
    steps_failed: int
    steps_skipped: int
    error: Optional[str] = None

    @property
    def final_output(self) -> Any:
        """Get the output of the last completed step."""
        if not self.step_results:
            return None

        # Find terminal steps (no dependents that completed)
        completed = [sid for sid, r in self.step_results.items()
                    if r.status == StepStatus.COMPLETED]

        if completed:
            return self.step_results[completed[-1]].output
        return None


class WorkflowEngine:
    """
    The Workflow Engine orchestrates capability composition.

    It builds on CapabilityRegistry to provide:
    - DAG-based workflow execution
    - Parallel step execution
    - Conditional branching
    - Smart retry with fallbacks
    - Execution optimization
    """

    def __init__(
        self,
        registry=None,
        max_workers: int = 4,
        verbose: bool = True,
    ):
        """
        Initialize the workflow engine.

        Args:
            registry: CapabilityRegistry instance (created if None)
            max_workers: Max parallel execution threads
            verbose: Print progress
        """
        self.max_workers = max_workers
        self.verbose = verbose

        # Initialize registry
        if registry:
            self._registry = registry
        else:
            try:
                from cc_atoms.tools.multi_db_agent.capability_registry import CapabilityRegistry
                self._registry = CapabilityRegistry(verbose=verbose)
            except ImportError:
                self._registry = None

        # Workflow storage
        self._workflows: Dict[str, Workflow] = {}
        self._execution_history: List[WorkflowResult] = []

        # Persistence
        self._store_path = Path.home() / ".cache" / "cc_atoms" / "workflow_store.json"
        self._load_workflows()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[Workflow] {msg}")

    # =========================================================================
    # WORKFLOW CREATION
    # =========================================================================

    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """Create a new workflow."""
        wf = Workflow(name=name, description=description)
        self._workflows[name] = wf
        return wf

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self._workflows.get(name)

    def list_workflows(self) -> List[str]:
        """List all workflow names."""
        return list(self._workflows.keys())

    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        if name in self._workflows:
            del self._workflows[name]
            self._save_workflows()
            return True
        return False

    # =========================================================================
    # AUTO-COMPOSITION
    # =========================================================================

    def compose(
        self,
        task_description: str,
        max_steps: int = 5,
    ) -> Workflow:
        """
        Automatically compose a workflow from natural language.

        Uses the capability registry to find matching capabilities
        and chains them together based on the task.

        Args:
            task_description: Natural language description of what to do
            max_steps: Maximum steps in generated workflow

        Returns:
            Auto-generated Workflow
        """
        if not self._registry:
            raise RuntimeError("CapabilityRegistry required for auto-composition")

        self._log(f"Auto-composing workflow for: {task_description}")

        # Parse task into potential steps
        # Simple heuristic: split by commas and "then"
        parts = task_description.replace(" then ", ", ").split(",")
        parts = [p.strip() for p in parts if p.strip()][:max_steps]

        if not parts:
            parts = [task_description]

        # Create workflow
        wf_name = f"auto_{hashlib.md5(task_description.encode()).hexdigest()[:8]}"
        wf = self.create_workflow(wf_name, description=task_description)

        prev_step = None
        for i, part in enumerate(parts):
            step_id = f"step_{i}"

            # Find matching capability
            matches = self._registry.match(part, max_results=1)

            if matches:
                cap, score = matches[0]
                capability = cap.name
                self._log(f"  Step {i}: '{part}' -> {capability} (score: {score:.2f})")
            else:
                # Fall back to atom_runtime for unknown tasks
                capability = "atom_runtime"
                self._log(f"  Step {i}: '{part}' -> atom_runtime (no match)")

            # Build params - use output from previous step
            params = {"task": part}
            if prev_step:
                params["input"] = f"{{{prev_step}.output}}"

            wf.add_step(step_id, capability=capability, params=params)

            if prev_step:
                wf.add_edge(prev_step, step_id)

            prev_step = step_id

        wf.metadata["auto_composed"] = True
        wf.metadata["source_task"] = task_description

        self._save_workflows()
        return wf

    # =========================================================================
    # EXECUTION
    # =========================================================================

    def execute(
        self,
        workflow: Union[str, Workflow],
        input: Any = None,
        variables: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 600.0,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            workflow: Workflow instance or name
            input: Initial input value
            variables: Additional context variables
            timeout_seconds: Total workflow timeout

        Returns:
            WorkflowResult with all step results
        """
        # Resolve workflow
        if isinstance(workflow, str):
            wf = self.get_workflow(workflow)
            if not wf:
                return WorkflowResult(
                    workflow_name=workflow,
                    success=False,
                    outputs={},
                    step_results={},
                    duration_seconds=0,
                    steps_completed=0,
                    steps_failed=0,
                    steps_skipped=0,
                    error=f"Workflow not found: {workflow}",
                )
        else:
            wf = workflow

        # Validate
        errors = wf.validate()
        if errors:
            return WorkflowResult(
                workflow_name=wf.name,
                success=False,
                outputs={},
                step_results={},
                duration_seconds=0,
                steps_completed=0,
                steps_failed=0,
                steps_skipped=0,
                error=f"Validation errors: {errors}",
            )

        # Initialize context
        context = WorkflowContext(
            input=input,
            variables=variables or {},
            start_time=datetime.now(),
        )

        start_time = time.time()
        self._log(f"Executing workflow: {wf.name}")

        try:
            # Get parallel execution groups
            groups = wf.get_parallel_groups()
            self._log(f"Execution groups: {len(groups)}")

            # Execute each group
            for group_idx, group in enumerate(groups):
                self._log(f"  Group {group_idx + 1}: {group}")

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    return self._build_result(
                        wf, context, start_time,
                        error="Workflow timeout exceeded"
                    )

                # Execute group (parallel if multiple steps)
                if len(group) == 1:
                    self._execute_step(wf.steps[group[0]], context, wf)
                else:
                    self._execute_parallel(
                        [wf.steps[s] for s in group],
                        context,
                        wf,
                    )

                # Check for failures that should stop execution
                for step_id in group:
                    result = context.step_results.get(step_id)
                    if result and result.status == StepStatus.FAILED:
                        step = wf.steps[step_id]
                        # Only stop if no fallback succeeded
                        if not context.outputs.get(step_id):
                            self._log(f"  Step {step_id} failed, stopping workflow")
                            return self._build_result(
                                wf, context, start_time,
                                error=f"Step {step_id} failed: {result.error}"
                            )

            # Success
            return self._build_result(wf, context, start_time)

        except Exception as e:
            return self._build_result(
                wf, context, start_time,
                error=f"Execution error: {type(e).__name__}: {e}"
            )

    def _execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
        workflow: Workflow,
    ):
        """Execute a single workflow step."""
        self._log(f"    Running: {step.id}")

        # Handle different node types
        if step.node_type == NodeType.BRANCH:
            return self._execute_branch(step, context, workflow)
        elif step.node_type == NodeType.MERGE:
            return self._execute_merge(step, context, workflow)

        # Regular step - execute capability
        start_time = time.time()
        result = StepResult(step_id=step.id, status=StepStatus.RUNNING)

        # Resolve parameters
        resolved_params = {}
        for key, value in step.params.items():
            resolved_params[key] = context.resolve(value)

        # Execute with retries
        last_error = None
        for attempt in range(1, step.max_retries + 1):
            try:
                output = self._execute_capability(
                    step.capability,
                    resolved_params,
                    timeout=step.timeout_seconds,
                )

                result.status = StepStatus.COMPLETED
                result.output = output
                result.duration_seconds = time.time() - start_time
                result.attempts = attempt

                context.outputs[step.id] = output
                context.step_results[step.id] = result

                self._log(f"    Completed: {step.id} ({result.duration_seconds:.1f}s)")
                return

            except Exception as e:
                last_error = str(e)
                self._log(f"    Retry {attempt}/{step.max_retries}: {step.id} - {e}")

                if attempt < step.max_retries:
                    time.sleep(step.retry_delay_seconds)

        # All retries failed - try fallback
        if step.fallback_capability:
            self._log(f"    Trying fallback: {step.fallback_capability}")
            try:
                output = self._execute_capability(
                    step.fallback_capability,
                    resolved_params,
                    timeout=step.timeout_seconds,
                )

                result.status = StepStatus.COMPLETED
                result.output = output
                result.metadata["used_fallback"] = True

                context.outputs[step.id] = output
                context.step_results[step.id] = result
                return

            except Exception as e:
                last_error = f"Fallback also failed: {e}"

        # Complete failure
        result.status = StepStatus.FAILED
        result.error = last_error
        result.duration_seconds = time.time() - start_time
        context.step_results[step.id] = result
        context.errors.append(f"{step.id}: {last_error}")

    def _execute_parallel(
        self,
        steps: List[WorkflowStep],
        context: WorkflowContext,
        workflow: Workflow,
    ):
        """Execute multiple steps in parallel."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._execute_step, step, context, workflow): step
                for step in steps
            }

            for future in as_completed(futures):
                step = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self._log(f"    Parallel error in {step.id}: {e}")

    def _execute_branch(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
        workflow: Workflow,
    ):
        """Execute a branch node - evaluate conditions and route."""
        # Get output from dependency
        deps = workflow.get_dependencies(step.id)
        if not deps:
            return

        source_output = context.outputs.get(deps[0])

        # Evaluate conditions
        selected_target = None
        for condition, target in step.conditions:
            if condition == "default":
                selected_target = target
            elif self._evaluate_condition(condition, source_output, context):
                selected_target = target
                break

        if selected_target and selected_target in workflow.steps:
            # Mark this branch as taken
            context.variables[f"{step.id}_target"] = selected_target
            self._log(f"    Branch {step.id} -> {selected_target}")

    def _execute_merge(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
        workflow: Workflow,
    ):
        """Execute a merge node - combine outputs from parallel branches."""
        deps = workflow.get_dependencies(step.id)
        merged = {}

        for dep in deps:
            if dep in context.outputs:
                merged[dep] = context.outputs[dep]

        context.outputs[step.id] = merged
        context.step_results[step.id] = StepResult(
            step_id=step.id,
            status=StepStatus.COMPLETED,
            output=merged,
        )

    def _execute_capability(
        self,
        capability_name: str,
        params: Dict[str, Any],
        timeout: float = 300.0,
    ) -> Any:
        """Execute a capability and return its output."""
        if not capability_name:
            raise ValueError("No capability specified")

        # Special handling for atom_runtime
        if capability_name == "atom_runtime":
            from cc_atoms.atom_core import AtomRuntime

            runtime = AtomRuntime.create_ephemeral(
                system_prompt="Complete the following task efficiently.",
                max_iterations=10,
                verbose=self.verbose,
            )

            task = params.get("task", params.get("input", ""))
            result = runtime.run(task)

            if result.get("success"):
                return result.get("output", "")
            else:
                raise RuntimeError(result.get("error", "Unknown error"))

        # Use registry to execute
        if self._registry:
            result = self._registry.execute(capability_name, **params)
            if result.success:
                return result.output
            else:
                raise RuntimeError(result.error or "Capability execution failed")

        raise ValueError(f"Cannot execute capability: {capability_name}")

    def _evaluate_condition(
        self,
        condition: str,
        output: Any,
        context: WorkflowContext,
    ) -> bool:
        """Evaluate a branch condition."""
        # Simple condition evaluation
        # Supports: output.field == 'value', output == 'value', contains, etc.

        try:
            # Build evaluation context
            eval_context = {
                "output": output,
                "input": context.input,
                "var": context.variables,
            }

            # Simple string matching
            if "==" in condition:
                left, right = condition.split("==", 1)
                left_val = self._resolve_path(left.strip(), eval_context)
                right_val = right.strip().strip("'\"")
                return str(left_val) == right_val

            if " in " in condition:
                needle, haystack = condition.split(" in ", 1)
                needle_val = self._resolve_path(needle.strip(), eval_context)
                haystack_val = self._resolve_path(haystack.strip(), eval_context)
                return needle_val in str(haystack_val)

            # Boolean output check
            if condition == "output":
                return bool(output)

        except Exception:
            pass

        return False

    def _resolve_path(self, path: str, context: Dict) -> Any:
        """Resolve a dotted path like 'output.type' in context."""
        parts = path.split(".")
        current = context

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    def _build_result(
        self,
        workflow: Workflow,
        context: WorkflowContext,
        start_time: float,
        error: Optional[str] = None,
    ) -> WorkflowResult:
        """Build the workflow result."""
        completed = sum(1 for r in context.step_results.values()
                       if r.status == StepStatus.COMPLETED)
        failed = sum(1 for r in context.step_results.values()
                    if r.status == StepStatus.FAILED)
        skipped = sum(1 for r in context.step_results.values()
                     if r.status == StepStatus.SKIPPED)

        result = WorkflowResult(
            workflow_name=workflow.name,
            success=error is None and failed == 0,
            outputs=context.outputs,
            step_results=context.step_results,
            duration_seconds=time.time() - start_time,
            steps_completed=completed,
            steps_failed=failed,
            steps_skipped=skipped,
            error=error,
        )

        # Record in history
        self._execution_history.append(result)
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-50:]

        return result

    # =========================================================================
    # OPTIMIZATION
    # =========================================================================

    def optimize(self, workflow: Union[str, Workflow]) -> Dict[str, Any]:
        """
        Analyze workflow and suggest optimizations.

        Returns suggestions for:
        - Parallel execution opportunities
        - Slow steps that could use faster alternatives
        - Error-prone steps that need fallbacks
        """
        if isinstance(workflow, str):
            wf = self.get_workflow(workflow)
            if not wf:
                return {"error": "Workflow not found"}
        else:
            wf = workflow

        suggestions = []

        # Find steps that could run in parallel but don't
        groups = wf.get_parallel_groups()
        parallel_opportunities = sum(1 for g in groups if len(g) > 1)

        if parallel_opportunities > 0:
            suggestions.append({
                "type": "parallelism",
                "message": f"{parallel_opportunities} groups can run in parallel",
                "details": [g for g in groups if len(g) > 1],
            })

        # Check for missing fallbacks on historically failing steps
        if self._registry:
            for step_id, step in wf.steps.items():
                if step.capability:
                    cap = self._registry.get(step.capability)
                    if cap and cap.success_rate < 0.8:
                        if not step.fallback_capability:
                            suggestions.append({
                                "type": "fallback",
                                "message": f"Step '{step_id}' uses '{step.capability}' with {cap.success_rate:.0%} success rate",
                                "suggestion": "Add a fallback capability",
                            })

        # Analyze execution history for this workflow
        recent_runs = [r for r in self._execution_history
                      if r.workflow_name == wf.name][-10:]

        if recent_runs:
            avg_duration = sum(r.duration_seconds for r in recent_runs) / len(recent_runs)
            success_rate = sum(1 for r in recent_runs if r.success) / len(recent_runs)

            slow_steps = []
            for run in recent_runs:
                for step_id, result in run.step_results.items():
                    if result.duration_seconds > avg_duration / len(wf.steps):
                        slow_steps.append(step_id)

            if slow_steps:
                from collections import Counter
                common_slow = Counter(slow_steps).most_common(3)
                suggestions.append({
                    "type": "performance",
                    "message": "Slow steps detected",
                    "details": common_slow,
                })

        return {
            "workflow": wf.name,
            "steps": len(wf.steps),
            "parallel_groups": len(groups),
            "suggestions": suggestions,
        }

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def _save_workflows(self):
        """Save workflows to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            name: wf.to_dict()
            for name, wf in self._workflows.items()
        }

        with open(self._store_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_workflows(self):
        """Load workflows from disk."""
        if not self._store_path.exists():
            return

        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)

            for name, wf_data in data.items():
                self._workflows[name] = Workflow.from_dict(wf_data)

        except Exception as e:
            self._log(f"Could not load workflows: {e}")

    # =========================================================================
    # INTROSPECTION
    # =========================================================================

    def print_workflow(self, workflow: Union[str, Workflow]):
        """Print a visual representation of a workflow."""
        if isinstance(workflow, str):
            wf = self.get_workflow(workflow)
            if not wf:
                print(f"Workflow not found: {workflow}")
                return
        else:
            wf = workflow

        print(f"\n{'='*60}")
        print(f"Workflow: {wf.name}")
        print(f"Description: {wf.description or 'N/A'}")
        print(f"{'='*60}")

        groups = wf.get_parallel_groups()

        for i, group in enumerate(groups):
            if len(group) > 1:
                print(f"\n[Parallel Group {i+1}]")
                for step_id in group:
                    step = wf.steps[step_id]
                    print(f"  ├── {step_id}: {step.capability or step.node_type.value}")
            else:
                step_id = group[0]
                step = wf.steps[step_id]
                deps = wf.get_dependencies(step_id)
                arrow = "└──" if i == len(groups) - 1 else "├──"
                print(f"\n{arrow} {step_id}: {step.capability or step.node_type.value}")
                if deps:
                    print(f"    (depends on: {', '.join(deps)})")


# =========================================================================
# CLI
# =========================================================================

def main():
    """CLI entry point for workflow engine."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Workflow Engine - Intelligent capability composition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  workflow-engine list                           # List all workflows
  workflow-engine show my-workflow               # Show workflow details
  workflow-engine compose "search, analyze"      # Auto-compose from description
  workflow-engine run my-workflow --input "foo"  # Execute workflow
  workflow-engine optimize my-workflow           # Get optimization suggestions
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List workflows")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show workflow details")
    show_parser.add_argument("name", help="Workflow name")

    # Compose command
    compose_parser = subparsers.add_parser("compose", help="Auto-compose workflow")
    compose_parser.add_argument("description", help="Task description")
    compose_parser.add_argument("--name", help="Workflow name")

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute workflow")
    run_parser.add_argument("name", help="Workflow name")
    run_parser.add_argument("--input", "-i", help="Input value")
    run_parser.add_argument("--timeout", type=float, default=600, help="Timeout seconds")

    # Optimize command
    opt_parser = subparsers.add_parser("optimize", help="Get optimization suggestions")
    opt_parser.add_argument("name", help="Workflow name")

    # Global args
    parser.add_argument("--quiet", "-q", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    engine = WorkflowEngine(verbose=not args.quiet)

    if args.command == "list":
        workflows = engine.list_workflows()
        if not workflows:
            print("No workflows defined.")
        else:
            print(f"\nWorkflows ({len(workflows)}):\n")
            for name in workflows:
                wf = engine.get_workflow(name)
                print(f"  {name}: {len(wf.steps)} steps - {wf.description or 'No description'}")
        return 0

    elif args.command == "show":
        engine.print_workflow(args.name)
        return 0

    elif args.command == "compose":
        wf = engine.compose(args.description)
        print(f"\nCreated workflow: {wf.name}")
        engine.print_workflow(wf)
        return 0

    elif args.command == "run":
        result = engine.execute(
            args.name,
            input=args.input,
            timeout_seconds=args.timeout,
        )

        print(f"\n{'='*60}")
        print(f"Workflow: {result.workflow_name}")
        print(f"Success: {result.success}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Steps: {result.steps_completed} completed, {result.steps_failed} failed")

        if result.error:
            print(f"Error: {result.error}")

        print(f"\nOutputs:")
        for step_id, output in result.outputs.items():
            preview = str(output)[:100]
            print(f"  {step_id}: {preview}")

        return 0 if result.success else 1

    elif args.command == "optimize":
        suggestions = engine.optimize(args.name)

        if "error" in suggestions:
            print(f"Error: {suggestions['error']}")
            return 1

        print(f"\n{'='*60}")
        print(f"Optimization Analysis: {suggestions['workflow']}")
        print(f"{'='*60}")
        print(f"Total steps: {suggestions['steps']}")
        print(f"Parallel groups: {suggestions['parallel_groups']}")

        if suggestions["suggestions"]:
            print(f"\nSuggestions:")
            for sug in suggestions["suggestions"]:
                print(f"\n  [{sug['type'].upper()}]")
                print(f"  {sug['message']}")
                if "suggestion" in sug:
                    print(f"  → {sug['suggestion']}")
                if "details" in sug:
                    print(f"  Details: {sug['details']}")
        else:
            print("\nNo optimization suggestions - workflow looks good!")

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
