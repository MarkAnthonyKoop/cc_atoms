#!/usr/bin/env python3
"""
atom_gui - Enhanced real-time GUI monitor for atom sessions

Features:
- Resizable left pane with session tree and individual prompts
- Main window with all existing features (README, Session Log tabs)
- Editable prompt view with cut/paste and image support
- Auto-refresh on file changes
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import sys
import os
from pathlib import Path
import json
import time
import re
from datetime import datetime
import threading


class PromptParser:
    """Parse session logs to extract individual prompts and responses."""

    @staticmethod
    def parse_session_log(content):
        """Extract prompts and responses from session log markdown."""
        prompts = []

        # Pattern to match user prompts and assistant responses
        sections = re.split(r'^## (👤 User|🤖 Assistant)', content, flags=re.MULTILINE)

        current_type = None
        current_content = []

        for i, section in enumerate(sections):
            if section in ['👤 User', '🤖 Assistant']:
                # Save previous section
                if current_type and current_content:
                    text = ''.join(current_content).strip()
                    if text:
                        prompts.append({
                            'type': current_type,
                            'content': text,
                            'preview': text[:80].replace('\n', ' ')
                        })

                # Start new section
                current_type = 'user' if 'User' in section else 'assistant'
                current_content = []
            else:
                current_content.append(section)

        # Save last section
        if current_type and current_content:
            text = ''.join(current_content).strip()
            if text:
                prompts.append({
                    'type': current_type,
                    'content': text,
                    'preview': text[:80].replace('\n', ' ')
                })

        return prompts

    @staticmethod
    def parse_jsonl_file(jsonl_path):
        """Extract prompts directly from JSONL file."""
        prompts = []

        try:
            lines = Path(jsonl_path).read_text().splitlines()

            for line in lines:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    # Check if this is a user or assistant message
                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            content_raw = data.get("message", {}).get("content", "")

                            # Content can be string or list of blocks
                            content = ""
                            if isinstance(content_raw, str):
                                content = content_raw
                            elif isinstance(content_raw, list):
                                # Extract text from content blocks
                                for block in content_raw:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        content += block.get("text", "")
                                    elif isinstance(block, str):
                                        content += block

                            if content:
                                prompts.append({
                                    'type': role,
                                    'content': content,
                                    'preview': content[:80].replace('\n', ' ')
                                })

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Error parsing JSONL: {e}", file=sys.stderr)

        return prompts


class EditHistory:
    """Manages undo/redo history for JSONL edits."""

    def __init__(self):
        self.history = []  # List of (jsonl_path, prompt_index, prompt_type, old_content, new_content)
        self.current_position = -1  # Position in history (-1 = no history)

    def add_edit(self, jsonl_path, prompt_index, prompt_type, old_content, new_content):
        """Add an edit to history."""
        # Remove any "future" history if we're not at the end
        if self.current_position < len(self.history) - 1:
            self.history = self.history[:self.current_position + 1]

        # Add new edit
        self.history.append({
            'jsonl_path': str(jsonl_path),
            'prompt_index': prompt_index,
            'prompt_type': prompt_type,
            'old_content': old_content,
            'new_content': new_content,
            'timestamp': time.time()
        })

        self.current_position = len(self.history) - 1

    def can_undo(self):
        """Check if undo is available."""
        return self.current_position >= 0

    def can_redo(self):
        """Check if redo is available."""
        return self.current_position < len(self.history) - 1

    def get_undo_action(self):
        """Get the action to undo (returns None if can't undo)."""
        if not self.can_undo():
            return None

        action = self.history[self.current_position]
        return {
            'jsonl_path': action['jsonl_path'],
            'prompt_index': action['prompt_index'],
            'prompt_type': action['prompt_type'],
            'content': action['old_content']  # Restore old content
        }

    def get_redo_action(self):
        """Get the action to redo (returns None if can't redo)."""
        if not self.can_redo():
            return None

        action = self.history[self.current_position + 1]
        return {
            'jsonl_path': action['jsonl_path'],
            'prompt_index': action['prompt_index'],
            'prompt_type': action['prompt_type'],
            'content': action['new_content']  # Restore new content
        }

    def move_back(self):
        """Move back in history (after undo)."""
        if self.can_undo():
            self.current_position -= 1

    def move_forward(self):
        """Move forward in history (after redo)."""
        if self.can_redo():
            self.current_position += 1

    def get_history_info(self):
        """Get info about current history state."""
        return {
            'total': len(self.history),
            'position': self.current_position + 1,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo()
        }


class SessionSaver:
    """Handles saving edits back to JSONL session files."""

    @staticmethod
    def find_jsonl_file(session_dir):
        """Find the JSONL session file for a given session directory."""
        # Claude Code stores sessions in ~/.claude/projects/
        claude_projects = Path.home() / ".claude" / "projects"

        if not claude_projects.exists():
            return None

        # Convert session path to Claude's format: -path-to-dir
        try:
            session_path_str = str(session_dir.resolve())
            # Remove leading slash, replace / and _ with -
            mangled_path = session_path_str.replace("/", "-").replace("_", "-")

            project_dir = claude_projects / mangled_path

            if not project_dir.exists():
                return None

            # Find the most recent JSONL file (can be session-*.jsonl or UUID.jsonl)
            jsonl_files = sorted(project_dir.glob("*.jsonl"),
                               key=lambda p: p.stat().st_mtime,
                               reverse=True)

            if jsonl_files:
                return jsonl_files[0]

        except Exception as e:
            print(f"Error finding JSONL file: {e}", file=sys.stderr)

        return None

    @staticmethod
    def get_original_content(session_dir, prompt_index, prompt_type):
        """Get the original content of a prompt before editing."""
        jsonl_file = SessionSaver.find_jsonl_file(session_dir)

        if not jsonl_file:
            return None

        try:
            lines = jsonl_file.read_text().splitlines()
            message_count = 0

            for line in lines:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            target_type = "user" if prompt_type == "user" else "assistant"

                            if role == target_type:
                                if message_count == prompt_index:
                                    # Found the message
                                    if "message" in data and "content" in data["message"]:
                                        return data["message"]["content"]

                                message_count += 1

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Error getting original content: {e}", file=sys.stderr)

        return None

    @staticmethod
    def save_prompt_edit(session_dir, prompt_index, new_content, prompt_type):
        """Save edited prompt back to JSONL file."""
        jsonl_file = SessionSaver.find_jsonl_file(session_dir)

        if not jsonl_file:
            return False, "Could not find JSONL session file"

        try:
            # Read all lines
            lines = jsonl_file.read_text().splitlines()

            # Track user/assistant messages
            message_count = 0
            modified = False

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    # Check if this is a user or assistant message
                    # Format: {"type": "user", "message": {"role": "user", "content": "..."}}
                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            # Check if this is the message we want to edit
                            target_type = "user" if prompt_type == "user" else "assistant"

                            if role == target_type:
                                if message_count == prompt_index:
                                    # Found the message to edit
                                    if "message" in data and "content" in data["message"]:
                                        # Update the content (string format)
                                        data["message"]["content"] = new_content
                                        modified = True

                                        # Update the line
                                        lines[i] = json.dumps(data)
                                        break

                                message_count += 1

                except json.JSONDecodeError:
                    continue

            if not modified:
                return False, f"Could not find message at index {prompt_index}"

            # Write back to file
            jsonl_file.write_text('\n'.join(lines) + '\n')

            return True, "Successfully saved to JSONL file"

        except Exception as e:
            return False, f"Error saving: {str(e)}"

    @staticmethod
    def apply_undo_redo(jsonl_path, prompt_index, content, prompt_type):
        """Apply an undo or redo action directly to JSONL file."""
        jsonl_file = Path(jsonl_path)

        if not jsonl_file.exists():
            return False, f"JSONL file not found: {jsonl_file}"

        try:
            lines = jsonl_file.read_text().splitlines()
            message_count = 0
            modified = False

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            target_type = "user" if prompt_type == "user" else "assistant"

                            if role == target_type:
                                if message_count == prompt_index:
                                    # Found the message
                                    if "message" in data and "content" in data["message"]:
                                        data["message"]["content"] = content
                                        modified = True
                                        lines[i] = json.dumps(data)
                                        break

                                message_count += 1

                except json.JSONDecodeError:
                    continue

            if not modified:
                return False, f"Could not find message at index {prompt_index}"

            # Write back to file
            jsonl_file.write_text('\n'.join(lines) + '\n')

            return True, "Successfully applied undo/redo"

        except Exception as e:
            return False, f"Error applying undo/redo: {str(e)}"


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


class MainWindow:
    """Main window with resizable panes."""

    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.scanner = SessionScanner(root_path)
        self.current_session = None
        self.current_prompt = None
        self.current_prompt_index = None
        self.auto_refresh = True
        self.edit_history = EditHistory()

        # Store tree item data (since treeview doesn't have custom columns)
        self.tree_item_data = {}  # item_id -> {'session_path': ..., 'prompt_index': ...}

        # Create main window
        self.window = tk.Tk()
        self.window.title(f"Atom GUI - {root_path}")
        self.window.geometry("1400x800")

        self._create_widgets()
        self._start_refresh_thread()

    def _create_widgets(self):
        """Create GUI widgets."""
        # Top toolbar
        toolbar = tk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Button(toolbar, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Extract Log", command=self.extract_log).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Expand All", command=self.expand_all_sessions).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Collapse All", command=self.collapse_all).pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        tk.Button(toolbar, text="Save Edits", command=self.save_edits).pack(side=tk.LEFT, padx=2)

        self.undo_button = tk.Button(toolbar, text="Undo", command=self.undo_edit, state=tk.DISABLED)
        self.undo_button.pack(side=tk.LEFT, padx=2)

        self.redo_button = tk.Button(toolbar, text="Redo", command=self.redo_edit, state=tk.DISABLED)
        self.redo_button.pack(side=tk.LEFT, padx=2)

        self.history_label = tk.Label(toolbar, text="", fg="gray", font=("Arial", 8))
        self.history_label.pack(side=tk.LEFT, padx=5)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        self.auto_refresh_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            toolbar,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh
        ).pack(side=tk.LEFT, padx=2)

        self.status_label = tk.Label(toolbar, text="Loading...", fg="blue")
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # Main paned window (resizable)
        self.paned = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, sashwidth=5, bg='gray')
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left pane - Session tree
        self._create_left_pane()

        # Right pane - Content display
        self._create_right_pane()

        # Bind F5 to refresh
        self.window.bind('<F5>', lambda e: self.refresh())

        # Initial scan
        self.refresh()

    def _create_left_pane(self):
        """Create left pane with session and prompt tree."""
        left_frame = tk.Frame(self.paned, width=350)
        self.paned.add(left_frame, minsize=200)

        # Label
        tk.Label(left_frame, text="Sessions & Prompts", font=("Arial", 10, "bold")).pack(
            side=tk.TOP, pady=5
        )

        # Tree view
        tree_container = tk.Frame(left_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        vsb = tk.Scrollbar(tree_container, orient="vertical")
        hsb = tk.Scrollbar(tree_container, orient="horizontal")

        self.session_tree = ttk.Treeview(
            tree_container,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=self.session_tree.yview)
        hsb.config(command=self.session_tree.xview)

        self.session_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Bind selection
        self.session_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def _create_right_pane(self):
        """Create right pane with tabs."""
        right_frame = tk.Frame(self.paned)
        self.paned.add(right_frame, minsize=400)

        # Session info panel (at top)
        info_frame = tk.LabelFrame(right_frame, text="Current Session", padx=5, pady=5)
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.path_label = tk.Label(info_frame, text="Path: ", anchor=tk.W, font=("Courier", 9))
        self.path_label.pack(fill=tk.X)

        self.status_info = tk.Label(info_frame, text="Status: ", anchor=tk.W, font=("Courier", 10, "bold"))
        self.status_info.pack(fill=tk.X)

        # Notebook for tabs
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Overview tab
        self._create_overview_tab()

        # README tab
        self._create_readme_tab()

        # Session log tab
        self._create_session_log_tab()

        # Session Outline tab (vim-fold style)
        self._create_session_outline_tab()

        # Editable prompt tab
        self._create_prompt_editor_tab()

    def _create_overview_tab(self):
        """Create overview tab."""
        overview_frame = tk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="Overview")

        tk.Label(overview_frame, text="Overview:", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=2)
        self.overview_text = tk.Text(overview_frame, height=4, wrap=tk.WORD, font=("Arial", 9))
        self.overview_text.pack(fill=tk.X, padx=5)

        tk.Label(overview_frame, text="Progress:", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=2)
        self.progress_text = tk.Text(overview_frame, height=8, wrap=tk.WORD, font=("Courier", 9))
        self.progress_text.pack(fill=tk.BOTH, expand=True, padx=5)

    def _create_readme_tab(self):
        """Create README tab."""
        readme_frame = tk.Frame(self.notebook)
        self.notebook.add(readme_frame, text="README.md")

        self.readme_text = scrolledtext.ScrolledText(
            readme_frame,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.readme_text.pack(fill=tk.BOTH, expand=True)

    def _create_session_log_tab(self):
        """Create session log tab."""
        log_frame = tk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Session Log")

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_prompt_editor_tab(self):
        """Create editable prompt tab."""
        editor_frame = tk.Frame(self.notebook)
        self.notebook.add(editor_frame, text="Edit Prompt")

        # Toolbar for editor
        editor_toolbar = tk.Frame(editor_frame)
        editor_toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Button(editor_toolbar, text="Insert Image", command=self.insert_image).pack(side=tk.LEFT, padx=2)
        tk.Button(editor_toolbar, text="Cut", command=self.cut_text).pack(side=tk.LEFT, padx=2)
        tk.Button(editor_toolbar, text="Copy", command=self.copy_text).pack(side=tk.LEFT, padx=2)
        tk.Button(editor_toolbar, text="Paste", command=self.paste_text).pack(side=tk.LEFT, padx=2)

        self.prompt_type_label = tk.Label(editor_toolbar, text="", font=("Arial", 9, "bold"))
        self.prompt_type_label.pack(side=tk.RIGHT, padx=5)

        # Editable text area
        self.prompt_editor = scrolledtext.ScrolledText(
            editor_frame,
            wrap=tk.WORD,
            font=("Courier", 9),
            undo=True
        )
        self.prompt_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status
        self.editor_status = tk.Label(editor_frame, text="Select a prompt from the tree", fg="gray")
        self.editor_status.pack(side=tk.BOTTOM, pady=2)

    def _start_refresh_thread(self):
        """Start background thread for auto-refresh."""
        def refresh_loop():
            while True:
                time.sleep(2)
                if self.auto_refresh and self.current_session:
                    if self.current_session.refresh():
                        self.window.after(0, self.update_display)

        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()

    def toggle_auto_refresh(self):
        """Toggle auto-refresh."""
        self.auto_refresh = self.auto_refresh_var.get()

    def refresh(self):
        """Scan for sessions and update display."""
        self.status_label.config(text="Scanning...", fg="blue")
        self.window.update()

        self.scanner.scan()
        self.populate_tree()

        # Select latest session if none selected
        if not self.current_session:
            self.current_session = self.scanner.get_latest_session()
            if self.current_session:
                self.current_session.load_session_log()

        self.update_display()

        self.status_label.config(
            text=f"Found {len(self.scanner.sessions)} sessions - Last update: {datetime.now().strftime('%H:%M:%S')}",
            fg="green"
        )

    def populate_tree(self):
        """Populate tree with directory structure and sessions (only dirs with sessions)."""
        # Clear existing
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)

        # Clear tree item data
        self.tree_item_data = {}

        # Build directory hierarchy (only for paths that have sessions)
        dir_nodes = {}  # path -> tree_item_id

        # Create root project directory node
        root_node_id = self.session_tree.insert(
            "",
            "end",
            text=f"📁 {self.root_path.name}",
            tags=("directory",)
        )
        dir_nodes["__root__"] = root_node_id  # Special key for root

        # Sort sessions by path to process in order
        sorted_sessions = sorted(self.scanner.sessions.items())

        for rel_path, session in sorted_sessions:
            # Handle root session (path = ".") specially
            if rel_path == ".":
                # Root session goes directly under root node
                parent_id = root_node_id
            else:
                # All other sessions: build directory hierarchy starting from root
                path_parts = Path(rel_path).parts
                current_path = ""
                parent_id = root_node_id  # Start from root project node

                for i, part in enumerate(path_parts):
                    if current_path:
                        current_path = str(Path(current_path) / part)
                    else:
                        current_path = part

                    # Check if we already created this directory node
                    if current_path not in dir_nodes:
                        # Create directory node (only created when needed for sessions)
                        dir_id = self.session_tree.insert(
                            parent_id,
                            "end",
                            text=f"📁 {part}",
                            tags=("directory",)
                        )
                        dir_nodes[current_path] = dir_id

                    parent_id = dir_nodes[current_path]

            # Now add session under this directory
            session_display = session.overview[:30] + "..." if len(session.overview) > 30 else session.overview
            if not session_display:
                session_display = "Session"

            session_id = self.session_tree.insert(
                parent_id,
                "end",
                text=f"📄 {session_display}",
                tags=("session",)
            )

            # Store session reference
            self.tree_item_data[session_id] = {
                'session_path': str(rel_path),
                'prompt_index': None,
                'is_session': True
            }

            # Try to load prompts (from session_log.md or JSONL)
            if session.load_session_log():
                if session.prompts:
                    for i, prompt in enumerate(session.prompts):
                        icon = "👤" if prompt['type'] == 'user' else "🤖"
                        prompt_text = f"{icon} {prompt['preview']}"

                        prompt_id = self.session_tree.insert(
                            session_id,
                            "end",
                            text=prompt_text,
                            tags=("prompt",)
                        )

                        # Store prompt reference
                        self.tree_item_data[prompt_id] = {
                            'session_path': str(rel_path),
                            'prompt_index': i,
                            'is_session': False
                        }
                else:
                    # Loaded but no prompts found
                    placeholder = self.session_tree.insert(
                        session_id,
                        "end",
                        text="(no prompts in this session)",
                        tags=("placeholder",)
                    )
            else:
                # No Claude Code session found
                placeholder = self.session_tree.insert(
                    session_id,
                    "end",
                    text="(no Claude Code session)",
                    tags=("placeholder",)
                )

        # Configure colors
        self.session_tree.tag_configure("directory", foreground="darkblue", font=("Arial", 9, "bold"))
        self.session_tree.tag_configure("session", foreground="blue", font=("Arial", 9))
        self.session_tree.tag_configure("prompt", foreground="black")
        self.session_tree.tag_configure("placeholder", foreground="gray", font=("Arial", 9, "italic"))

    def on_tree_select(self, event):
        """Handle tree selection."""
        selection = self.session_tree.selection()
        if not selection:
            return

        item = selection[0]

        try:
            # Get data from our dict instead of treeview columns
            item_data = self.tree_item_data.get(item, {})
            session_path = item_data.get('session_path')
            prompt_index = item_data.get('prompt_index')

            if session_path and session_path in self.scanner.sessions:
                session = self.scanner.sessions[session_path]

                # If clicking on a session (not a prompt)
                if prompt_index is None:
                    self.current_session = session
                    self.current_prompt = None
                    self.current_session.load_session_log()
                    self.update_display()
                else:
                    # Clicking on a specific prompt
                    self.current_session = session
                    self.current_session.load_session_log()

                    if 0 <= prompt_index < len(session.prompts):
                        self.current_prompt = session.prompts[prompt_index]
                        self.current_prompt_index = prompt_index
                        self.update_display()
                        self.show_prompt_editor()

        except Exception as e:
            print(f"Error in tree selection: {e}", file=sys.stderr)

    def expand_all_sessions(self):
        """Expand all items in the tree to show all prompts."""
        def expand_recursive(item):
            self.session_tree.item(item, open=True)
            for child in self.session_tree.get_children(item):
                expand_recursive(child)

        for item in self.session_tree.get_children():
            expand_recursive(item)

        self.status_label.config(text="Expanded all sessions", fg="green")

    def collapse_all(self):
        """Collapse all items in the tree."""
        def collapse_recursive(item):
            self.session_tree.item(item, open=False)
            for child in self.session_tree.get_children(item):
                collapse_recursive(child)

        for item in self.session_tree.get_children():
            collapse_recursive(item)

        self.status_label.config(text="Collapsed all sessions", fg="green")

    def update_history_buttons(self):
        """Update undo/redo button states based on history."""
        info = self.edit_history.get_history_info()

        # Update button states
        if info['can_undo']:
            self.undo_button.config(state=tk.NORMAL)
        else:
            self.undo_button.config(state=tk.DISABLED)

        if info['can_redo']:
            self.redo_button.config(state=tk.NORMAL)
        else:
            self.redo_button.config(state=tk.DISABLED)

        # Update history label
        if info['total'] > 0:
            self.history_label.config(text=f"History: {info['position']}/{info['total']}")
        else:
            self.history_label.config(text="")

    def show_prompt_editor(self):
        """Show the prompt editor with current prompt."""
        if not self.current_prompt:
            return

        # Switch to editor tab
        self.notebook.select(3)  # Edit Prompt tab

        # Update editor
        self.prompt_editor.delete(1.0, tk.END)
        self.prompt_editor.insert(1.0, self.current_prompt['content'])

        # Update type label
        prompt_type = "User Prompt" if self.current_prompt['type'] == 'user' else "Assistant Response"
        self.prompt_type_label.config(
            text=f"Editing: {prompt_type}",
            fg="blue" if self.current_prompt['type'] == 'user' else "green"
        )

        self.editor_status.config(text="Edit the prompt above and click 'Save Edits' to save changes", fg="blue")

    def update_display(self):
        """Update display with current session info."""
        if not self.current_session:
            self.path_label.config(text="Path: No sessions found")
            self.status_info.config(text="Status: N/A")
            self.overview_text.delete(1.0, tk.END)
            self.progress_text.delete(1.0, tk.END)
            self.readme_text.delete(1.0, tk.END)
            self.log_text.delete(1.0, tk.END)
            return

        # Update info panel
        self.path_label.config(text=f"Path: {self.current_session.path}")

        status_color = {
            "COMPLETE": "green",
            "IN_PROGRESS": "blue",
            "BLOCKED": "red",
            "NEEDS_DECOMPOSITION": "orange"
        }.get(self.current_session.status, "black")

        self.status_info.config(
            text=f"Status: {self.current_session.status}",
            fg=status_color
        )

        # Update overview tab
        self.overview_text.delete(1.0, tk.END)
        self.overview_text.insert(1.0, self.current_session.overview)

        self.progress_text.delete(1.0, tk.END)
        self.progress_text.insert(1.0, '\n'.join(self.current_session.progress))

        # Update README tab
        self.readme_text.delete(1.0, tk.END)
        if self.current_session.readme_path.exists():
            try:
                readme_content = self.current_session.readme_path.read_text()
                self.readme_text.insert(1.0, readme_content)
            except Exception as e:
                self.readme_text.insert(1.0, f"Error reading README: {e}")

        # Update session log tab
        self.log_text.delete(1.0, tk.END)
        if self.current_session.session_content:
            self.log_text.insert(1.0, self.current_session.session_content)

    def extract_log(self):
        """Extract session log for current session."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please select a session from the tree first")
            return

        self.status_label.config(text=f"Extracting session log for {self.current_session.path.name}...", fg="blue")
        self.window.update()

        if self.current_session.extract_session_log():
            self.populate_tree()  # Refresh tree to show new prompts
            self.update_display()
            self.status_label.config(text=f"Session log extracted for {self.current_session.path.name}", fg="green")
        else:
            self.status_label.config(text="Failed to extract session log", fg="red")
            messagebox.showerror(
                "Extraction Failed",
                f"Failed to extract session log for {self.current_session.path}.\n\n"
                "Make sure:\n"
                "1. atom_session_analyzer is installed\n"
                "2. This directory has an active Claude Code session\n"
                "3. The session is in ~/.claude/projects/"
            )

    def insert_image(self):
        """Insert image reference into prompt."""
        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )

        if filename:
            # Insert image reference at cursor
            image_ref = f"\n[Image: {filename}]\n"
            self.prompt_editor.insert(tk.INSERT, image_ref)
            self.editor_status.config(text=f"Inserted image reference: {Path(filename).name}", fg="green")

    def cut_text(self):
        """Cut selected text."""
        try:
            self.prompt_editor.event_generate("<<Cut>>")
            self.editor_status.config(text="Text cut to clipboard", fg="green")
        except:
            pass

    def copy_text(self):
        """Copy selected text."""
        try:
            self.prompt_editor.event_generate("<<Copy>>")
            self.editor_status.config(text="Text copied to clipboard", fg="green")
        except:
            pass

    def paste_text(self):
        """Paste text from clipboard."""
        try:
            self.prompt_editor.event_generate("<<Paste>>")
            self.editor_status.config(text="Text pasted from clipboard", fg="green")
        except:
            pass

    def save_edits(self):
        """Save edits to prompt."""
        if not self.current_prompt:
            messagebox.showinfo("No Prompt Selected", "Please select a prompt from the tree to edit")
            return

        if not self.current_session:
            messagebox.showerror("No Session", "No session selected")
            return

        edited_content = self.prompt_editor.get(1.0, tk.END).strip()

        # Confirm save
        result = messagebox.askyesno(
            "Save Edits",
            "This will modify the Claude Code session JSONL file.\n\n"
            "The changes will affect the original session data.\n\n"
            "Do you want to save?"
        )

        if not result:
            self.editor_status.config(text="Save cancelled", fg="gray")
            return

        # Get prompt index from tree
        try:
            selection = self.session_tree.selection()
            if selection:
                item = selection[0]
                item_data = self.tree_item_data.get(item, {})
                prompt_index = item_data.get('prompt_index')

                if prompt_index is None:
                    messagebox.showerror("Error", "No prompt selected")
                    return

                # Get original content for history
                original_content = SessionSaver.get_original_content(
                    self.current_session.path,
                    prompt_index,
                    self.current_prompt['type']
                )

                if original_content is None:
                    messagebox.showerror("Error", "Could not get original content")
                    return

                # Save to JSONL
                self.status_label.config(text="Saving to JSONL...", fg="blue")
                self.window.update()

                success, message = SessionSaver.save_prompt_edit(
                    self.current_session.path,
                    prompt_index,
                    edited_content,
                    self.current_prompt['type']
                )

                if success:
                    # Add to history
                    jsonl_file = SessionSaver.find_jsonl_file(self.current_session.path)
                    if jsonl_file:
                        self.edit_history.add_edit(
                            jsonl_file,
                            prompt_index,
                            self.current_prompt['type'],
                            original_content,
                            edited_content
                        )
                        self.update_history_buttons()

                    # Update prompt content in memory
                    self.current_prompt['content'] = edited_content

                    self.editor_status.config(text=f"✓ {message}", fg="green")
                    self.status_label.config(text="Saved successfully", fg="green")

                    # Re-extract session log to see changes
                    if messagebox.askyesno("Update Session Log",
                                          "Save successful! Extract updated session log?"):
                        self.extract_log()
                else:
                    self.editor_status.config(text=f"✗ {message}", fg="red")
                    self.status_label.config(text="Save failed", fg="red")
                    messagebox.showerror("Save Failed", message)

        except Exception as e:
            error_msg = f"Error saving: {str(e)}"
            self.editor_status.config(text=error_msg, fg="red")
            self.status_label.config(text="Save failed", fg="red")
            messagebox.showerror("Save Error", error_msg)

    def undo_edit(self):
        """Undo the last edit."""
        if not self.edit_history.can_undo():
            return

        action = self.edit_history.get_undo_action()
        if not action:
            return

        # Apply undo
        self.status_label.config(text="Undoing...", fg="blue")
        self.window.update()

        success, message = SessionSaver.apply_undo_redo(
            action['jsonl_path'],
            action['prompt_index'],
            action['content'],
            action['prompt_type']
        )

        if success:
            self.edit_history.move_back()
            self.update_history_buttons()
            self.status_label.config(text="Undo successful", fg="green")
            self.editor_status.config(text="✓ Undo applied", fg="green")

            # Re-extract to show changes
            if messagebox.askyesno("Update Display", "Undo successful! Extract updated session log?"):
                self.extract_log()
        else:
            self.status_label.config(text="Undo failed", fg="red")
            self.editor_status.config(text=f"✗ {message}", fg="red")
            messagebox.showerror("Undo Failed", message)

    def redo_edit(self):
        """Redo the last undone edit."""
        if not self.edit_history.can_redo():
            return

        action = self.edit_history.get_redo_action()
        if not action:
            return

        # Apply redo
        self.status_label.config(text="Redoing...", fg="blue")
        self.window.update()

        success, message = SessionSaver.apply_undo_redo(
            action['jsonl_path'],
            action['prompt_index'],
            action['content'],
            action['prompt_type']
        )

        if success:
            self.edit_history.move_forward()
            self.update_history_buttons()
            self.status_label.config(text="Redo successful", fg="green")
            self.editor_status.config(text="✓ Redo applied", fg="green")

            # Re-extract to show changes
            if messagebox.askyesno("Update Display", "Redo successful! Extract updated session log?"):
                self.extract_log()
        else:
            self.status_label.config(text="Redo failed", fg="red")
            self.editor_status.config(text=f"✗ {message}", fg="red")
            messagebox.showerror("Redo Failed", message)

    def run(self):
        """Run the GUI."""
        self.window.mainloop()


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
