#!/usr/bin/env python3
"""
Capability Registry: The Missing Abstraction Layer

This module provides runtime discovery, registration, and composition of
capabilities in the cc_atoms ecosystem.

The key insight: Tools exist, but there's no way to programmatically discover
what they can do, how well they perform, or how to compose them.

The Capability Registry provides:

1. DISCOVERY - Scans tools/ and prompts/ directories to find capabilities
2. REGISTRATION - Creates structured metadata for each capability
3. COMPOSITION - Enables combining capabilities into workflows
4. TRACKING - Records usage and effectiveness
5. MATCHING - Finds the best capability for a given task

This is the "atom" of the next layer up - instead of working with raw tools,
you work with composable, tracked, discoverable capabilities.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │                    Capability Registry                    │
    ├──────────────────────────────────────────────────────────┤
    │  • Discovery Engine    → Scans for capabilities          │
    │  • Capability Graph    → Tracks relationships            │
    │  • Performance Index   → Records effectiveness           │
    │  • Composition Engine  → Combines capabilities           │
    └──────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
    ┌────────┐           ┌────────┐           ┌────────┐
    │ Tools  │           │Prompts │           │Learned │
    └────────┘           └────────┘           └────────┘

Usage:
    from cc_atoms.tools.multi_db_agent.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()

    # Discover all capabilities
    caps = registry.discover()

    # Find best capability for a task
    best = registry.match("analyze code for security issues")

    # Compose capabilities
    workflow = registry.compose(["search", "analyze", "report"])

    # Execute with tracking
    result = registry.execute("search", query="authentication")

    # Get performance insights
    insights = registry.analyze()
"""
import os
import sys
import json
import time
import hashlib
import importlib
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Callable, Set
from enum import Enum


class CapabilityType(Enum):
    """Types of capabilities in the registry"""
    TOOL = "tool"             # Python tool in tools/
    PROMPT = "prompt"         # System prompt in prompts/
    COMPOSED = "composed"     # Composition of multiple capabilities
    RUNTIME = "runtime"       # Runtime-defined capability
    EXTERNAL = "external"     # External command or service


class CapabilityStatus(Enum):
    """Status of a capability"""
    ACTIVE = "active"         # Working and available
    DEPRECATED = "deprecated" # Still works but discouraged
    BROKEN = "broken"         # Known to be broken
    UNTESTED = "untested"     # Never been tested


@dataclass
class CapabilitySignature:
    """Function signature for a capability"""
    inputs: Dict[str, str]    # name -> type
    outputs: Dict[str, str]   # name -> type
    required: List[str]       # Required input names
    optional: Dict[str, Any]  # Optional inputs with defaults


@dataclass
class CapabilityMetadata:
    """Rich metadata for a capability"""
    name: str
    type: CapabilityType
    description: str
    path: Optional[Path] = None
    status: CapabilityStatus = CapabilityStatus.UNTESTED

    # Taxonomy
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    domain: str = "general"

    # Signature
    signature: Optional[CapabilitySignature] = None

    # Dependencies
    requires: List[str] = field(default_factory=list)  # Other capabilities
    provides: List[str] = field(default_factory=list)  # What it provides

    # Performance
    usage_count: int = 0
    success_count: int = 0
    total_duration: float = 0.0
    last_used: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    average_iterations: float = 0.0

    # Documentation
    examples: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 1.0
        return self.success_count / self.usage_count

    @property
    def average_duration(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.total_duration / self.usage_count

    @property
    def effectiveness_score(self) -> float:
        """Composite score combining multiple factors"""
        # Weight factors
        success_weight = 0.5
        speed_weight = 0.2
        recency_weight = 0.3

        # Success factor (0-1)
        success_factor = self.success_rate

        # Speed factor (faster = better, normalized to 0-1)
        # Assume 60s is "average", faster gets bonus, slower gets penalty
        if self.average_duration == 0:
            speed_factor = 0.5
        else:
            speed_factor = min(1.0, 60.0 / max(1.0, self.average_duration))

        # Recency factor (used recently = bonus)
        if self.last_success:
            hours_ago = (datetime.now() - self.last_success).total_seconds() / 3600
            recency_factor = max(0, 1.0 - (hours_ago / 168))  # Decay over 1 week
        else:
            recency_factor = 0.5

        return (
            success_weight * success_factor +
            speed_weight * speed_factor +
            recency_weight * recency_factor
        )


@dataclass
class ComposedCapability:
    """A workflow composed of multiple capabilities"""
    name: str
    description: str
    steps: List[str]  # Capability names in order
    data_flow: Dict[str, str]  # How outputs connect to inputs


@dataclass
class ExecutionResult:
    """Result of executing a capability"""
    capability: str
    success: bool
    output: Any
    duration_seconds: float
    iterations: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """
    Central registry for discovering, tracking, and composing capabilities.

    The registry provides a unified interface for working with all types
    of capabilities in the cc_atoms ecosystem.
    """

    def __init__(
        self,
        cc_atoms_root: Optional[Path] = None,
        auto_discover: bool = True,
        verbose: bool = True,
    ):
        """
        Initialize the capability registry.

        Args:
            cc_atoms_root: Path to cc_atoms directory (auto-detected if None)
            auto_discover: Run discovery on init
            verbose: Print progress info
        """
        self.verbose = verbose

        # Auto-detect cc_atoms root
        if cc_atoms_root:
            self.root = Path(cc_atoms_root)
        else:
            for candidate in [
                Path.home() / "claude" / "cc",
                Path.home() / "cc_atoms",
                Path(__file__).parent.parent.parent.parent.parent,
            ]:
                if candidate.exists() and (candidate / "src" / "cc_atoms").exists():
                    self.root = candidate
                    break
            else:
                self.root = Path.home() / "claude" / "cc"

        # Directory paths
        self.tools_dir = self.root / "src" / "cc_atoms" / "tools"
        self.prompts_dir = self.root / "src" / "cc_atoms" / "prompts"

        # Registry storage
        self._capabilities: Dict[str, CapabilityMetadata] = {}
        self._compositions: Dict[str, ComposedCapability] = {}
        self._execution_log: List[ExecutionResult] = []

        # Persistence
        self._state_file = Path.home() / ".cache" / "cc_atoms" / "capability_registry.json"

        # Load saved state
        self._load_state()

        # Run initial discovery
        if auto_discover:
            self.discover()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[Registry] {msg}")

    # =========================================================================
    # DISCOVERY - Finding Capabilities
    # =========================================================================

    def discover(self, refresh: bool = False) -> Dict[str, CapabilityMetadata]:
        """
        Discover all capabilities in the ecosystem.

        Scans:
        - tools/ for Python tools
        - prompts/ for system prompts
        - Runtime-registered capabilities

        Args:
            refresh: Force re-scan even if cached

        Returns:
            Dictionary of capability name -> metadata
        """
        if self._capabilities and not refresh:
            return self._capabilities

        self._log("Discovering capabilities...")

        # Discover tools
        self._discover_tools()

        # Discover prompts
        self._discover_prompts()

        # Discover atom_core capabilities
        self._discover_core()

        self._log(f"Found {len(self._capabilities)} capabilities")
        self._save_state()

        return self._capabilities

    def _discover_tools(self):
        """Scan tools directory for available tools."""
        if not self.tools_dir.exists():
            self._log(f"Tools dir not found: {self.tools_dir}")
            return

        for tool_dir in self.tools_dir.iterdir():
            if not tool_dir.is_dir() or tool_dir.name.startswith("_"):
                continue

            # Look for main Python file
            main_file = tool_dir / f"{tool_dir.name}.py"
            if not main_file.exists():
                init_file = tool_dir / "__init__.py"
                if init_file.exists():
                    main_file = init_file
                else:
                    continue

            # Extract metadata
            description, signature, tags, examples = self._analyze_tool(tool_dir, main_file)

            # Create capability
            cap = CapabilityMetadata(
                name=tool_dir.name,
                type=CapabilityType.TOOL,
                description=description,
                path=tool_dir,
                tags=tags,
                signature=signature,
                examples=examples,
                category=self._infer_category(tool_dir.name, description),
                domain=self._infer_domain(tool_dir.name, description),
            )

            # Merge with existing data if present
            if tool_dir.name in self._capabilities:
                existing = self._capabilities[tool_dir.name]
                cap.usage_count = existing.usage_count
                cap.success_count = existing.success_count
                cap.total_duration = existing.total_duration
                cap.last_used = existing.last_used
                cap.last_success = existing.last_success
                cap.average_iterations = existing.average_iterations

            self._capabilities[tool_dir.name] = cap

    def _discover_prompts(self):
        """Scan prompts directory for system prompts."""
        if not self.prompts_dir.exists():
            self._log(f"Prompts dir not found: {self.prompts_dir}")
            return

        for prompt_file in self.prompts_dir.glob("*.md"):
            if prompt_file.name.startswith("_"):
                continue

            name = f"prompt_{prompt_file.stem.lower()}"

            # Read and analyze prompt
            try:
                content = prompt_file.read_text()
                description = self._extract_prompt_description(content)
                tags = self._extract_prompt_tags(content)
            except Exception:
                description = f"Prompt: {prompt_file.stem}"
                tags = []

            cap = CapabilityMetadata(
                name=name,
                type=CapabilityType.PROMPT,
                description=description,
                path=prompt_file,
                tags=tags,
                category="prompt",
            )

            self._capabilities[name] = cap

    def _discover_core(self):
        """Discover atom_core capabilities."""
        core_caps = [
            CapabilityMetadata(
                name="atom_runtime",
                type=CapabilityType.RUNTIME,
                description="Core orchestration engine for iterative Claude sessions",
                tags=["core", "runtime", "orchestration"],
                category="core",
                provides=["iteration", "retry", "context_accumulation"],
            ),
            CapabilityMetadata(
                name="memory_provider",
                type=CapabilityType.RUNTIME,
                description="RAG-based memory context injection from indexed files",
                tags=["core", "memory", "rag", "context"],
                category="core",
                provides=["semantic_search", "context_injection"],
            ),
            CapabilityMetadata(
                name="prompt_loader",
                type=CapabilityType.RUNTIME,
                description="Loads and composes system prompts from search paths",
                tags=["core", "prompt", "loader"],
                category="core",
                provides=["prompt_loading", "prompt_composition"],
            ),
        ]

        for cap in core_caps:
            self._capabilities[cap.name] = cap

    def _analyze_tool(
        self,
        tool_dir: Path,
        main_file: Path
    ) -> Tuple[str, Optional[CapabilitySignature], List[str], List[str]]:
        """Analyze a tool to extract metadata."""
        description = "Tool: " + tool_dir.name
        signature = None
        tags = []
        examples = []

        # Try README first
        readme = tool_dir / "README.md"
        if readme.exists():
            try:
                content = readme.read_text()[:2000]

                # Extract description
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith("#"):
                        desc_lines = []
                        for j in range(i, min(i + 5, len(lines))):
                            if not lines[j].strip():
                                break
                            desc_lines.append(lines[j])
                        description = " ".join(desc_lines)[:400]
                        break

                # Extract examples from code blocks
                import re
                code_blocks = re.findall(r"```(?:bash|python|sh)?\n(.*?)```", content, re.DOTALL)
                examples = [block.strip()[:200] for block in code_blocks[:3]]
            except Exception:
                pass

        # Try main file docstring
        try:
            content = main_file.read_text()[:3000]
            if '"""' in content:
                start = content.index('"""') + 3
                end = content.index('"""', start)
                docstring = content[start:end].strip()
                if len(docstring) > len(description):
                    description = docstring[:400]

            # Extract function signatures
            import re
            main_func = re.search(r"def main\((.*?)\)", content)
            if main_func:
                args_str = main_func.group(1)
                inputs = {}
                for arg in args_str.split(","):
                    if ":" in arg:
                        name, type_ = arg.split(":")
                        inputs[name.strip()] = type_.strip()
                signature = CapabilitySignature(
                    inputs=inputs,
                    outputs={"result": "Any"},
                    required=list(inputs.keys()),
                    optional={},
                )
        except Exception:
            pass

        # Infer tags
        tags = self._infer_tags(tool_dir.name, description)

        return description, signature, tags, examples

    def _extract_prompt_description(self, content: str) -> str:
        """Extract description from prompt content."""
        lines = content.split("\n")
        for line in lines:
            if line.strip() and not line.startswith("#"):
                return line.strip()[:200]
        return "Specialized prompt"

    def _extract_prompt_tags(self, content: str) -> List[str]:
        """Extract tags from prompt content."""
        tags = []
        content_lower = content.lower()

        tag_keywords = {
            "automation": ["automat", "workflow", "pipeline"],
            "analysis": ["analyz", "review", "inspect", "audit"],
            "creation": ["creat", "generat", "scaffold", "build"],
            "testing": ["test", "verif", "validat"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(tag)

        return tags

    def _infer_tags(self, name: str, description: str) -> List[str]:
        """Infer tags from name and description."""
        tags = []
        text = f"{name} {description}".lower()

        tag_keywords = {
            "gui": ["gui", "window", "click", "screen", "visual", "ui"],
            "data": ["data", "index", "search", "query", "database", "vector"],
            "analysis": ["analyze", "review", "check", "inspect", "audit"],
            "automation": ["automate", "automatic", "daemon", "monitor", "agent"],
            "sync": ["sync", "synchronize", "update", "refresh", "index"],
            "create": ["create", "generate", "scaffold", "new", "build"],
            "test": ["test", "verify", "validate", "check", "qa"],
            "llm": ["claude", "gemini", "llm", "ai", "model", "embedding"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        return tags

    def _infer_category(self, name: str, description: str) -> str:
        """Infer category from name and description."""
        text = f"{name} {description}".lower()

        if any(kw in text for kw in ["gui", "window", "click", "visual"]):
            return "interface"
        elif any(kw in text for kw in ["data", "database", "index", "vector"]):
            return "data"
        elif any(kw in text for kw in ["automat", "agent", "daemon"]):
            return "automation"
        elif any(kw in text for kw in ["sync", "upload", "download"]):
            return "integration"
        elif any(kw in text for kw in ["analyz", "review", "audit"]):
            return "analysis"
        else:
            return "general"

    def _infer_domain(self, name: str, description: str) -> str:
        """Infer domain from name and description."""
        text = f"{name} {description}".lower()

        if any(kw in text for kw in ["code", "python", "programming", "refactor"]):
            return "development"
        elif any(kw in text for kw in ["file", "document", "pdf", "text"]):
            return "documents"
        elif any(kw in text for kw in ["web", "browser", "http", "api"]):
            return "web"
        elif any(kw in text for kw in ["macos", "system", "screen"]):
            return "system"
        else:
            return "general"

    # =========================================================================
    # REGISTRATION - Adding Capabilities
    # =========================================================================

    def register(
        self,
        name: str,
        description: str,
        type_: CapabilityType = CapabilityType.RUNTIME,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> CapabilityMetadata:
        """
        Register a new capability.

        Args:
            name: Unique name for the capability
            description: What it does
            type_: Type of capability
            tags: Categorization tags
            **kwargs: Additional metadata

        Returns:
            The registered capability
        """
        cap = CapabilityMetadata(
            name=name,
            type=type_,
            description=description,
            tags=tags or [],
            **kwargs
        )

        self._capabilities[name] = cap
        self._save_state()

        self._log(f"Registered capability: {name}")
        return cap

    def unregister(self, name: str) -> bool:
        """Remove a capability from the registry."""
        if name in self._capabilities:
            del self._capabilities[name]
            self._save_state()
            return True
        return False

    # =========================================================================
    # MATCHING - Finding Capabilities
    # =========================================================================

    def get(self, name: str) -> Optional[CapabilityMetadata]:
        """Get a capability by name."""
        return self._capabilities.get(name)

    def list(
        self,
        tag: Optional[str] = None,
        type_: Optional[CapabilityType] = None,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        min_effectiveness: float = 0.0,
    ) -> List[CapabilityMetadata]:
        """
        List capabilities with optional filtering.

        Args:
            tag: Filter by tag
            type_: Filter by type
            category: Filter by category
            domain: Filter by domain
            min_effectiveness: Minimum effectiveness score

        Returns:
            List of matching capabilities, sorted by effectiveness
        """
        caps = list(self._capabilities.values())

        if tag:
            caps = [c for c in caps if tag in c.tags]
        if type_:
            caps = [c for c in caps if c.type == type_]
        if category:
            caps = [c for c in caps if c.category == category]
        if domain:
            caps = [c for c in caps if c.domain == domain]
        if min_effectiveness > 0:
            caps = [c for c in caps if c.effectiveness_score >= min_effectiveness]

        caps.sort(key=lambda c: c.effectiveness_score, reverse=True)
        return caps

    def match(
        self,
        task: str,
        max_results: int = 5,
        min_score: float = 0.3,
    ) -> List[Tuple[CapabilityMetadata, float]]:
        """
        Find capabilities that match a task description.

        Uses keyword matching and tag inference to find relevant capabilities.
        For better matching, consider using the semantic search via memory.

        Args:
            task: Task description
            max_results: Maximum results to return
            min_score: Minimum match score (0-1)

        Returns:
            List of (capability, score) tuples sorted by score
        """
        task_lower = task.lower()
        task_words = set(task_lower.split())
        task_tags = self._infer_tags("", task)

        results = []

        for cap in self._capabilities.values():
            # Calculate match score
            score = 0.0

            # Tag overlap
            cap_tags = set(cap.tags)
            tag_overlap = len(task_tags) & len(cap_tags)
            if task_tags:
                score += 0.3 * (tag_overlap / len(task_tags))

            # Keyword match in description
            desc_lower = cap.description.lower()
            keyword_matches = sum(1 for word in task_words if word in desc_lower)
            if task_words:
                score += 0.3 * (keyword_matches / len(task_words))

            # Name match
            if cap.name.lower() in task_lower:
                score += 0.2

            # Effectiveness boost
            score += 0.2 * cap.effectiveness_score

            if score >= min_score:
                results.append((cap, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def suggest(self, task: str) -> Optional[CapabilityMetadata]:
        """
        Suggest the single best capability for a task.

        Args:
            task: Task description

        Returns:
            Best matching capability, or None
        """
        matches = self.match(task, max_results=1)
        if matches:
            return matches[0][0]
        return None

    # =========================================================================
    # COMPOSITION - Combining Capabilities
    # =========================================================================

    def compose(
        self,
        name: str,
        description: str,
        steps: List[str],
        data_flow: Optional[Dict[str, str]] = None,
    ) -> ComposedCapability:
        """
        Create a composed capability from multiple capabilities.

        Args:
            name: Name for the composition
            description: What it does
            steps: Ordered list of capability names
            data_flow: How outputs connect to inputs

        Returns:
            The composed capability
        """
        # Verify all steps exist
        for step in steps:
            if step not in self._capabilities:
                raise ValueError(f"Unknown capability in composition: {step}")

        composition = ComposedCapability(
            name=name,
            description=description,
            steps=steps,
            data_flow=data_flow or {},
        )

        self._compositions[name] = composition

        # Also register as a capability
        self.register(
            name=name,
            description=description,
            type_=CapabilityType.COMPOSED,
            tags=["composed"],
            requires=steps,
        )

        self._save_state()
        return composition

    # =========================================================================
    # EXECUTION - Using Capabilities
    # =========================================================================

    def execute(
        self,
        name: str,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute a capability with tracking.

        Args:
            name: Capability name
            **kwargs: Arguments for the capability

        Returns:
            ExecutionResult with output and metadata
        """
        cap = self.get(name)
        if not cap:
            return ExecutionResult(
                capability=name,
                success=False,
                output=None,
                duration_seconds=0,
                error=f"Capability not found: {name}",
            )

        start_time = time.time()
        result = ExecutionResult(
            capability=name,
            success=False,
            output=None,
            duration_seconds=0,
        )

        try:
            if cap.type == CapabilityType.TOOL:
                result = self._execute_tool(cap, **kwargs)
            elif cap.type == CapabilityType.COMPOSED:
                result = self._execute_composed(name, **kwargs)
            elif cap.type == CapabilityType.PROMPT:
                result = self._execute_prompt(cap, **kwargs)
            else:
                result.error = f"Cannot execute capability type: {cap.type}"
        except Exception as e:
            result.error = f"{type(e).__name__}: {str(e)}"

        result.duration_seconds = time.time() - start_time

        # Update tracking
        self._record_execution(cap, result)

        return result

    def _execute_tool(self, cap: CapabilityMetadata, **kwargs) -> ExecutionResult:
        """Execute a tool capability."""
        if not cap.path:
            return ExecutionResult(
                capability=cap.name,
                success=False,
                output=None,
                duration_seconds=0,
                error="Tool path not found",
            )

        # Try to import and run the tool
        tool_file = cap.path / f"{cap.name}.py"
        if not tool_file.exists():
            tool_file = cap.path / "__init__.py"

        if not tool_file.exists():
            return ExecutionResult(
                capability=cap.name,
                success=False,
                output=None,
                duration_seconds=0,
                error=f"Tool file not found: {tool_file}",
            )

        try:
            spec = importlib.util.spec_from_file_location(cap.name, tool_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "main"):
                output = module.main(**kwargs)
                return ExecutionResult(
                    capability=cap.name,
                    success=True,
                    output=output,
                    duration_seconds=0,
                )
            else:
                return ExecutionResult(
                    capability=cap.name,
                    success=False,
                    output=None,
                    duration_seconds=0,
                    error="Tool has no main function",
                )
        except Exception as e:
            return ExecutionResult(
                capability=cap.name,
                success=False,
                output=None,
                duration_seconds=0,
                error=f"Tool execution error: {e}",
            )

    def _execute_composed(self, name: str, **kwargs) -> ExecutionResult:
        """Execute a composed capability."""
        composition = self._compositions.get(name)
        if not composition:
            return ExecutionResult(
                capability=name,
                success=False,
                output=None,
                duration_seconds=0,
                error=f"Composition not found: {name}",
            )

        outputs = {}
        total_iterations = 0

        for step in composition.steps:
            # Get inputs for this step
            step_kwargs = dict(kwargs)
            if step in composition.data_flow:
                # Map previous output to this input
                source = composition.data_flow[step]
                if source in outputs:
                    step_kwargs["input"] = outputs[source]

            # Execute step
            result = self.execute(step, **step_kwargs)

            if not result.success:
                return ExecutionResult(
                    capability=name,
                    success=False,
                    output=outputs,
                    duration_seconds=0,
                    iterations=total_iterations,
                    error=f"Step '{step}' failed: {result.error}",
                )

            outputs[step] = result.output
            total_iterations += result.iterations

        return ExecutionResult(
            capability=name,
            success=True,
            output=outputs,
            duration_seconds=0,
            iterations=total_iterations,
        )

    def _execute_prompt(self, cap: CapabilityMetadata, task: str = "", **kwargs) -> ExecutionResult:
        """Execute a prompt capability via AtomRuntime."""
        if not cap.path:
            return ExecutionResult(
                capability=cap.name,
                success=False,
                output=None,
                duration_seconds=0,
                error="Prompt path not found",
            )

        try:
            from cc_atoms.atom_core import AtomRuntime

            system_prompt = cap.path.read_text()
            max_iterations = kwargs.get("max_iterations", 10)

            runtime = AtomRuntime.create_ephemeral(
                system_prompt=system_prompt,
                max_iterations=max_iterations,
                verbose=kwargs.get("verbose", self.verbose),
            )

            result = runtime.run(task)

            return ExecutionResult(
                capability=cap.name,
                success=result.get("success", False),
                output=result.get("output", ""),
                duration_seconds=result.get("duration", 0),
                iterations=result.get("iterations", 0),
            )
        except Exception as e:
            return ExecutionResult(
                capability=cap.name,
                success=False,
                output=None,
                duration_seconds=0,
                error=f"Prompt execution error: {e}",
            )

    def _record_execution(self, cap: CapabilityMetadata, result: ExecutionResult):
        """Record execution for tracking."""
        cap.usage_count += 1
        cap.total_duration += result.duration_seconds
        cap.last_used = datetime.now()

        if result.success:
            cap.success_count += 1
            cap.last_success = datetime.now()
        else:
            cap.last_failure = datetime.now()

        # Update average iterations
        if result.iterations > 0:
            cap.average_iterations = (
                (cap.average_iterations * (cap.usage_count - 1) + result.iterations)
                / cap.usage_count
            )

        # Log execution
        self._execution_log.append(result)
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-500:]

        self._save_state()

    # =========================================================================
    # ANALYSIS - Understanding Performance
    # =========================================================================

    def analyze(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze capability performance.

        Args:
            window_hours: Analysis window

        Returns:
            Analysis report
        """
        cutoff = datetime.now() - timedelta(hours=window_hours)

        # Filter recent executions
        recent = [r for r in self._execution_log
                 if hasattr(r, 'timestamp') and r.metadata.get('timestamp', datetime.min) > cutoff]

        # Overall stats
        total = len(recent)
        successes = sum(1 for r in recent if r.success)

        # Per-capability stats
        cap_stats = {}
        for cap in self._capabilities.values():
            if cap.usage_count > 0:
                cap_stats[cap.name] = {
                    "uses": cap.usage_count,
                    "success_rate": cap.success_rate,
                    "avg_duration": cap.average_duration,
                    "effectiveness": cap.effectiveness_score,
                }

        # Find bottlenecks
        bottlenecks = [
            name for name, stats in cap_stats.items()
            if stats["success_rate"] < 0.5 and stats["uses"] >= 3
        ]

        # Find top performers
        top_performers = sorted(
            cap_stats.items(),
            key=lambda x: x[1]["effectiveness"],
            reverse=True
        )[:5]

        return {
            "window_hours": window_hours,
            "total_executions": total,
            "success_rate": successes / total if total > 0 else 1.0,
            "capabilities_analyzed": len(cap_stats),
            "bottlenecks": bottlenecks,
            "top_performers": [name for name, _ in top_performers],
            "per_capability": cap_stats,
        }

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def _save_state(self):
        """Save registry state to disk."""
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        # Serialize capabilities
        caps_data = {}
        for name, cap in self._capabilities.items():
            caps_data[name] = {
                "type": cap.type.value,
                "description": cap.description,
                "path": str(cap.path) if cap.path else None,
                "tags": cap.tags,
                "category": cap.category,
                "domain": cap.domain,
                "usage_count": cap.usage_count,
                "success_count": cap.success_count,
                "total_duration": cap.total_duration,
                "last_used": cap.last_used.isoformat() if cap.last_used else None,
                "last_success": cap.last_success.isoformat() if cap.last_success else None,
                "average_iterations": cap.average_iterations,
            }

        # Serialize compositions
        comps_data = {}
        for name, comp in self._compositions.items():
            comps_data[name] = {
                "description": comp.description,
                "steps": comp.steps,
                "data_flow": comp.data_flow,
            }

        state = {
            "capabilities": caps_data,
            "compositions": comps_data,
            "version": 1,
        }

        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load registry state from disk."""
        if not self._state_file.exists():
            return

        try:
            with open(self._state_file, "r") as f:
                state = json.load(f)

            # Load capability stats
            self._saved_cap_stats = state.get("capabilities", {})

            # Load compositions
            for name, comp_data in state.get("compositions", {}).items():
                self._compositions[name] = ComposedCapability(
                    name=name,
                    description=comp_data["description"],
                    steps=comp_data["steps"],
                    data_flow=comp_data.get("data_flow", {}),
                )

        except Exception as e:
            self._log(f"Could not load state: {e}")

    # =========================================================================
    # DISPLAY
    # =========================================================================

    def print_capabilities(self):
        """Print a formatted list of capabilities."""
        caps = self.list()

        print(f"\n{'='*60}")
        print(f"Capability Registry ({len(caps)} capabilities)")
        print(f"{'='*60}\n")

        by_category: Dict[str, List[CapabilityMetadata]] = {}
        for cap in caps:
            if cap.category not in by_category:
                by_category[cap.category] = []
            by_category[cap.category].append(cap)

        for category, cat_caps in sorted(by_category.items()):
            print(f"\n## {category.upper()} ({len(cat_caps)})\n")
            for cap in cat_caps:
                status = "★" if cap.effectiveness_score > 0.8 else "○"
                print(f"{status} {cap.name} [{cap.type.value}]")
                print(f"  {cap.description[:70]}")
                print(f"  Tags: {', '.join(cap.tags) or 'none'}")
                print(f"  Score: {cap.effectiveness_score:.2f} | Uses: {cap.usage_count}")
                print()


# =========================================================================
# CLI
# =========================================================================

def main():
    """CLI entry point for capability registry."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Capability Registry for cc_atoms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cap-registry list                    # List all capabilities
  cap-registry list --tag automation   # Filter by tag
  cap-registry match "analyze code"    # Find matching capabilities
  cap-registry analyze                 # Performance analysis
  cap-registry execute tool_name       # Execute with tracking
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List capabilities")
    list_parser.add_argument("--tag", "-t", help="Filter by tag")
    list_parser.add_argument("--category", "-c", help="Filter by category")
    list_parser.add_argument("--type", help="Filter by type")
    list_parser.add_argument("--refresh", "-r", action="store_true")

    # Match command
    match_parser = subparsers.add_parser("match", help="Find matching capabilities")
    match_parser.add_argument("task", help="Task description")
    match_parser.add_argument("--max", "-n", type=int, default=5)

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Performance analysis")
    analyze_parser.add_argument("--hours", type=int, default=24)

    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Execute a capability")
    exec_parser.add_argument("name", help="Capability name")
    exec_parser.add_argument("--task", help="Task for prompt capabilities")

    parser.add_argument("--quiet", "-q", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    registry = CapabilityRegistry(
        verbose=not args.quiet,
        auto_discover=True
    )

    if args.command == "list":
        if args.refresh:
            registry.discover(refresh=True)

        type_filter = None
        if args.type:
            type_filter = CapabilityType(args.type)

        caps = registry.list(
            tag=args.tag,
            category=args.category,
            type_=type_filter,
        )

        if args.quiet:
            for cap in caps:
                print(f"{cap.name}\t{cap.type.value}\t{cap.effectiveness_score:.2f}")
        else:
            registry.print_capabilities()
        return 0

    elif args.command == "match":
        matches = registry.match(args.task, max_results=args.max)

        if not matches:
            print("No matching capabilities found.")
            return 1

        print(f"\nMatching capabilities for: {args.task}\n")
        for cap, score in matches:
            print(f"  {score:.2f}  {cap.name}: {cap.description[:50]}")
        return 0

    elif args.command == "analyze":
        analysis = registry.analyze(window_hours=args.hours)

        print(f"\n{'='*60}")
        print(f"Capability Performance Analysis ({args.hours}h window)")
        print(f"{'='*60}\n")

        print(f"Total executions: {analysis['total_executions']}")
        print(f"Success rate: {analysis['success_rate']:.0%}")
        print(f"Capabilities analyzed: {analysis['capabilities_analyzed']}")

        if analysis["bottlenecks"]:
            print(f"\nBottlenecks (low success rate):")
            for name in analysis["bottlenecks"]:
                print(f"  - {name}")

        if analysis["top_performers"]:
            print(f"\nTop performers:")
            for name in analysis["top_performers"]:
                print(f"  - {name}")

        return 0

    elif args.command == "execute":
        result = registry.execute(args.name, task=args.task or "")

        print(f"\n{'='*60}")
        print(f"Execution: {args.name}")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        if result.error:
            print(f"Error: {result.error}")
        if result.output:
            print(f"\nOutput:\n{result.output}")
        return 0 if result.success else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
