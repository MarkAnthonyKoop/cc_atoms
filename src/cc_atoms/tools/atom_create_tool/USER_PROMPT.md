# Create atom_create_tool - A Tool Builder Tool

## Objective

Create a tool called `atom_create_tool` that helps users quickly scaffold and build new atom-based tools for the cc_atoms ecosystem.

## Background

We've successfully created `atom_session_analyzer`, which:
1. Extracts session logs using `claude-conversation-extractor`
2. Optionally spawns an atom with `--toolname` to analyze the session
3. Has a bash script launcher, system prompt (ATOM_CREATE_TOOL.md), and comprehensive README

The pattern is powerful and should be reusable for creating new tools.

## Requirements

Create `atom_create_tool` that follows this pattern:

### Without Arguments (Interactive Mode)
When run without arguments, it should:
1. Interactively prompt the user for:
   - Tool name (e.g., "atom_code_reviewer")
   - Brief description
   - Key features/capabilities
2. Generate a complete tool structure:
   - Tool directory in `~/cc_atoms/tools/<toolname>/`
   - Executable bash script
   - System prompt (`<TOOLNAME>.md` in all caps)
   - Comprehensive README.md with examples
   - Launcher in `~/cc_atoms/bin/`

### With Arguments (AI-Assisted Mode)
When run with a description as an argument:
```bash
atom_create_tool "create a tool that reviews Python code for best practices and generates improvement suggestions"
```

It should:
1. Spawn an atom with `--toolname atom_create_tool`
2. The atom analyzes the request and creates a complete, working tool
3. The atom has access to:
   - This codebase (atom_session_analyzer as reference)
   - The session_logger tool structure as a template
   - Full file system access to create the new tool

## Tool Structure Template

Each generated tool should have:

```
~/cc_atoms/tools/<toolname>/
├── <toolname>                    # Executable bash script
├── <TOOLNAME>.md                 # System prompt for --toolname mode
├── README.md                     # Documentation with examples
└── USER_PROMPT.md                # Original creation prompt (optional)

~/cc_atoms/bin/<toolname>         # Launcher script
```

## Key Features

### 1. Template-Based Generation
The tool should use atom_session_analyzer as a reference template:
- Bash script structure with argument handling
- System prompt format and style
- README structure with Quick Start, Examples, How It Works
- Proper error handling and exit codes

### 2. Smart Naming
- Enforce `atom_` prefix for toolnames that use --toolname
- Generate proper all-caps names for system prompts
- Create descriptive yet concise tool names

### 3. Documentation Quality
Generate README.md sections:
- Quick Start with 2-3 examples
- What This Tool Does (clear explanation)
- Detailed examples (5-6 use cases)
- How It Works (architecture explanation)
- Installation (if needed)

### 4. Validation
- Check if tool name already exists
- Validate tool name format (lowercase, underscores, atom_ prefix)
- Test that generated scripts are executable

### 5. Best Practices
Apply lessons learned:
- Clear separation of concerns (extract, analyze)
- Pass through return codes and stdout
- Use `set -e` for error handling
- Consistent file naming (`session_log.md` pattern)
- Parent directory access (`../file.md` pattern for atom subdirs)

## Implementation Notes

### Bash Script Pattern
```bash
#!/bin/bash
set -e

# 1. Do initial work (extract, download, process)
# 2. If no arguments, output result and exit
# 3. If arguments, spawn atom with --toolname
# 4. Pass through return code and output
```

### System Prompt Pattern
The generated `TOOLNAME.md` should:
- Explain the tool's mode/purpose
- List available resources (files, commands, tools)
- Describe common tasks
- Provide example workflows
- Include output guidelines
- Signal completion with EXIT_LOOP_NOW

### README Pattern
Start with Quick Start showing:
- Simplest usage (no arguments)
- 2-3 AI-assisted examples
Then explain what it does, detailed examples, architecture

## Example Tools to Support

The tool should be capable of generating:

1. **atom_code_reviewer** - Reviews code, suggests improvements
2. **atom_test_generator** - Creates test suites from code
3. **atom_doc_writer** - Generates documentation from code/sessions
4. **atom_refactorer** - Suggests and applies refactorings
5. **atom_security_scanner** - Scans code for security issues
6. **atom_dependency_analyzer** - Analyzes and updates dependencies
7. **atom_api_designer** - Designs APIs from requirements

## Deliverables

1. **atom_create_tool** executable python script
   - Interactive mode for manual tool creation
   - AI mode for automated tool generation

2. **ATOM_CREATE_TOOL.md** system prompt in ~/cc_atoms/prompts
   - Guides atom in understanding tool creation requests
   - Provides templates and patterns
   - Ensures consistent quality

3. **README.md**
   - Clear quick start
   - Examples of creating various types of tools
   - Architecture explanation

4. **Launcher** in ~/cc_atoms/bin/

## Testing

Create at least one example tool using atom_create_tool to validate:
- The generation process works
- Generated tools are functional
- Documentation is clear and complete

## Success Criteria

- Can create a functional tool in under 2 minutes (AI mode)
- Generated tools follow consistent patterns
- All generated scripts are executable and error-free
- Documentation enables users to quickly understand and use new tools
- The tool itself is well-documented and easy to use


Some modifications to this user prompt have been made to fix some issues:

1.  new tools should be python based not bash.
2.  if the tools are "atom" tools, the interface should be the same as the atom interface (basically just pass the args directly to the subprocess that calls atom, but be sure to insert the --toolname <toolname> into the args if it is not already there.
3.  fix both this tool (atom_create_tool) as well as atom_session_analyzer to reflext these requirements
4.  check all files in ~/cc_atoms (/prompts, /bin, /tools) and make sure everything is consistent

