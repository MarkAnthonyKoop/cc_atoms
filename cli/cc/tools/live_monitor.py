#!/usr/bin/env python3
"""
Claude Code Live Monitor
Watch Claude Code sessions in real-time with live updates.
"""

import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent


# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'


@dataclass
class LiveEvent:
    """A live event from a session."""
    timestamp: datetime
    session_id: str
    project: str
    event_type: str  # user, assistant, tool_use, tool_result
    content: str
    tool_name: Optional[str] = None
    is_error: bool = False


class SessionWatcher(FileSystemEventHandler):
    """Watch for changes in session files."""

    def __init__(self, callback):
        self.callback = callback
        self.file_positions: Dict[str, int] = {}
        self.known_files: Set[str] = set()

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.jsonl'):
            return
        self._process_file(event.src_path)

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.jsonl'):
            return
        self._process_file(event.src_path)

    def _process_file(self, filepath: str):
        """Process new lines in a session file."""
        try:
            # Get last known position
            last_pos = self.file_positions.get(filepath, 0)

            with open(filepath, 'r', encoding='utf-8') as f:
                # If new file, skip to near end for initial read
                if filepath not in self.known_files:
                    f.seek(0, 2)  # Go to end
                    size = f.tell()
                    # Read last 10KB for context
                    start_pos = max(0, size - 10240)
                    f.seek(start_pos)
                    if start_pos > 0:
                        f.readline()  # Skip partial line
                    self.known_files.add(filepath)
                else:
                    f.seek(last_pos)

                new_lines = []
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            new_lines.append(entry)
                        except json.JSONDecodeError:
                            continue

                # Update position
                self.file_positions[filepath] = f.tell()

                # Process new entries
                for entry in new_lines:
                    self.callback(filepath, entry)

        except Exception as e:
            pass  # Silently handle errors


class LiveMonitor:
    """Real-time Claude Code session monitor."""

    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self.events: deque = deque(maxlen=100)
        self.running = True
        self.stats = {
            'sessions_active': set(),
            'total_messages': 0,
            'total_tools': 0,
            'errors': 0,
        }
        self.observer = None

    def parse_timestamp(self, ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00').replace('+00:00', ''))
        except:
            return datetime.now()

    def extract_project_name(self, filepath: str) -> str:
        """Extract project name from filepath."""
        parts = Path(filepath).parent.name.split('-')
        if len(parts) > 1:
            return parts[-1][:20]
        return "unknown"

    def process_entry(self, filepath: str, entry: Dict[str, Any]):
        """Process a session entry and create events."""
        entry_type = entry.get('type', '')
        session_id = entry.get('sessionId', '')[:8]
        project = self.extract_project_name(filepath)
        timestamp = self.parse_timestamp(entry.get('timestamp', ''))

        self.stats['sessions_active'].add(session_id)

        if entry_type == 'user':
            self.stats['total_messages'] += 1
            msg = entry.get('message', {})
            content = msg.get('content', '')

            if isinstance(content, str) and content:
                # User message
                event = LiveEvent(
                    timestamp=timestamp,
                    session_id=session_id,
                    project=project,
                    event_type='user',
                    content=content[:100] + ('...' if len(content) > 100 else ''),
                )
                self.events.append(event)
                self.print_event(event)

            elif isinstance(content, list):
                # Check for tool results
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        is_error = block.get('is_error', False)
                        result_content = str(block.get('content', ''))[:50]

                        if is_error:
                            self.stats['errors'] += 1

                        event = LiveEvent(
                            timestamp=timestamp,
                            session_id=session_id,
                            project=project,
                            event_type='tool_result',
                            content=result_content,
                            is_error=is_error,
                        )
                        self.events.append(event)
                        self.print_event(event)

        elif entry_type == 'assistant':
            self.stats['total_messages'] += 1
            msg = entry.get('message', {})
            content = msg.get('content', [])

            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get('type', '')

                        if block_type == 'text':
                            text = block.get('text', '')[:100]
                            if text:
                                event = LiveEvent(
                                    timestamp=timestamp,
                                    session_id=session_id,
                                    project=project,
                                    event_type='assistant',
                                    content=text + ('...' if len(block.get('text', '')) > 100 else ''),
                                )
                                self.events.append(event)
                                self.print_event(event)

                        elif block_type == 'tool_use':
                            self.stats['total_tools'] += 1
                            tool_name = block.get('name', 'unknown')
                            tool_input = block.get('input', {})

                            # Format tool input nicely
                            if tool_name in ('Read', 'Write', 'Edit'):
                                detail = tool_input.get('file_path', '')[-40:]
                            elif tool_name == 'Bash':
                                detail = tool_input.get('command', '')[:40]
                            elif tool_name == 'Grep':
                                detail = tool_input.get('pattern', '')[:30]
                            elif tool_name == 'Glob':
                                detail = tool_input.get('pattern', '')[:30]
                            else:
                                detail = str(tool_input)[:40]

                            event = LiveEvent(
                                timestamp=timestamp,
                                session_id=session_id,
                                project=project,
                                event_type='tool_use',
                                content=detail,
                                tool_name=tool_name,
                            )
                            self.events.append(event)
                            self.print_event(event)

    def print_event(self, event: LiveEvent):
        """Print an event to the terminal."""
        c = Colors

        # Time
        time_str = event.timestamp.strftime('%H:%M:%S')

        # Session/Project badge
        badge = f"[{event.project[:10]}]"

        # Format based on event type
        if event.event_type == 'user':
            icon = "👤"
            color = c.CYAN
            label = "USER"
        elif event.event_type == 'assistant':
            icon = "🤖"
            color = c.GREEN
            label = "ASST"
        elif event.event_type == 'tool_use':
            icon = "🔧"
            color = c.YELLOW
            label = event.tool_name or "TOOL"
        elif event.event_type == 'tool_result':
            if event.is_error:
                icon = "❌"
                color = c.RED
                label = "ERR"
            else:
                icon = "✅"
                color = c.DIM
                label = "OK"
        else:
            icon = "•"
            color = c.WHITE
            label = "???"

        # Print the line
        print(f"{c.DIM}{time_str}{c.RESET} {icon} {color}{label:8}{c.RESET} {c.BLUE}{badge:12}{c.RESET} {event.content}")

    def print_header(self):
        """Print the monitor header."""
        c = Colors
        print(f"\n{c.BG_BLUE}{c.WHITE}{c.BOLD} ⚡ CLAUDE CODE LIVE MONITOR ⚡ {c.RESET}")
        print(f"{c.DIM}Watching: {self.projects_dir}{c.RESET}")
        print(f"{c.DIM}Press Ctrl+C to stop{c.RESET}")
        print(f"{c.DIM}{'─' * 70}{c.RESET}\n")

    def print_stats(self):
        """Print current stats."""
        c = Colors
        print(f"\n{c.DIM}{'─' * 70}{c.RESET}")
        print(f"{c.BOLD}Stats:{c.RESET} Sessions: {len(self.stats['sessions_active'])} | "
              f"Messages: {self.stats['total_messages']} | "
              f"Tools: {self.stats['total_tools']} | "
              f"Errors: {c.RED if self.stats['errors'] > 0 else ''}{self.stats['errors']}{c.RESET}")

    def run(self):
        """Start monitoring."""
        self.print_header()

        # Set up file watcher
        watcher = SessionWatcher(self.process_entry)
        self.observer = Observer()

        # Watch all project directories
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                self.observer.schedule(watcher, str(project_dir), recursive=False)

        self.observer.start()

        print(f"{Colors.GREEN}▶ Monitoring started... Waiting for activity...{Colors.RESET}\n")

        try:
            last_stats = time.time()
            while self.running:
                time.sleep(0.5)

                # Print stats every 30 seconds
                if time.time() - last_stats > 30:
                    self.print_stats()
                    last_stats = time.time()

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⏹ Stopping monitor...{Colors.RESET}")
        finally:
            self.observer.stop()
            self.observer.join()
            self.print_stats()
            print(f"\n{Colors.GREEN}👋 Monitor stopped. Happy coding!{Colors.RESET}")


def main():
    """Launch the live monitor."""
    projects_dir = Path.home() / ".claude" / "projects"

    if len(sys.argv) > 1:
        projects_dir = Path(sys.argv[1])

    if not projects_dir.exists():
        print(f"Error: {projects_dir} does not exist")
        sys.exit(1)

    # Check for watchdog
    try:
        from watchdog.observers import Observer
    except ImportError:
        print("Installing watchdog...")
        os.system(f"{sys.executable} -m pip install watchdog -q")
        from watchdog.observers import Observer

    monitor = LiveMonitor(projects_dir)
    monitor.run()


if __name__ == "__main__":
    main()
