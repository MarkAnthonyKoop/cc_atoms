"""Session management utilities for atom_gui."""
import os
import subprocess
import sys
from pathlib import Path

from .parser import PromptParser
from .saver import SessionSaver


class SessionInfo:
    """Information about an atom session."""

    def __init__(self, path, readme_path=None):
        self.path = Path(path)
        self.readme_path = Path(readme_path) if readme_path else self.path / "README.md"
        self.status = "UNKNOWN"
        self.overview = ""
        self.progress = []
        self.last_modified = 0
        self.session_log_path = self.path / "session_log.md"
        self.session_content = ""
        self.session_log_mtime = 0
        self.prompts = []

        self._load_info()

    def _load_info(self):
        """Load session info from README.md."""
        if not self.readme_path.exists():
            return

        self.last_modified = self.readme_path.stat().st_mtime

        try:
            content = self.readme_path.read_text()

            # Parse status
            for line in content.split('\n'):
                if line.startswith('## Status'):
                    idx = content.find(line) + len(line)
                    rest = content[idx:].strip()
                    if rest:
                        self.status = rest.split('\n')[0].strip()
                    break

            # Parse overview
            if '## Overview' in content:
                start = content.find('## Overview') + len('## Overview')
                end = content.find('\n##', start)
                if end == -1:
                    end = len(content)
                self.overview = content[start:end].strip()

            # Parse progress
            self.progress = []
            in_progress = False
            for line in content.split('\n'):
                if line.startswith('## Progress'):
                    in_progress = True
                    continue
                if in_progress:
                    if line.startswith('##'):
                        break
                    if line.strip().startswith('- ['):
                        self.progress.append(line.strip())

        except Exception as e:
            print(f"Error reading {self.readme_path}: {e}", file=sys.stderr)

    def load_session_log(self, force=False):
        """Load the session log content."""
        # Try to load from local session_log.md first
        if self.session_log_path.exists():
            try:
                current_mtime = self.session_log_path.stat().st_mtime

                # Only reload if forced or file has changed
                if force or current_mtime > self.session_log_mtime:
                    self.session_content = self.session_log_path.read_text()
                    self.session_log_mtime = current_mtime

                    # Parse prompts from markdown
                    self.prompts = PromptParser.parse_session_log(self.session_content)
                    return True

                return self.session_content != ""

            except Exception as e:
                print(f"Error reading session log: {e}", file=sys.stderr)

        # If no local log, try to load directly from JSONL
        jsonl_file = SessionSaver.find_jsonl_file(self.path)
        if jsonl_file:
            try:
                # Parse prompts directly from JSONL
                self.prompts = PromptParser.parse_jsonl_file(jsonl_file)
                self.session_content = f"[Loaded {len(self.prompts)} prompts from {jsonl_file.name}]"
                return True
            except Exception as e:
                print(f"Error loading from JSONL: {e}", file=sys.stderr)

        return False

    def extract_session_log(self):
        """Extract session log using atom_session_analyzer."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.path)

            result = subprocess.run(
                ["atom_session_analyzer"],
                capture_output=True,
                text=True,
                timeout=10
            )

            os.chdir(original_dir)

            if result.returncode == 0:
                return self.load_session_log(force=True)

        except Exception as e:
            print(f"Error extracting session log: {e}", file=sys.stderr)

        return False

    def refresh(self):
        """Refresh session info if file has changed."""
        if self.readme_path.exists():
            current_mtime = self.readme_path.stat().st_mtime
            if current_mtime > self.last_modified:
                self._load_info()
                return True
        return False


class SessionScanner:
    """Scans directory tree for atom sessions."""

    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.sessions = {}

    def scan(self):
        """Scan for all README.md files indicating atom sessions."""
        self.sessions = {}

        for readme_path in self.root_path.rglob("README.md"):
            try:
                content = readme_path.read_text()
                if '## Status' in content:
                    session_dir = readme_path.parent
                    rel_path = session_dir.relative_to(self.root_path)
                    self.sessions[str(rel_path)] = SessionInfo(session_dir, readme_path)
            except Exception as e:
                print(f"Error checking {readme_path}: {e}", file=sys.stderr)

        return self.sessions

    def get_latest_session(self):
        """Get the most recently modified session."""
        if not self.sessions:
            return None

        latest = max(self.sessions.values(), key=lambda s: s.last_modified)
        return latest
