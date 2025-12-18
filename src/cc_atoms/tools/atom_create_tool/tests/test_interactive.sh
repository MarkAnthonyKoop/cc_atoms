#!/bin/bash
#
# Test interactive mode of atom_create_tool
#

set -e

echo "Testing atom_create_tool in interactive mode..."
echo

# Simulate user input
{
    echo "atom_test_example"
    echo "A simple test tool for demonstration"
    echo "Runs basic diagnostics"
    echo "Validates system configuration"
    echo ""
} | ~/cc_atoms/tools/atom_create_tool/atom_create_tool

echo
echo "=== Verification ==="
echo

# Check if tool was created
TOOL_DIR="$HOME/cc_atoms/tools/atom_test_example"

if [ -d "$TOOL_DIR" ]; then
    echo "✓ Tool directory created: $TOOL_DIR"
else
    echo "✗ Tool directory NOT found"
    exit 1
fi

# Check bash script
if [ -x "$TOOL_DIR/atom_test_example" ]; then
    echo "✓ Bash script created and executable"
else
    echo "✗ Bash script missing or not executable"
    exit 1
fi

# Check system prompt
if [ -f "$HOME/cc_atoms/prompts/ATOM_TEST_EXAMPLE.md" ]; then
    echo "✓ System prompt created"
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
if [ -x "$HOME/cc_atoms/bin/atom_test_example" ]; then
    echo "✓ Launcher created and executable"
else
    echo "✗ Launcher missing or not executable"
    exit 1
fi

echo
echo "=== Testing Basic Mode ==="
echo

# Test basic mode (should not fail)
if ~/cc_atoms/bin/atom_test_example; then
    echo "✓ Basic mode executed successfully"
else
    echo "✗ Basic mode failed"
    exit 1
fi

echo
echo "=== All Tests Passed ==="
echo

# Show created files
echo "Created files:"
ls -lh "$TOOL_DIR"
echo
ls -lh "$HOME/cc_atoms/prompts/ATOM_TEST_EXAMPLE.md"
echo
ls -lh "$HOME/cc_atoms/bin/atom_test_example"
