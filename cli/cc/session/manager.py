"""Session lifecycle management for CC CLI."""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..config.paths import get_session_dir, get_session_file
from .storage import SessionStorage


@dataclass
class SessionInfo:
    """Information about a session."""
    id: str
    project: str
    last_modified: str
    message_count: int


class SessionManager:
    """Manages conversation sessions."""

    def __init__(self, project_path: Path) -> None:
        """Initialize session manager.

        Args:
            project_path: Path to the project
        """
        self.project_path = project_path.absolute()
        self._current_session_id: Optional[str] = None
        self._storage: Optional[SessionStorage] = None

    def create(self) -> str:
        """Create a new session and return its ID.

        Returns:
            New session ID
        """
        session_id = str(uuid.uuid4())
        self._current_session_id = session_id

        # Create empty session file
        session_file = get_session_file(session_id, self.project_path)
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.touch()

        self._storage = SessionStorage(session_file)
        return session_id

    def get_current(self) -> Optional[str]:
        """Get current session ID.

        Returns:
            Current session ID or None
        """
        return self._current_session_id

    def get_recent(self) -> Optional[str]:
        """Get most recent session ID for -c flag.

        Returns:
            Most recent session ID or None
        """
        sessions = self.list_sessions()
        if sessions:
            return sessions[0].id
        return None

    def list_sessions(self) -> List[SessionInfo]:
        """List all sessions for current project.

        Returns:
            List of session info, sorted by last modified (newest first)
        """
        session_dir = get_session_dir(self.project_path)
        if not session_dir.exists():
            return []

        sessions = []
        for session_file in session_dir.glob("*.jsonl"):
            session_id = session_file.stem
            stat = session_file.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # Count messages
            storage = SessionStorage(session_file)
            messages = list(storage.iter_messages())

            sessions.append(SessionInfo(
                id=session_id,
                project=str(self.project_path),
                last_modified=last_modified,
                message_count=len(messages),
            ))

        # Sort by last modified (newest first)
        sessions.sort(key=lambda s: s.last_modified, reverse=True)
        return sessions

    def load(self, session_id: str) -> SessionStorage:
        """Load a session by ID.

        Args:
            session_id: Session ID to load

        Returns:
            Session storage object

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        session_file = get_session_file(session_id, self.project_path)
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        self._current_session_id = session_id
        self._storage = SessionStorage(session_file)
        return self._storage

    def get_storage(self) -> Optional[SessionStorage]:
        """Get current session storage.

        Returns:
            Session storage or None if no session active
        """
        if self._storage is None and self._current_session_id:
            session_file = get_session_file(self._current_session_id, self.project_path)
            self._storage = SessionStorage(session_file)
        return self._storage

    def fork(self, session_id: str) -> str:
        """Create a fork of existing session.

        Args:
            session_id: Session ID to fork

        Returns:
            New session ID

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        source_file = get_session_file(session_id, self.project_path)
        if not source_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        # Create new session
        new_session_id = str(uuid.uuid4())
        new_file = get_session_file(new_session_id, self.project_path)

        # Copy content
        source_storage = SessionStorage(source_file)
        entries = source_storage.read()

        # Update session IDs in entries
        for entry in entries:
            if "sessionId" in entry:
                entry["sessionId"] = new_session_id

        # Write to new file
        new_storage = SessionStorage(new_file)
        new_storage.write(entries)

        return new_session_id

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        session_file = get_session_file(session_id, self.project_path)
        if session_file.exists():
            session_file.unlink()
            if self._current_session_id == session_id:
                self._current_session_id = None
                self._storage = None
            return True
        return False

    def ensure_session(self) -> str:
        """Ensure a session exists, creating one if needed.

        Returns:
            Session ID
        """
        if self._current_session_id is None:
            return self.create()
        return self._current_session_id
