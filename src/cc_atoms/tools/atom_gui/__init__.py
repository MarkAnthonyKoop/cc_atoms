"""
atom_gui - Real-time session monitor for cc_atoms

Usage:
    atom-gui /path/to/project

Note: main is imported lazily to avoid tkinter dependency for core modules
"""


def main():
    """Entry point - imports lazily to avoid tkinter requirement for core modules"""
    from .atom_gui import main as _main
    return _main()


__all__ = ["main"]
