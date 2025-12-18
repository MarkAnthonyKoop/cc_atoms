# Two-Tier Delegation Guide

## Overview

Each atom has two delegation mechanisms available. Choose based on the work's weight and persistence needs.

## Tier 1: Task Tool (Lightweight)

Native Claude Code feature. Ephemeral, single-shot, parallel-capable.

### When to Use
- Codebase exploration before implementing
- Parallel research across multiple areas
- Quick validation or review within an iteration
- Independent subtasks that don't need their own iteration loop

### Examples

```
# Parallel exploration
Task(Explore) → "find authentication patterns in src/"
Task(Explore) → "find database models"
Task(Explore) → "find existing test patterns"
# All run concurrently, results return to you

# Quick architectural input
Task(Plan) → "design the API structure for user management"

# Independent subtask
Task(general-purpose) → "write unit tests for utils.py"
```

### Characteristics
- Runs within your current iteration
- No directory created
- No iteration loop
- Results return immediately
- Can spawn multiple in parallel

## Tier 2: Sub-Atom (Heavyweight)

cc_atoms recursive spawning. Persistent, multi-iteration, quality-gated.

### When to Use
- Major implementation chunks (auth system, API layer, etc.)
- Work requiring multiple iterations to complete
- Tasks needing quality gates and retry handling
- Substantial refactoring or feature implementation

### Examples

```
# Decomposition creates sub-atoms:
step_1_backend/
  └── AtomRuntime (5 iterations, quality gates, retries)

step_2_frontend/
  └── AtomRuntime (5 iterations, quality gates, retries)
```

### Characteristics
- Own subdirectory with `claude -c` persistence
- Iteration loop (1-N iterations until EXIT_LOOP_NOW)
- Quality gate scanning before completion
- Retry handling for session limits
- Memory injection from home index
- Can spawn its own sub-atoms (recursive)

## Decision Matrix

| Scenario | Tier | Rationale |
|----------|------|-----------|
| "What auth patterns exist?" | Task(Explore) | Quick research |
| "Build the auth system" | Sub-Atom | Major implementation |
| "Check if tests pass" | Task | Single verification |
| "Write comprehensive test suite" | Sub-Atom | Substantial work |
| "Find all TODO comments" | Task(Explore) | Quick search |
| "Refactor error handling" | Sub-Atom | Multi-file changes |
| "Review this implementation" | Task(general-purpose) | Quick review |
| "Implement and verify feature X" | Sub-Atom | Needs iteration loop |

## Hybrid Pattern

Within a single iteration, you might:

1. Use Task(Explore) to research the codebase (parallel)
2. Use Task(Plan) to get architectural guidance
3. Implement based on findings
4. Decide a component needs heavyweight treatment → signal sub-atom

The atom decides. No hard rules—use judgment based on scope and persistence needs.

## Key Difference

**Task tool**: You stay in control, agents return results to you.

**Sub-atom**: Autonomous execution with its own iteration loop until done.
