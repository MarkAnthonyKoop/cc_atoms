# Task: Add Missing Tools to CC CLI

The CC CLI has a working agentic loop (verified!). Now add the missing tools that Claude Code has.

## Current Tools (6)
- Bash, Read, Write, Edit, Glob, Grep

## Missing Tools (add these)
1. **TodoWrite** - Task list management (critical for agentic work)
2. **WebSearch** - Web search capability
3. **WebFetch** - Fetch and parse web pages
4. **NotebookEdit** - Jupyter notebook editing

## Requirements for Each Tool

### TodoWrite
- Manage a todo list with: content, status (pending/in_progress/completed), activeForm
- Store todos in memory or session
- Match Claude Code's TodoWrite interface

### WebSearch
- Take a search query
- Return search results (can use a simple implementation or mock for now)

### WebFetch
- Take a URL and prompt
- Fetch the URL content
- Return processed content

### NotebookEdit
- Edit Jupyter notebook cells
- Support insert, replace, delete modes

## Implementation Pattern

Follow the existing tool pattern in `cc/tools/`:
1. Create `cc/tools/todo.py` (etc.)
2. Inherit from `BaseTool`
3. Implement `execute()` method
4. Add `get_definition()` for API schema
5. Register in `cc/tools/__init__.py`
6. Add tests in `tests/test_tools.py`

## Verification

After implementing each tool:
1. Run `python3 -m pytest tests/test_tools.py -v` - must pass
2. Test the tool manually if possible

## DO NOT
- Break existing functionality (all 112 tests must still pass)
- Create skeleton code
- Skip tests

## Iterate Until Complete

Keep iterating until all 4 tools are implemented and tested.
Signal EXIT_LOOP_NOW only when done.
