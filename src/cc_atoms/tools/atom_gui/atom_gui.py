#!/usr/bin/env python3
"""
atom_gui - Enhanced real-time GUI monitor for atom sessions

Features:
- Resizable left pane with session tree and individual prompts
- Main window with all existing features (README, Session Log tabs)
- Editable prompt view with cut/paste and image support
- Auto-refresh on file changes
"""

import sys
import os
from pathlib import Path

from cc_atoms.tools.atom_gui.gui import MainWindow


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = os.getcwd()

    root_path = Path(root_path).resolve()

    if not root_path.exists():
        print(f"Error: Directory {root_path} does not exist", file=sys.stderr)
        sys.exit(1)

    app = MainWindow(root_path)
    app.run()


if __name__ == "__main__":
    main()
