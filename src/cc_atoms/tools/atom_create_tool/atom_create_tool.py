#!/usr/bin/env python3
"""
atom_create_tool - Generate new atom-based tools

Usage:
    atom_create_tool                                      # Interactive mode
    atom_create_tool "description of tool to create"      # AI-assisted mode
"""

import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import date

from cc_atoms.config import TOOLS_DIR, BIN_DIR, PROMPTS_DIR


def validate_tool_name(name):
    """Validate tool name format and uniqueness."""
    if not name:
        print("Error: Tool name cannot be empty", file=sys.stderr)
        return False

    if not re.match(r'^[a-z0-9_]+$', name):
        print("Error: Tool name must contain only lowercase letters, numbers, and underscores", file=sys.stderr)
        return False

    tool_dir = TOOLS_DIR / name
    if tool_dir.exists():
        print(f"Error: Tool '{name}' already exists at {tool_dir}", file=sys.stderr)
        return False

    return True


def to_uppercase(name):
    """Convert tool name to uppercase for system prompt."""
    return name.upper()


def generate_python_tool_script(tool_name, description, is_atom_tool):
    """Generate Python tool script based on whether it's an atom tool."""

    if is_atom_tool:
        # Atom tools pass args directly to atom subprocess
        return f'''#!/usr/bin/env python3
"""
{tool_name} - {description}

Usage:
    {tool_name} [args...]    # Pass arguments to atom with {tool_name} context
"""

import subprocess
import sys


def main():
    # Build atom command with toolname
    args = sys.argv[1:]

    # Check if --toolname is already in args
    has_toolname = any(arg == "--toolname" for arg in args)

    # Build atom command
    atom_cmd = ["atom"]
    if not has_toolname:
        atom_cmd.extend(["--toolname", "{tool_name}"])
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
'''
    else:
        # Non-atom tools have custom logic
        return f'''#!/usr/bin/env python3
"""
{tool_name} - {description}

Usage:
    {tool_name}                    # Basic mode
    {tool_name} [args...]          # With arguments
"""

import sys


def main():
    if len(sys.argv) == 1:
        # Basic mode - implement core functionality
        print("Running {tool_name} in basic mode...")
        # TODO: Add your implementation here
        sys.exit(0)

    # Handle arguments
    args = sys.argv[1:]
    # TODO: Implement argument handling
    print(f"Arguments: {{args}}")


if __name__ == "__main__":
    main()
'''


def generate_system_prompt(tool_name, description, features):
    """Generate system prompt markdown."""
    prompt_name = to_uppercase(tool_name)

    prompt = f'''# {prompt_name} Tool Mode

You are running in **{tool_name}** mode. Your task is to {description}.

## Overview

{description}

## Key Capabilities

'''

    for feature in features:
        prompt += f"- {feature}\n"

    prompt += '''
## Available Resources

- Full file system access
- All standard Claude Code tools
- Ability to create files, run commands, and install packages

## Your Task

The user has provided a prompt requesting specific functionality. Your job is to:

1. **Understand the request**: Parse the user's prompt in `USER_PROMPT.md`
2. **Implement the solution**: Use available tools to fulfill the request
3. **Generate output**: Create files, reports, or results as requested
4. **Validate**: Test your work to ensure it meets requirements

## Output Guidelines

- Create files in the current directory (the atom subdir)
- Use clear, descriptive filenames
- Include documentation for complex outputs
- Follow best practices for code quality and maintainability

## Signal Completion

When your task is complete:
1. Generate all requested outputs
2. Verify everything works as expected
3. Print a summary of what was created
4. Output `EXIT_LOOP_NOW` to signal completion

Begin your work!
'''
    return prompt


def generate_readme(tool_name, description, features):
    """Generate README markdown."""

    readme = f'''# {tool_name} - {description}

## Quick Start

**Basic usage:**
```bash
{tool_name}
```

**With arguments:**
```bash
{tool_name} "your request here"
```

## What This Tool Does

{description}

## Key Features

'''

    for feature in features:
        readme += f"- {feature}\n"

    readme += f'''
## Examples

### Example 1: Basic Usage
```bash
# TODO: Add specific example
```

### Example 2: With Arguments
```bash
# TODO: Add specific example with arguments
```

## How It Works

This tool is implemented in Python and provides a simple interface for {description.lower()}.

## Installation

This tool is part of the cc_atoms ecosystem.

```bash
# The tool is located at:
# ~/cc_atoms/tools/{tool_name}/

# Available via the launcher:
# ~/cc_atoms/bin/{tool_name}
```

---

**Created**: {date.today().isoformat()}
**Status**: Ready for implementation
'''
    return readme


def interactive_mode():
    """Interactive mode for manual tool scaffolding."""
    print("=== Atom Tool Creator - Interactive Mode ===")
    print()

    # Get tool name
    while True:
        tool_name = input("Tool name (e.g., atom_code_reviewer): ").strip()
        if validate_tool_name(tool_name):
            break

    # Get description
    description = input("Brief description: ").strip()

    # Get key features
    print("Key features/capabilities (one per line, empty line to finish):")
    features = []
    while True:
        feature = input("  - ").strip()
        if not feature:
            break
        features.append(feature)

    # Create tool directory
    tool_dir = TOOLS_DIR / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("Creating tool structure...")

    # Determine if it's an atom tool
    is_atom_tool = tool_name.startswith("atom_")

    # Generate the Python script
    script_file = tool_dir / f"{tool_name}.py"
    script_content = generate_python_tool_script(tool_name, description, is_atom_tool)
    script_file.write_text(script_content)
    script_file.chmod(0o755)

    # Create symlink for backward compatibility
    symlink = tool_dir / tool_name
    if not symlink.exists():
        symlink.symlink_to(f"{tool_name}.py")

    # Generate the system prompt
    prompt_name = to_uppercase(tool_name)

    # Determine where to put the system prompt
    if is_atom_tool:
        # Tools with atom_ prefix get prompts in ~/cc_atoms/prompts/
        prompt_file = PROMPTS_DIR / f"{prompt_name}.md"
    else:
        # Other tools get prompts in their tool directory
        prompt_file = tool_dir / f"{prompt_name}.md"

    prompt_content = generate_system_prompt(tool_name, description, features)
    prompt_file.write_text(prompt_content)

    # Generate README
    readme_file = tool_dir / "README.md"
    readme_content = generate_readme(tool_name, description, features)
    readme_file.write_text(readme_content)

    # Create launcher in bin
    launcher_file = BIN_DIR / tool_name
    launcher_content = f'''#!/bin/bash
exec python3 {script_file} "$@"
'''
    launcher_file.write_text(launcher_content)
    launcher_file.chmod(0o755)

    # Success message
    print()
    print("✓ Tool created successfully!")
    print()
    print(f"Location: {tool_dir}")
    print("Files created:")
    print(f"  - {script_file} (executable)")
    print(f"  - {prompt_file} (system prompt)")
    print(f"  - {readme_file} (documentation)")
    print(f"  - {launcher_file} (launcher)")
    print()
    print("Next steps:")
    print(f"  1. Edit {script_file} to implement functionality")
    print(f"  2. Customize {prompt_file} for your tool's specific needs")
    print(f"  3. Update {readme_file} with specific examples")
    print(f"  4. Test with: {tool_name}")
    print()


def ai_mode(request):
    """AI-assisted mode - spawn atom to create complete tool."""
    print("Creating tool with AI assistance...")
    print(f"Request: {request}")
    print()

    # Create USER_PROMPT.txt with the request
    prompt_content = f'''Create a complete, functional Python-based tool for the cc_atoms ecosystem based on this request:

{request}

The tool should follow these requirements:
1. Be implemented in Python (not bash)
2. For atom_ prefixed tools: pass arguments directly to atom subprocess, inserting --toolname if not present
3. Include a comprehensive system prompt for --toolname mode in ~/cc_atoms/prompts/
4. Include complete README.md with examples
5. Create launcher in ~/cc_atoms/bin/

Study the atom_session_analyzer Python implementation as a reference for atom_ tools.

Make the tool immediately usable and well-documented.
'''

    # Write to USER_PROMPT.txt
    Path("USER_PROMPT.txt").write_text(prompt_content)

    # Spawn atom with atom_create_tool system prompt
    try:
        result = subprocess.run(["atom", "--toolname", "atom_create_tool"], input=prompt_content, text=True)
        exit_code = result.returncode
    except FileNotFoundError:
        print("Error: atom command not found", file=sys.stderr)
        exit_code = 1
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        # Clean up
        if Path("USER_PROMPT.txt").exists():
            Path("USER_PROMPT.txt").unlink()

    sys.exit(exit_code)


def main():
    """Main entry point."""
    # Ensure required directories exist
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) == 1:
        # No arguments - interactive mode
        interactive_mode()
    else:
        # Arguments provided - AI mode
        request = " ".join(sys.argv[1:])
        ai_mode(request)


if __name__ == "__main__":
    main()
