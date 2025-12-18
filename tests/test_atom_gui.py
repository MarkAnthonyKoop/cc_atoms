#!/usr/bin/env python3
"""
Tests for atom_gui tool

These tests verify:
1. Core components (parser, history, saver, session) - no tkinter needed
2. GUI module structure (with tkinter check)
3. CLI entry point handling

Note: These tests import core modules directly to avoid tkinter dependency
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Check if tkinter is available
TKINTER_AVAILABLE = False
try:
    import tkinter
    TKINTER_AVAILABLE = True
except ImportError:
    pass


class TestAtomGuiCoreImports:
    """Tests for atom_gui core module imports (no tkinter needed)"""

    def test_core_parser_imports(self):
        """Test that core.parser can be imported"""
        # Import directly from the file, not through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "parser",
            Path(__file__).parent.parent / "src/cc_atoms/tools/atom_gui/core/parser.py"
        )
        parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser_module)
        assert hasattr(parser_module, 'PromptParser')
        print("✓ core.parser imports (PromptParser)")

    def test_core_history_imports(self):
        """Test that core.history can be imported"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "history",
            Path(__file__).parent.parent / "src/cc_atoms/tools/atom_gui/core/history.py"
        )
        history_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(history_module)
        assert hasattr(history_module, 'EditHistory')
        print("✓ core.history imports (EditHistory)")

    def test_core_saver_imports(self):
        """Test that core.saver can be imported"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "saver",
            Path(__file__).parent.parent / "src/cc_atoms/tools/atom_gui/core/saver.py"
        )
        saver_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(saver_module)
        assert hasattr(saver_module, 'SessionSaver')
        print("✓ core.saver imports (SessionSaver)")

    def test_core_session_imports(self):
        """Test that core.session can be imported"""
        from cc_atoms.tools.atom_gui.core.session import SessionInfo, SessionScanner
        assert SessionInfo is not None
        assert SessionScanner is not None
        print("✓ core.session imports (SessionInfo, SessionScanner)")


class TestAtomGuiWithTkinter:
    """Tests that require tkinter"""

    def test_gui_main_window_imports(self):
        """Test that gui.main_window can be imported"""
        if not TKINTER_AVAILABLE:
            print("⚠ gui.main_window skipped (tkinter not available)")
            return

        from cc_atoms.tools.atom_gui.gui.main_window import MainWindow
        assert MainWindow is not None
        print("✓ gui.main_window imports (MainWindow)")

    def test_main_module_imports(self):
        """Test that atom_gui main module can be imported"""
        if not TKINTER_AVAILABLE:
            print("⚠ atom_gui main skipped (tkinter not available)")
            return

        from cc_atoms.tools.atom_gui import main
        assert callable(main)
        print("✓ atom_gui main module imports")


class TestPromptParser:
    """Tests for PromptParser"""

    def _get_parser_class(self):
        """Get PromptParser class without triggering tkinter import"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "parser",
            Path(__file__).parent.parent / "src/cc_atoms/tools/atom_gui/core/parser.py"
        )
        parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser_module)
        return parser_module.PromptParser

    def test_parser_instantiation(self):
        """Test that PromptParser can be instantiated"""
        PromptParser = self._get_parser_class()
        parser = PromptParser()
        assert parser is not None
        print("✓ PromptParser instantiates")

    def test_parser_parse_empty(self):
        """Test parsing empty content"""
        PromptParser = self._get_parser_class()
        result = PromptParser.parse_session_log("")
        assert isinstance(result, list), "Should return list"
        assert len(result) == 0, "Empty content should return empty list"
        print("✓ PromptParser handles empty content")

    def test_parser_parse_session_log(self):
        """Test parsing session log with user and assistant messages"""
        PromptParser = self._get_parser_class()
        content = """## 👤 User
Hello, can you help me?

## 🤖 Assistant
Of course! What do you need?

## 👤 User
Write some code.
"""
        result = PromptParser.parse_session_log(content)
        assert isinstance(result, list), "Should return list"
        assert len(result) == 3, f"Should have 3 prompts, got {len(result)}"
        assert result[0]['type'] == 'user'
        assert result[1]['type'] == 'assistant'
        assert result[2]['type'] == 'user'
        print("✓ PromptParser parses session log correctly")


class TestEditHistory:
    """Tests for EditHistory (undo/redo)"""

    def _get_history_class(self):
        """Get EditHistory class without triggering tkinter import"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "history",
            Path(__file__).parent.parent / "src/cc_atoms/tools/atom_gui/core/history.py"
        )
        history_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(history_module)
        return history_module.EditHistory

    def test_history_instantiation(self):
        """Test that EditHistory can be instantiated"""
        EditHistory = self._get_history_class()
        history = EditHistory()
        assert history is not None
        print("✓ EditHistory instantiates")

    def test_history_add_and_undo(self):
        """Test add_edit and undo operations"""
        EditHistory = self._get_history_class()
        history = EditHistory()

        # Add edits
        history.add_edit("/path/to/file.jsonl", 0, "user", "old1", "new1")
        history.add_edit("/path/to/file.jsonl", 1, "assistant", "old2", "new2")

        # Check can undo
        assert history.can_undo(), "Should be able to undo"

        # Get undo action
        action = history.get_undo_action()
        assert action is not None, "Undo action should not be None"
        assert action['content'] == "old2", "Undo should return old content"
        print("✓ EditHistory add_edit and undo work")

    def test_history_redo(self):
        """Test redo operation"""
        EditHistory = self._get_history_class()
        history = EditHistory()

        history.add_edit("/path/to/file.jsonl", 0, "user", "old", "new")
        history.move_back()  # Undo

        # Check can redo
        assert history.can_redo(), "Should be able to redo"

        # Get redo action
        action = history.get_redo_action()
        assert action is not None, "Redo action should not be None"
        assert action['content'] == "new", "Redo should return new content"
        print("✓ EditHistory redo works")

    def test_history_empty(self):
        """Test empty history state"""
        EditHistory = self._get_history_class()
        history = EditHistory()

        # Empty history
        assert not history.can_undo(), "Empty history can't undo"
        assert not history.can_redo(), "Empty history can't redo"
        assert history.get_undo_action() is None, "Undo should return None"
        print("✓ EditHistory handles empty state")


class TestSessionScanner:
    """Tests for SessionScanner"""

    def _get_session_classes(self):
        """Get session classes"""
        from cc_atoms.tools.atom_gui.core.session import SessionInfo, SessionScanner
        return SessionInfo, SessionScanner

    def test_scanner_instantiation(self):
        """Test that SessionScanner can be instantiated"""
        SessionInfo, SessionScanner = self._get_session_classes()

        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = SessionScanner(Path(tmpdir))
            assert scanner is not None
            print("✓ SessionScanner instantiates")

    def test_scanner_finds_sessions(self):
        """Test that scanner finds session directories"""
        SessionInfo, SessionScanner = self._get_session_classes()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a session-like directory with ## Status (required for detection)
            session_dir = root / "my_session"
            session_dir.mkdir()
            (session_dir / "README.md").write_text("# My Session\n## Status\nCOMPLETE")

            scanner = SessionScanner(root)
            sessions = scanner.scan()

            assert isinstance(sessions, dict), "Should return dict"
            assert len(sessions) == 1, f"Should find 1 session, found {len(sessions)}"
            print(f"✓ SessionScanner finds sessions ({len(sessions)} found)")

    def test_scanner_empty_directory(self):
        """Test scanner with empty directory"""
        SessionInfo, SessionScanner = self._get_session_classes()

        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = SessionScanner(Path(tmpdir))
            sessions = scanner.scan()

            assert isinstance(sessions, dict), "Should return dict even if empty"
            assert len(sessions) == 0, "Empty dir should have no sessions"
            print("✓ SessionScanner handles empty directory")


def main():
    """Run all atom_gui tests"""
    print("Running atom_gui tests...\n")
    print(f"tkinter available: {TKINTER_AVAILABLE}\n")

    try:
        # Core import tests (no tkinter needed)
        print("Testing core imports (no tkinter needed)...")
        test_imports = TestAtomGuiCoreImports()
        test_imports.test_core_parser_imports()
        test_imports.test_core_history_imports()
        test_imports.test_core_saver_imports()
        test_imports.test_core_session_imports()
        print()

        # GUI import tests (tkinter needed)
        print("Testing GUI imports (tkinter needed)...")
        test_gui = TestAtomGuiWithTkinter()
        test_gui.test_gui_main_window_imports()
        test_gui.test_main_module_imports()
        print()

        # PromptParser tests
        print("Testing PromptParser...")
        test_parser = TestPromptParser()
        test_parser.test_parser_instantiation()
        test_parser.test_parser_parse_empty()
        test_parser.test_parser_parse_session_log()
        print()

        # EditHistory tests
        print("Testing EditHistory...")
        test_history = TestEditHistory()
        test_history.test_history_instantiation()
        test_history.test_history_add_and_undo()
        test_history.test_history_redo()
        test_history.test_history_empty()
        print()

        # SessionScanner tests
        print("Testing SessionScanner...")
        test_scanner = TestSessionScanner()
        test_scanner.test_scanner_instantiation()
        test_scanner.test_scanner_finds_sessions()
        test_scanner.test_scanner_empty_directory()
        print()

        print("\n✅ All atom_gui tests passed!")
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
