"""Tests for session module."""

import json
import pytest
from pathlib import Path

from cc.session.storage import SessionStorage
from cc.session.manager import SessionManager


class TestSessionStorage:
    """Tests for SessionStorage class."""

    def test_create_user_entry(self):
        """Test creating a user entry."""
        entry = SessionStorage.create_user_entry(
            content="Hello, Claude!",
            session_id="test-session",
            cwd="/home/user",
            parent_uuid=None,
        )

        assert entry["type"] == "user"
        assert entry["message"]["role"] == "user"
        assert entry["message"]["content"] == "Hello, Claude!"
        assert entry["sessionId"] == "test-session"
        assert entry["cwd"] == "/home/user"
        assert "uuid" in entry
        assert "timestamp" in entry

    def test_create_assistant_entry(self):
        """Test creating an assistant entry."""
        entry = SessionStorage.create_assistant_entry(
            content=[{"type": "text", "text": "Hello!"}],
            session_id="test-session",
            cwd="/home/user",
            parent_uuid="user-uuid",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
        )

        assert entry["type"] == "assistant"
        assert entry["message"]["role"] == "assistant"
        assert entry["message"]["content"] == [{"type": "text", "text": "Hello!"}]
        assert entry["usage"]["inputTokens"] == 100
        assert entry["usage"]["outputTokens"] == 50

    def test_read_write(self, temp_dir):
        """Test reading and writing entries."""
        session_file = temp_dir / "session.jsonl"
        storage = SessionStorage(session_file)

        # Write entries
        entry1 = SessionStorage.create_user_entry("Hello", "sess", "/", None)
        entry2 = SessionStorage.create_assistant_entry([{"type": "text", "text": "Hi"}], "sess", "/", entry1["uuid"])

        storage.append(entry1)
        storage.append(entry2)

        # Read entries
        entries = storage.read()
        assert len(entries) == 2
        assert entries[0]["type"] == "user"
        assert entries[1]["type"] == "assistant"

    def test_iter_messages(self, temp_dir):
        """Test iterating over messages."""
        session_file = temp_dir / "session.jsonl"
        storage = SessionStorage(session_file)

        entry1 = SessionStorage.create_user_entry("Hello", "sess", "/", None)
        entry2 = SessionStorage.create_assistant_entry([{"type": "text", "text": "Hi"}], "sess", "/", entry1["uuid"])

        storage.append(entry1)
        storage.append(entry2)

        messages = list(storage.iter_messages())
        assert len(messages) == 2

    def test_get_messages_for_api(self, temp_dir):
        """Test getting messages formatted for API."""
        session_file = temp_dir / "session.jsonl"
        storage = SessionStorage(session_file)

        entry1 = SessionStorage.create_user_entry("Hello", "sess", "/", None)
        entry2 = SessionStorage.create_assistant_entry([{"type": "text", "text": "Hi"}], "sess", "/", entry1["uuid"])

        storage.append(entry1)
        storage.append(entry2)

        api_messages = storage.get_messages_for_api()
        assert len(api_messages) == 2
        assert api_messages[0]["role"] == "user"
        assert api_messages[0]["content"] == "Hello"
        assert api_messages[1]["role"] == "assistant"


class TestSessionManager:
    """Tests for SessionManager class."""

    def _patch_session_paths(self, temp_dir):
        """Helper to patch session paths."""
        import cc.config.paths
        import cc.session.manager as manager_module

        session_dir = temp_dir / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        orig_get_session_dir = cc.config.paths.get_session_dir
        orig_get_session_file = cc.config.paths.get_session_file

        cc.config.paths.get_session_dir = lambda p: session_dir
        cc.config.paths.get_session_file = lambda sid, p: session_dir / f"{sid}.jsonl"

        # Also patch in the manager module since it imports directly
        manager_module.get_session_dir = lambda p: session_dir
        manager_module.get_session_file = lambda sid, p: session_dir / f"{sid}.jsonl"

        return orig_get_session_dir, orig_get_session_file

    def _restore_session_paths(self, orig_dir, orig_file):
        """Helper to restore session paths."""
        import cc.config.paths
        import cc.session.manager as manager_module

        cc.config.paths.get_session_dir = orig_dir
        cc.config.paths.get_session_file = orig_file
        manager_module.get_session_dir = orig_dir
        manager_module.get_session_file = orig_file

    def test_create_session(self, temp_dir, monkeypatch):
        """Test creating a new session."""
        orig_dir, orig_file = self._patch_session_paths(temp_dir)

        try:
            manager = SessionManager(temp_dir)
            session_id = manager.create()

            assert session_id is not None
            assert manager.get_current() == session_id
        finally:
            self._restore_session_paths(orig_dir, orig_file)

    def test_list_sessions(self, temp_dir, monkeypatch):
        """Test listing sessions."""
        orig_dir, orig_file = self._patch_session_paths(temp_dir)

        try:
            manager = SessionManager(temp_dir)

            # Create a few sessions
            manager.create()
            manager.create()
            manager.create()

            sessions = manager.list_sessions()
            assert len(sessions) == 3
        finally:
            self._restore_session_paths(orig_dir, orig_file)

    def test_get_recent(self, temp_dir, monkeypatch):
        """Test getting most recent session."""
        orig_dir, orig_file = self._patch_session_paths(temp_dir)

        try:
            manager = SessionManager(temp_dir)
            manager.create()

            recent = manager.get_recent()
            assert recent is not None
        finally:
            self._restore_session_paths(orig_dir, orig_file)

    def test_ensure_session(self, temp_dir, monkeypatch):
        """Test ensuring a session exists."""
        orig_dir, orig_file = self._patch_session_paths(temp_dir)

        try:
            manager = SessionManager(temp_dir)
            session_id = manager.ensure_session()

            assert session_id is not None
            # Calling again should return the same session
            assert manager.ensure_session() == session_id
        finally:
            self._restore_session_paths(orig_dir, orig_file)
