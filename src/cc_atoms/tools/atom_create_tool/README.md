# atom_create_tool - Tool Builder for cc_atoms Ecosystem

## Quick Start

**Interactive mode (manual scaffolding):**
```bash
atom_create_tool
# Follow prompts to create tool structure
```

**AI-assisted mode (automated generation):**
```bash
atom_create_tool "create a tool that reviews Python code for best practices and generates improvement suggestions"
atom_create_tool "build a tool that analyzes git commit history and generates release notes"
atom_create_tool "make a tool that scans for security vulnerabilities in dependencies"
```

## What This Tool Does

`atom_create_tool` is a meta-tool that scaffolds new atom-based tools for the cc_atoms ecosystem. It automates the creation of properly structured tools that follow established patterns and best practices.

The tool provides two modes:
1. **Interactive Mode**: Manual scaffolding with prompts for tool details
2. **AI Mode**: Automated generation where an AI agent creates a complete, working tool

All generated tools are **Python-based** and follow the proven pattern from `atom_session_analyzer`:
- For atom_ tools: Direct argument passing to atom subprocess
- Consistent file structure and naming
- Comprehensive documentation
- Proper error handling

## Examples

### Example 1: Create Tool Interactively

```bash
$ atom_create_tool
=== Atom Tool Creator - Interactive Mode ===

Tool name (e.g., atom_code_reviewer): atom_doc_generator
Brief description: Generates comprehensive documentation from code
Key features/capabilities (one per line, empty line to finish):
  - Analyzes code structure and comments
  - Creates markdown documentation
  - Generates API references
  -

✓ Tool created successfully!

Location: ~/cc_atoms/tools/atom_doc_generator
Files created:
  - ~/cc_atoms/tools/atom_doc_generator/atom_doc_generator (executable)
  - ~/cc_atoms/prompts/ATOM_DOC_GENERATOR.md (system prompt)
  - ~/cc_atoms/tools/atom_doc_generator/README.md (documentation)
  - ~/cc_atoms/bin/atom_doc_generator (launcher)
```

### Example 2: AI-Generated Code Reviewer

```bash
atom_create_tool "create a tool that reviews code for:
- Code quality and best practices
- Security vulnerabilities
- Performance issues
- Documentation completeness
The tool should support multiple languages and provide actionable feedback"
```

The AI will create a complete tool with:
- Working Python script that passes args to atom
- Comprehensive system prompt tailored to code review
- Detailed README with examples
- Proper integration into cc_atoms ecosystem

### Example 3: AI-Generated Test Generator

```bash
atom_create_tool "build a tool that generates comprehensive test suites from existing code, supporting unit tests, integration tests, and edge cases"
```

### Example 4: AI-Generated Refactoring Tool

```bash
atom_create_tool "create a tool that analyzes code for refactoring opportunities and can automatically apply common refactorings like extract method, rename variables, and simplify conditionals"
```

### Example 5: AI-Generated API Designer

```bash
atom_create_tool "make a tool that designs REST APIs from requirements, generates OpenAPI specs, and creates implementation scaffolding"
```

## How It Works

### Interactive Mode (No Arguments)

When run without arguments, `atom_create_tool` provides an interactive prompt-based workflow:

1. **Collect Information**
   - Tool name (validated for format and uniqueness)
   - Brief description
   - Key features/capabilities

2. **Generate Structure**
   - Creates tool directory in `~/cc_atoms/tools/<toolname>/`
   - Generates executable Python script (.py file)
   - Creates symlink for backward compatibility
   - Creates system prompt (TOOLNAME.md) in ~/cc_atoms/prompts/ for atom_* tools
   - Generates README.md with standard sections
   - Creates launcher in `~/cc_atoms/bin/`

3. **Validation**
   - Makes scripts executable (chmod +x)
   - Validates file creation
   - Provides next steps

### AI-Assisted Mode (With Description)

When run with a description, `atom_create_tool` spawns an AI agent to create a complete tool:

1. **Preparation**
   - Constructs detailed prompt with requirements
   - Creates USER_PROMPT.txt with tool specification

2. **AI Generation**
   - Spawns atom with `--toolname atom_create_tool`
   - AI loads ATOM_CREATE_TOOL.md system prompt
   - AI studies reference tools (atom_session_analyzer)
   - AI creates complete, functional tool

3. **Output**
   - Working Python script
   - For atom_ tools: direct argument passing to atom subprocess
   - Tailored system prompt for the tool's domain
   - Comprehensive README with realistic examples
   - Full integration with cc_atoms ecosystem

### Generated Tool Structure

Every generated tool follows this pattern:

```
~/cc_atoms/tools/<toolname>/
├── <toolname>.py                 # Python script (executable)
├── <toolname>                    # Symlink to .py file
├── README.md                     # Documentation
└── USER_PROMPT.md                # Creation prompt (AI mode only)

~/cc_atoms/prompts/<TOOLNAME>.md  # System prompt (for atom_* tools)
~/cc_atoms/bin/<toolname>         # Launcher script
```

### Python Script Pattern

#### For Atom Tools (atom_* prefix)

Generated scripts pass arguments directly to atom:

```python
#!/usr/bin/env python3
import subprocess
import sys

def main():
    args = sys.argv[1:]

    # Check if --toolname is already in args
    has_toolname = any(arg == "--toolname" for arg in args)

    # Build atom command
    atom_cmd = ["atom"]
    if not has_toolname:
        atom_cmd.extend(["--toolname", "<toolname>"])
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
```

#### For Non-Atom Tools

Tools without `atom_` prefix implement custom logic instead of calling atom.

### System Prompt Pattern

System prompts (TOOLNAME.md) include:

1. **Mode Declaration**: Clear statement of purpose
2. **Overview**: What the tool does
3. **Available Resources**: Files, commands, tools accessible
4. **Your Task**: Step-by-step workflow for the AI
5. **Common Tasks**: Typical use cases and examples
6. **Output Guidelines**: Where to create files, naming conventions
7. **Signal Completion**: How to indicate task completion

## Tool Naming Conventions

### Tool Names
- Use lowercase with underscores: `atom_code_reviewer`
- Use `atom_` prefix for tools using --toolname mode
- Be descriptive but concise
- Pattern: `atom_<domain>_<action>`

### System Prompt Names
- Convert tool name to ALL CAPS
- Example: `atom_code_reviewer` → `ATOM_CODE_REVIEWER.md`
- Location: `~/cc_atoms/prompts/` for atom_* tools

### Validation Rules
- Only lowercase letters, numbers, underscores allowed
- Must not conflict with existing tools
- Must be non-empty

## Best Practices

### From Reference Tools

1. **Simple Atom Wrapper** (for atom_ tools)
   - Pass args directly to atom subprocess
   - Insert `--toolname` if not already present
   - No temporary files needed
   - Clean and simple implementation

2. **Clean File Handling**
   - Use consistent filenames
   - For sub-atoms, use `../filename.md` pattern
   - Avoid unnecessary temporary files

3. **Error Handling**
   - Handle FileNotFoundError for missing atom command
   - Handle KeyboardInterrupt gracefully
   - Provide clear error messages to stderr
   - Use try/except blocks appropriately

4. **Return Code Management**
   - Always capture and pass through atom's exit code
   - Use `sys.exit(result.returncode)`
   - Preserve stdout/stderr

5. **Documentation Quality**
   - Start with Quick Start
   - Provide realistic examples
   - Explain architecture clearly

## Installation

This tool is part of the cc_atoms ecosystem and is ready to use:

```bash
# Tool location
~/cc_atoms/tools/atom_create_tool/

# Available via launcher
~/cc_atoms/bin/atom_create_tool

# System prompt
~/cc_atoms/prompts/ATOM_CREATE_TOOL.md
```

No additional installation required!

## Example Tools to Create

The tool can generate various types of tools:

### Analysis Tools
```bash
atom_create_tool "tool that analyzes session logs and extracts key decisions"
atom_create_tool "tool that reviews code for security vulnerabilities"
atom_create_tool "tool that analyzes dependencies and suggests updates"
```

### Generation Tools
```bash
atom_create_tool "tool that generates test suites from code"
atom_create_tool "tool that creates documentation from code and comments"
atom_create_tool "tool that generates API clients from OpenAPI specs"
```

### Transformation Tools
```bash
atom_create_tool "tool that refactors code following best practices"
atom_create_tool "tool that migrates code between frameworks"
atom_create_tool "tool that converts between data formats"
```

### Integration Tools
```bash
atom_create_tool "tool that deploys applications to cloud platforms"
atom_create_tool "tool that interacts with REST APIs"
atom_create_tool "tool that manages database migrations"
```

## Architecture

### Components

1. **atom_create_tool** - Main executable
   - Handles argument parsing
   - Implements interactive mode
   - Orchestrates AI mode
   - Validates inputs
   - Creates file structures

2. **ATOM_CREATE_TOOL.md** - System prompt
   - Guides AI in tool creation
   - Provides templates and patterns
   - References example tools
   - Ensures quality and consistency

3. **README.md** - Documentation (this file)
   - Usage instructions
   - Examples
   - Best practices
   - Architecture explanation

4. **Launcher** - Global access
   - Links tool to PATH
   - Enables use from anywhere

### Design Decisions

**Pattern-Based Generation**: Using atom_session_analyzer as the reference template ensures consistency and proven patterns across all generated tools.

**Dual Mode Support**: Interactive mode for simple tools, AI mode for complex tools provides flexibility for different use cases.

**Validation First**: Checking tool names and preventing conflicts before creation avoids errors and confusion.

**Clear Separation**: Keeping system prompts in ~/cc_atoms/prompts/ for atom_* tools maintains a clean, discoverable structure.

## Testing

The tool includes comprehensive tests:

```bash
# Test interactive mode
~/cc_atoms/tools/atom_create_tool/tests/test_interactive.sh

# Test AI mode (requires atom command)
atom_create_tool "create a simple test tool"
```

Tests verify:
- Tool directory creation
- Script executability
- System prompt generation
- README creation
- Launcher setup
- Basic mode functionality

## Success Criteria

A successfully created tool should:

- [ ] Have a valid, unique name
- [ ] Python script is executable (chmod +x)
- [ ] Symlink exists (<toolname> → <toolname>.py)
- [ ] For atom_ tools: passes args directly to atom
- [ ] Have comprehensive system prompt in ~/cc_atoms/prompts/
- [ ] Include detailed README
- [ ] Be accessible via launcher in ~/cc_atoms/bin/
- [ ] Follow naming conventions
- [ ] Include proper error handling
- [ ] Have clear documentation

## Troubleshooting

**Tool name validation fails:**
- Use only lowercase letters, numbers, underscores
- Ensure tool doesn't already exist
- Use `atom_` prefix for tools with --toolname mode

**Generated tool doesn't work:**
- Verify Python script is executable: `chmod +x ~/cc_atoms/tools/<toolname>/<toolname>.py`
- Check symlink exists: `ls -l ~/cc_atoms/tools/<toolname>/<toolname>`
- Check launcher exists: `ls ~/cc_atoms/bin/<toolname>`
- For atom_ tools, test with: `<toolname> --help` (should show atom help)

**AI mode fails:**
- Ensure `atom` command is available
- Check ATOM_CREATE_TOOL.md exists in ~/cc_atoms/prompts/
- Verify USER_PROMPT.txt is created and valid

## Status

**COMPLETE** - Tool is fully functional and tested

**Migration to Python** (2025-10-13): Converted from bash to Python implementation. All tools now follow the Python-based pattern where atom_ tools pass arguments directly to the atom subprocess.

## Files Created

```
~/cc_atoms/tools/atom_create_tool/
├── atom_create_tool.py           # Main Python executable
├── atom_create_tool              # Symlink to .py file
├── atom_create_tool.bash.old     # Original bash version (backup)
├── README.md                     # This file
├── USER_PROMPT.md                # Original task specification
└── tests/
    ├── test_interactive.sh       # Old bash test
    └── test_python_interactive.sh # Python version test

~/cc_atoms/prompts/
└── ATOM_CREATE_TOOL.md           # AI mode system prompt (updated for Python)

~/cc_atoms/bin/
└── atom_create_tool              # Global launcher (updated for Python)
```

## Next Steps

1. Create tools for common tasks:
   - `atom_code_reviewer` - Code quality analysis
   - `atom_test_generator` - Test suite generation
   - `atom_doc_writer` - Documentation generation
   - `atom_security_scanner` - Security analysis
   - `atom_refactorer` - Code refactoring

2. Enhance existing tools with AI modes

3. Build specialized domain tools as needed

---

**Created**: 2025-10-13
**Status**: COMPLETE - Ready for production use
