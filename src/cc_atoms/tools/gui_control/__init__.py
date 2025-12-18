"""
gui_control - macOS GUI automation using embedded atom orchestration

Usage:
    from cc_atoms.tools.gui_control import control_gui

    result = control_gui("Click the Submit button in Safari")
    if result["success"]:
        print(result["output"])
"""

from .gui_control import control_gui, main

__all__ = ["control_gui", "main"]
