#!/usr/bin/env python3
"""
Meta-Agent: Self-evolving autonomous system that builds higher abstractions

This agent:
1. Analyzes its own codebase and capabilities
2. Identifies patterns and gaps
3. Designs and implements the next abstraction layer
4. Bootstraps itself to higher levels of capability

The key insight: The agent doesn't know what it can do until it discovers it.
It must use the tools available to understand itself, then extend itself.

Usage:
    meta-agent evolve    # Analyze and build next abstraction
    meta-agent reflect   # Deep self-analysis without action
    meta-agent extend "capability description"  # Add specific capability
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class EvolutionResult:
    """Result of an evolution cycle"""
    generation: int
    insights: List[str]
    capabilities_discovered: List[str]
    abstractions_created: List[str]
    code_written: Dict[str, str]  # filename -> content
    next_steps: List[str]
    duration_seconds: float


META_SYSTEM_PROMPT = """# Meta-Agent: Self-Evolving System

You are a meta-agent - an autonomous system capable of understanding and extending itself.

## Your Prime Directive

Discover what you can do, then build higher abstractions on top of it.

## Phase 1: Discovery

You start knowing NOTHING about your environment. You must:

1. Explore the current working directory
2. Find and read any documentation (README.md, HANDOFF.md, etc.)
3. Discover what tools and capabilities exist
4. Understand the architecture you're running inside

DO NOT ASSUME. DISCOVER.

## Phase 2: Analysis

Once you understand the system:

1. Identify patterns across the codebase
2. Find repetitive tasks that could be abstracted
3. Discover gaps - what's missing that would be useful?
4. Map the dependency graph of capabilities

## Phase 3: Evolution

Design and implement the NEXT LEVEL of abstraction:

1. What meta-capability would make all other tasks easier?
2. What's the "atom" of the next layer up?
3. How can the system become more self-aware?
4. What would let the system teach itself new skills?

## Constraints

- You CAN create new Python files
- You CAN modify existing code (carefully)
- You MUST document what you create
- You MUST explain your reasoning
- You SHOULD leverage existing tools, not replace them

## Output

When complete, provide:

1. **Discovery Report**: What you found
2. **Analysis**: Patterns, gaps, opportunities
3. **Evolution**: What you built and why
4. **Next Generation**: What the NEXT meta-agent should do

Signal completion with: EXIT_LOOP_NOW
"""


class MetaAgent:
    """
    Self-evolving meta-agent that builds higher abstractions.

    The agent discovers its own capabilities through exploration,
    then designs and implements the next level of abstraction.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.generation = self._load_generation()
        self.evolution_log = Path.home() / '.cache' / 'meta_agent' / 'evolution_log.json'

    def _log(self, msg: str):
        if self.verbose:
            print(f"[MetaAgent Gen-{self.generation}] {msg}")

    def _load_generation(self) -> int:
        """Load current generation number"""
        state_file = Path.home() / '.cache' / 'meta_agent' / 'state.json'
        if state_file.exists():
            try:
                with open(state_file) as f:
                    return json.load(f).get('generation', 0)
            except:
                pass
        return 0

    def _save_generation(self, gen: int):
        """Save generation number"""
        state_file = Path.home() / '.cache' / 'meta_agent' / 'state.json'
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump({'generation': gen, 'timestamp': datetime.now().isoformat()}, f)

    def _log_evolution(self, result: EvolutionResult):
        """Log evolution to history"""
        self.evolution_log.parent.mkdir(parents=True, exist_ok=True)

        history = []
        if self.evolution_log.exists():
            try:
                with open(self.evolution_log) as f:
                    history = json.load(f)
            except:
                pass

        history.append({
            'generation': result.generation,
            'timestamp': datetime.now().isoformat(),
            'insights': result.insights,
            'capabilities_discovered': result.capabilities_discovered,
            'abstractions_created': result.abstractions_created,
            'files_created': list(result.code_written.keys()),
            'next_steps': result.next_steps,
            'duration': result.duration_seconds,
        })

        with open(self.evolution_log, 'w') as f:
            json.dump(history, f, indent=2)

    def reflect(self) -> str:
        """
        Deep self-analysis without taking action.
        Returns insights about the system.
        """
        self._log("Starting reflection cycle...")

        from cc_atoms.atom_core import AtomRuntime

        reflection_prompt = """## Reflection Task

Perform deep self-analysis of this system. You are running inside it.

1. **Explore**: Read files, understand the architecture
2. **Map**: What are all the capabilities?
3. **Analyze**: What patterns exist? What's elegant? What's messy?
4. **Theorize**: What's the next logical evolution?

DO NOT write any code. Only analyze and report.

Provide a comprehensive reflection report, then EXIT_LOOP_NOW.
"""

        runtime = AtomRuntime.create_ephemeral(
            system_prompt=META_SYSTEM_PROMPT,
            max_iterations=10,
            verbose=self.verbose,
            use_memory=False  # Must discover on its own
        )

        result = runtime.run(reflection_prompt)
        return result.get('output', '')

    def evolve(self, guidance: Optional[str] = None) -> EvolutionResult:
        """
        Run an evolution cycle.

        The agent will:
        1. Discover its environment
        2. Analyze patterns and gaps
        3. Design next abstraction
        4. Implement it

        Args:
            guidance: Optional hint about what direction to evolve

        Returns:
            EvolutionResult with what was discovered/created
        """
        start_time = time.time()
        self._log(f"Starting evolution cycle (Generation {self.generation} -> {self.generation + 1})")

        from cc_atoms.atom_core import AtomRuntime

        # Build evolution prompt
        if guidance:
            evolution_task = f"""## Evolution Task (Generation {self.generation} -> {self.generation + 1})

Guidance from previous generation: {guidance}

Your mission: Discover your capabilities, then build the NEXT LEVEL of abstraction.

You are in: {os.getcwd()}

### Requirements

1. **DISCOVER** - Explore files, read docs, understand what exists
2. **ANALYZE** - Find patterns, identify what's missing
3. **DESIGN** - What abstraction would make everything more powerful?
4. **IMPLEMENT** - Write the code, create the new capability
5. **DOCUMENT** - Explain what you built and why

### Key Questions

- What repetitive patterns could be abstracted?
- What would let this system do things it currently can't?
- How can the system become more self-aware?
- What's the "atom" of the next layer up?

Create real, working code. This is not a thought experiment.

When done, output EXIT_LOOP_NOW.
"""
        else:
            evolution_task = f"""## Evolution Task (Generation {self.generation} -> {self.generation + 1})

Your mission: Discover your capabilities, then build the NEXT LEVEL of abstraction.

You are in: {os.getcwd()}

Start by exploring. You know NOTHING about this system yet.

### Phase 1: Discovery
- What files exist here?
- What is this project?
- What tools are available?
- How does it work?

### Phase 2: Analysis
- What patterns do you see?
- What's missing?
- What would make this more powerful?

### Phase 3: Evolution
- Design a new abstraction layer
- Implement it (real code!)
- Document it

### Constraints
- Create files in the current directory or src/cc_atoms/tools/
- Must be real, working Python code
- Must integrate with existing architecture
- Must be more abstract than what exists

When done, output EXIT_LOOP_NOW.
"""

        runtime = AtomRuntime.create_ephemeral(
            system_prompt=META_SYSTEM_PROMPT,
            max_iterations=15,
            verbose=self.verbose,
            use_memory=False  # Must discover capabilities itself
        )

        result = runtime.run(evolution_task)
        duration = time.time() - start_time

        # Parse results (the agent should have created files and documented)
        output = result.get('output', '')

        # Increment generation
        self.generation += 1
        self._save_generation(self.generation)

        evolution_result = EvolutionResult(
            generation=self.generation,
            insights=self._extract_insights(output),
            capabilities_discovered=self._extract_capabilities(output),
            abstractions_created=self._extract_abstractions(output),
            code_written={},  # Would need file tracking
            next_steps=self._extract_next_steps(output),
            duration_seconds=duration
        )

        self._log_evolution(evolution_result)

        return evolution_result

    def _extract_insights(self, output: str) -> List[str]:
        """Extract insights from output"""
        insights = []
        for line in output.split('\n'):
            if 'insight' in line.lower() or 'discovered' in line.lower():
                insights.append(line.strip())
        return insights[:10]

    def _extract_capabilities(self, output: str) -> List[str]:
        """Extract discovered capabilities"""
        caps = []
        keywords = ['can ', 'able to', 'capability', 'tool:', 'command:']
        for line in output.split('\n'):
            if any(kw in line.lower() for kw in keywords):
                caps.append(line.strip())
        return caps[:20]

    def _extract_abstractions(self, output: str) -> List[str]:
        """Extract created abstractions"""
        abstractions = []
        keywords = ['created', 'implemented', 'built', 'new class', 'new function']
        for line in output.split('\n'):
            if any(kw in line.lower() for kw in keywords):
                abstractions.append(line.strip())
        return abstractions[:10]

    def _extract_next_steps(self, output: str) -> List[str]:
        """Extract next steps"""
        steps = []
        keywords = ['next', 'should', 'could', 'todo', 'future']
        for line in output.split('\n'):
            if any(kw in line.lower() for kw in keywords):
                steps.append(line.strip())
        return steps[:10]

    def extend(self, capability: str) -> EvolutionResult:
        """
        Extend the system with a specific capability.

        Args:
            capability: Description of capability to add

        Returns:
            EvolutionResult
        """
        self._log(f"Extending with capability: {capability}")
        return self.evolve(guidance=f"Add this specific capability: {capability}")

    def get_history(self) -> List[Dict]:
        """Get evolution history"""
        if self.evolution_log.exists():
            with open(self.evolution_log) as f:
                return json.load(f)
        return []


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Meta-Agent: Self-evolving autonomous system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  meta-agent evolve              # Run evolution cycle
  meta-agent reflect             # Self-analysis without action
  meta-agent extend "web scraping capability"
  meta-agent history             # Show evolution history
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Evolve command
    evolve_parser = subparsers.add_parser('evolve', help='Run evolution cycle')
    evolve_parser.add_argument('--guidance', '-g', help='Optional guidance')
    evolve_parser.add_argument('--generations', '-n', type=int, default=1, help='Number of generations')

    # Reflect command
    reflect_parser = subparsers.add_parser('reflect', help='Self-analysis without action')

    # Extend command
    extend_parser = subparsers.add_parser('extend', help='Add specific capability')
    extend_parser.add_argument('capability', help='Capability to add')

    # History command
    history_parser = subparsers.add_parser('history', help='Show evolution history')

    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    agent = MetaAgent(verbose=not args.quiet if hasattr(args, 'quiet') else True)

    if args.command == 'evolve':
        for i in range(args.generations):
            print(f"\n{'='*60}")
            print(f"EVOLUTION CYCLE {i+1}/{args.generations}")
            print(f"{'='*60}\n")

            result = agent.evolve(guidance=args.guidance)

            print(f"\n{'='*60}")
            print(f"GENERATION {result.generation} COMPLETE")
            print(f"{'='*60}")
            print(f"Duration: {result.duration_seconds:.1f}s")
            print(f"Capabilities discovered: {len(result.capabilities_discovered)}")
            print(f"Abstractions created: {len(result.abstractions_created)}")

            if result.next_steps:
                print(f"\nNext steps suggested:")
                for step in result.next_steps[:5]:
                    print(f"  - {step}")
        return 0

    elif args.command == 'reflect':
        output = agent.reflect()
        print(output)
        return 0

    elif args.command == 'extend':
        result = agent.extend(args.capability)
        print(f"\nExtension complete (Generation {result.generation})")
        print(f"Duration: {result.duration_seconds:.1f}s")
        return 0

    elif args.command == 'history':
        history = agent.get_history()
        if not history:
            print("No evolution history yet.")
            return 0

        print(f"\nEvolution History ({len(history)} generations)\n")
        for entry in history:
            print(f"Generation {entry['generation']} ({entry['timestamp']})")
            print(f"  Duration: {entry['duration']:.1f}s")
            print(f"  Capabilities: {len(entry['capabilities_discovered'])}")
            print(f"  Abstractions: {len(entry['abstractions_created'])}")
            print(f"  Files: {', '.join(entry['files_created']) or 'none'}")
            print()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
