#!/usr/bin/env python3
"""cc_atoms CLI - Autonomous Claude Code orchestrator with task analysis"""
import argparse
import sys
from pathlib import Path

from cc_atoms.atom_core import AtomRuntime, PromptLoader, DecompositionLevel
from cc_atoms.config import MAX_ITERATIONS, DECOMPOSITION_LEVEL, FORCE_COMPLEX


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Atom: Autonomous Claude Code orchestrator with intelligent task analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  atom "Say hello"                    # Simple task, minimal overhead
  atom "Build a REST API"             # Complex task, auto-decomposition
  atom --force-complex "Test task"    # Force full decomposition for testing
  atom --decomposition aggressive "Big feature"  # Maximum decomposition
  atom --no-analyze "Quick fix"       # Skip analysis, run directly
        """
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompt text to create USER_PROMPT.md"
    )
    parser.add_argument(
        "--toolname",
        type=str,
        default=None,
        help="Tool name to load specialized prompts (e.g., 'atom_my_tool' or 'my_tool')"
    )

    # v3 options
    parser.add_argument(
        "--decomposition", "-d",
        type=str,
        choices=["none", "light", "standard", "aggressive"],
        default=None,
        help="Decomposition level: none, light, standard, aggressive (default: standard)"
    )
    parser.add_argument(
        "--force-complex", "-f",
        action="store_true",
        default=FORCE_COMPLEX,
        help="Force complex mode for testing (treats all tasks as complex)"
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip task analysis, run directly"
    )
    parser.add_argument(
        "--no-meta-agents",
        action="store_true",
        help="Disable meta-agents (critic, verifier)"
    )
    parser.add_argument(
        "--no-quality-check",
        action="store_true",
        help="Disable quality gate checks"
    )
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Maximum iterations (default: {MAX_ITERATIONS})"
    )

    return parser.parse_args()


def handle_command_line_prompt(prompt_args):
    """Create USER_PROMPT.md from command line arguments if provided."""
    if prompt_args:
        prompt_text = " ".join(prompt_args)
        prompt_file = Path("USER_PROMPT.md")
        prompt_file.write_text(prompt_text)
        print(f"Created USER_PROMPT.md with provided prompt\n")


def validate_user_prompt():
    """Ensure USER_PROMPT.md exists in current directory."""
    prompt_file = Path("USER_PROMPT.md")
    if not prompt_file.exists():
        print("USER_PROMPT.md not found in current directory")
        print("Usage: atom [prompt text]")
        print("   or: create USER_PROMPT.md manually and run: atom")
        sys.exit(1)


def setup_atoms_environment():
    """Ensure ~/cc_atoms directory structure exists and bin is in PATH."""
    import os
    from cc_atoms.config import BIN_DIR, TOOLS_DIR, PROMPTS_DIR, META_AGENTS_DIR

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    META_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    if str(BIN_DIR) not in os.environ.get('PATH', ''):
        os.environ['PATH'] = f"{BIN_DIR}:{os.environ['PATH']}"


def get_decomposition_level(args):
    """Get decomposition level from args or config."""
    if args.decomposition:
        level_map = {
            "none": DecompositionLevel.NONE,
            "light": DecompositionLevel.LIGHT,
            "standard": DecompositionLevel.STANDARD,
            "aggressive": DecompositionLevel.AGGRESSIVE,
        }
        return level_map[args.decomposition]
    return DECOMPOSITION_LEVEL


def main():
    # Parse command line arguments
    args = parse_arguments()

    # Setup phase
    handle_command_line_prompt(args.prompt)
    validate_user_prompt()
    setup_atoms_environment()

    print(f"Atom v3: {Path.cwd().name}\n")

    # Load system prompt
    loader = PromptLoader()
    system_prompt = loader.load(args.toolname)

    # Get decomposition level
    decomposition_level = get_decomposition_level(args)

    # Create runtime with v3 options
    runtime = AtomRuntime(
        system_prompt=system_prompt,
        conversation_dir=Path.cwd(),
        max_iterations=args.max_iterations,
        verbose=True,  # CLI always verbose
        # v3 options
        use_task_analyzer=not args.no_analyze,
        decomposition_level=decomposition_level,
        force_complex=args.force_complex,
        use_meta_agents=not args.no_meta_agents,
        quality_check=not args.no_quality_check,
    )

    # Read user prompt
    user_prompt = Path("USER_PROMPT.md").read_text()

    # Run
    result = runtime.run(user_prompt)

    # Report
    print("\n" + "=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)

    if result.get("task_analysis"):
        analysis = result["task_analysis"]
        print(f"Complexity: {analysis.get('complexity', 'unknown')}")
        print(f"Estimated iterations: {analysis.get('estimated_iterations', '?')}")

    print(f"Actual iterations: {result.get('iterations', 0)}")
    print(f"Duration: {result.get('duration', 0):.1f}s")
    print(f"Memory used: {result.get('memory_used', False)}")

    if result.get("meta_agents_run"):
        print(f"Meta-agents run: {', '.join(result['meta_agents_run'])}")

    if result.get("decomposition"):
        decomp = result["decomposition"]
        print(f"Decomposition: {len(decomp.get('completed', []))}/{len(decomp.get('steps', []))} steps")

    print()

    if result["success"]:
        print(f"Complete after {result['iterations']} iterations")
        return 0
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
        elif result.get("reason") == "max_iterations":
            print(f"Max iterations ({args.max_iterations}) reached")
        else:
            print(f"Failed: {result.get('reason', 'unknown')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
