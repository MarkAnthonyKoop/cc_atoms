#!/bin/bash
#
# Test Python version of atom_create_tool in interactive mode
#

set -e

echo "Testing Python atom_create_tool in interactive mode..."
echo

# Clean up any existing test tool
rm -rf ~/cc_atoms/tools/atom_python_test ~/cc_atoms/bin/atom_python_test ~/cc_atoms/prompts/ATOM_PYTHON_TEST.md

# Simulate user input
{
    echo "atom_python_test"
    echo "A simple Python test tool"
    echo "Tests Python implementation"
    echo "Validates direct arg passing"
    echo ""
} | python3 ~/cc_atoms/tools/atom_create_tool/atom_create_tool.py

echo
echo "=== Verification ==="
echo

# Check if tool was created
TOOL_DIR="$HOME/cc_atoms/tools/atom_python_test"

if [ -d "$TOOL_DIR" ]; then
    echo "✓ Tool directory created: $TOOL_DIR"
else
    echo "✗ Tool directory NOT found"
    exit 1
fi

# Check Python script
if [ -x "$TOOL_DIR/atom_python_test.py" ]; then
    echo "✓ Python script created and executable"
else
    echo "✗ Python script missing or not executable"
    exit 1
fi

# Check symlink
if [ -L "$TOOL_DIR/atom_python_test" ]; then
    echo "✓ Symlink created"
else
    echo "✗ Symlink missing"
    exit 1
fi

# Check system prompt
if [ -f "$HOME/cc_atoms/prompts/ATOM_PYTHON_TEST.md" ]; then
    echo "✓ System prompt created in prompts directory"
else
    echo "✗ System prompt missing"
    exit 1
fi

# Check README
if [ -f "$TOOL_DIR/README.md" ]; then
    echo "✓ README.md created"
else
    echo "✗ README.md missing"
    exit 1
fi

# Check launcher
if [ -x "$HOME/cc_atoms/bin/atom_python_test" ]; then
    echo "✓ Launcher created and executable"
else
    echo "✗ Launcher missing or not executable"
    exit 1
fi

echo
echo "=== Testing Tool Execution ==="
echo

# Test that the tool passes args to atom correctly
if ~/cc_atoms/bin/atom_python_test --help 2>&1 | grep -q "atom.py"; then
    echo "✓ Tool correctly passes args to atom"
else
    echo "✗ Tool does not pass args correctly"
    exit 1
fi

echo
echo "=== All Tests Passed ==="
echo

# Show created files
echo "Created files:"
ls -lh "$TOOL_DIR"
echo
ls -lh "$HOME/cc_atoms/prompts/ATOM_PYTHON_TEST.md"
echo
ls -lh "$HOME/cc_atoms/bin/atom_python_test"

# Clean up
echo
echo "Cleaning up test tool..."
rm -rf ~/cc_atoms/tools/atom_python_test ~/cc_atoms/bin/atom_python_test ~/cc_atoms/prompts/ATOM_PYTHON_TEST.md
echo "Done!"
