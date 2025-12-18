#!/usr/bin/env python3
"""
atom_session_analyzer - Extract and analyze Claude Code sessions

Usage:
    atom_session_analyzer                    # Extract current session log
    atom_session_analyzer [args...]          # Pass args to atom with session context
"""

import subprocess
import sys
import os
from pathlib import Path

def extract_session():
    """Extract the most recent Claude Code session to current directory."""
    session_log_file = "session_log.md"

    # Use claude-extract to get the most recent session in detailed mode
    try:
        subprocess.run(
            ["claude-extract", "--extract", "1", "--output", ".", "--format", "markdown", "--detailed"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error: Failed to extract session log", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("Error: claude-extract command not found. Install with: pipx install claude-conversation-extractor", file=sys.stderr)
        return None

    # Find the generated file (it will have a date-stamped name)
    generated_files = sorted(Path(".").glob("claude-conversation-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not generated_files:
        print("Error: Failed to extract session log", file=sys.stderr)
        return None

    generated_file = generated_files[0]

    # Rename to session_log.md for consistent access
    generated_file.rename(session_log_file)

    return Path.cwd() / session_log_file


def main():
    # Extract the session
    session_path = extract_session()

    if session_path is None:
        sys.exit(1)

    # If no arguments, just print the path and exit
    if len(sys.argv) == 1:
        print(session_path)
        sys.exit(0)

    # If arguments provided, call atom with the session analyzer toolname
    args = sys.argv[1:]

    # Check if --toolname is already in args
    has_toolname = any(arg == "--toolname" for arg in args)

    # Build atom command
    atom_cmd = ["atom"]
    if not has_toolname:
        atom_cmd.extend(["--toolname", "atom_session_analyzer"])
    atom_cmd.extend(args)

    # Call atom and pass through the return code
    try:
        result = subprocess.run(atom_cmd)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("Error: atom command not found", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
