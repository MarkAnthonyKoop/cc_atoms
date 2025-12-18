#!/usr/bin/env python3
"""
Claude Code Analytics Dashboard
An interactive terminal dashboard for exploring Claude Code usage patterns.
"""

import curses
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sys


@dataclass
class SessionData:
    """Aggregated session data for dashboard."""
    total_sessions: int = 0
    total_messages: int = 0
    total_tool_uses: int = 0
    total_errors: int = 0
    tool_frequency: Counter = field(default_factory=Counter)
    file_patterns: Counter = field(default_factory=Counter)
    command_patterns: Counter = field(default_factory=Counter)
    hourly_activity: Counter = field(default_factory=Counter)
    daily_activity: Counter = field(default_factory=Counter)
    recent_sessions: List[Dict] = field(default_factory=list)
    projects: Counter = field(default_factory=Counter)


class DashboardAnalyzer:
    """Fast analyzer for dashboard updates."""

    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self.data = SessionData()
        self.last_scan = None

    def parse_timestamp(self, ts: str) -> Optional[datetime]:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00').replace('+00:00', ''))
        except:
            return None

    def scan_sessions(self, max_files: int = 500) -> SessionData:
        """Scan session files and build analytics."""
        self.data = SessionData()
        files_scanned = 0

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name.split('-')[-1][:20] if '-' in project_dir.name else project_dir.name[:20]

            for session_file in sorted(project_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
                if files_scanned >= max_files:
                    break

                try:
                    self._process_session(session_file, project_name)
                    files_scanned += 1
                except Exception:
                    continue

        self.last_scan = datetime.now()
        return self.data

    def _process_session(self, path: Path, project_name: str):
        """Process a single session file."""
        session_tools = 0
        session_messages = 0
        session_errors = 0
        first_ts = None
        last_ts = None

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get('type', '')
                ts = self.parse_timestamp(entry.get('timestamp', ''))

                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                if entry_type == 'user':
                    session_messages += 1
                    msg = entry.get('message', {})
                    content = msg.get('content', [])

                    # Check for tool results with errors
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_result':
                                if block.get('is_error'):
                                    session_errors += 1

                elif entry_type == 'assistant':
                    session_messages += 1
                    msg = entry.get('message', {})
                    content = msg.get('content', [])

                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                session_tools += 1
                                tool_name = block.get('name', 'unknown')
                                self.data.tool_frequency[tool_name] += 1

                                tool_input = block.get('input', {})

                                # Track file types
                                if tool_name in ('Read', 'Write', 'Edit'):
                                    file_path = tool_input.get('file_path', '')
                                    if file_path:
                                        ext = Path(file_path).suffix or '(no ext)'
                                        self.data.file_patterns[ext] += 1

                                # Track commands
                                elif tool_name == 'Bash':
                                    cmd = tool_input.get('command', '')
                                    if cmd:
                                        base_cmd = cmd.split()[0] if cmd.split() else ''
                                        self.data.command_patterns[base_cmd] += 1

        # Update aggregates
        if session_messages > 0:
            self.data.total_sessions += 1
            self.data.total_messages += session_messages
            self.data.total_tool_uses += session_tools
            self.data.total_errors += session_errors
            self.data.projects[project_name] += 1

            if first_ts:
                self.data.hourly_activity[first_ts.hour] += 1
                self.data.daily_activity[first_ts.strftime('%a')] += 1

                # Track recent sessions
                if len(self.data.recent_sessions) < 10:
                    self.data.recent_sessions.append({
                        'time': first_ts,
                        'project': project_name,
                        'messages': session_messages,
                        'tools': session_tools,
                    })


class Dashboard:
    """Interactive terminal dashboard."""

    def __init__(self, analyzer: DashboardAnalyzer):
        self.analyzer = analyzer
        self.current_view = 'overview'
        self.views = ['overview', 'tools', 'files', 'commands', 'activity', 'projects']
        self.view_index = 0
        self.running = True

    def draw_box(self, win, y: int, x: int, h: int, w: int, title: str = ""):
        """Draw a box with optional title."""
        # Draw corners
        win.addch(y, x, curses.ACS_ULCORNER)
        win.addch(y, x + w - 1, curses.ACS_URCORNER)
        win.addch(y + h - 1, x, curses.ACS_LLCORNER)
        win.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)

        # Draw horizontal lines
        for i in range(1, w - 1):
            win.addch(y, x + i, curses.ACS_HLINE)
            win.addch(y + h - 1, x + i, curses.ACS_HLINE)

        # Draw vertical lines
        for i in range(1, h - 1):
            win.addch(y + i, x, curses.ACS_VLINE)
            win.addch(y + i, x + w - 1, curses.ACS_VLINE)

        # Draw title
        if title:
            win.addstr(y, x + 2, f" {title} ", curses.A_BOLD)

    def draw_bar(self, win, y: int, x: int, value: int, max_val: int, width: int, color: int = 0):
        """Draw a horizontal bar."""
        if max_val == 0:
            return
        bar_len = int((value / max_val) * width)
        bar = "█" * bar_len + "░" * (width - bar_len)
        try:
            win.addstr(y, x, bar[:width], curses.color_pair(color))
        except curses.error:
            pass

    def draw_header(self, win, width: int):
        """Draw the header."""
        title = "⚡ CLAUDE CODE ANALYTICS DASHBOARD ⚡"
        win.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(1))

        # Navigation hints
        nav = "← → Navigate Views | q Quit | r Refresh"
        win.addstr(1, (width - len(nav)) // 2, nav, curses.color_pair(2))

        # Current view indicator
        view_line = ""
        for i, view in enumerate(self.views):
            if i == self.view_index:
                view_line += f" [{view.upper()}] "
            else:
                view_line += f"  {view}  "
        win.addstr(2, (width - len(view_line)) // 2, view_line, curses.A_DIM)

    def draw_overview(self, win, height: int, width: int, data: SessionData):
        """Draw overview panel."""
        y_start = 4

        # Stats box
        self.draw_box(win, y_start, 2, 8, width // 2 - 2, "📊 STATS")
        stats = [
            f"Sessions:     {data.total_sessions:,}",
            f"Messages:     {data.total_messages:,}",
            f"Tool Uses:    {data.total_tool_uses:,}",
            f"Errors:       {data.total_errors:,}",
            f"Error Rate:   {data.total_errors / max(data.total_tool_uses, 1) * 100:.1f}%",
            f"Tools/Session: {data.total_tool_uses / max(data.total_sessions, 1):.1f}",
        ]
        for i, stat in enumerate(stats):
            try:
                win.addstr(y_start + 1 + i, 4, stat)
            except curses.error:
                pass

        # Top tools box
        self.draw_box(win, y_start, width // 2 + 1, 8, width // 2 - 3, "🔧 TOP TOOLS")
        top_tools = data.tool_frequency.most_common(6)
        max_tool = top_tools[0][1] if top_tools else 1
        for i, (tool, count) in enumerate(top_tools):
            try:
                win.addstr(y_start + 1 + i, width // 2 + 3, f"{tool[:12]:12} {count:5}")
                self.draw_bar(win, y_start + 1 + i, width // 2 + 22, count, max_tool, 15, 3)
            except curses.error:
                pass

        # Activity chart
        y_start += 9
        self.draw_box(win, y_start, 2, 10, width - 4, "⏰ HOURLY ACTIVITY")
        hourly = data.hourly_activity
        max_hour = max(hourly.values()) if hourly else 1

        # Draw hour labels and bars
        for hour in range(24):
            x_pos = 4 + (hour * 3)
            if x_pos + 2 < width - 4:
                count = hourly.get(hour, 0)
                bar_height = int((count / max_hour) * 6) if max_hour > 0 else 0

                # Draw vertical bar
                for h in range(bar_height):
                    try:
                        win.addstr(y_start + 7 - h, x_pos, "█", curses.color_pair(4))
                    except curses.error:
                        pass

                # Draw hour label
                try:
                    win.addstr(y_start + 8, x_pos, f"{hour:02}", curses.A_DIM)
                except curses.error:
                    pass

        # Recent sessions
        y_start += 11
        if y_start + 8 < height:
            self.draw_box(win, y_start, 2, min(8, height - y_start - 1), width - 4, "🕐 RECENT SESSIONS")
            for i, session in enumerate(data.recent_sessions[:5]):
                try:
                    line = f"{session['time'].strftime('%m/%d %H:%M')}  {session['project'][:15]:15}  {session['messages']:3} msgs  {session['tools']:3} tools"
                    win.addstr(y_start + 1 + i, 4, line[:width - 8])
                except curses.error:
                    pass

    def draw_tools_view(self, win, height: int, width: int, data: SessionData):
        """Draw detailed tools view."""
        y_start = 4
        self.draw_box(win, y_start, 2, height - 6, width - 4, "🔧 TOOL USAGE BREAKDOWN")

        top_tools = data.tool_frequency.most_common(20)
        max_tool = top_tools[0][1] if top_tools else 1
        total = sum(data.tool_frequency.values())

        for i, (tool, count) in enumerate(top_tools):
            if y_start + 2 + i >= height - 4:
                break
            pct = (count / total * 100) if total > 0 else 0
            try:
                win.addstr(y_start + 1 + i, 4, f"{tool:20} {count:6} ({pct:5.1f}%)")
                self.draw_bar(win, y_start + 1 + i, 42, count, max_tool, width - 48, 3)
            except curses.error:
                pass

    def draw_files_view(self, win, height: int, width: int, data: SessionData):
        """Draw file types view."""
        y_start = 4
        self.draw_box(win, y_start, 2, height - 6, width - 4, "📁 FILE TYPES ACCESSED")

        top_files = data.file_patterns.most_common(20)
        max_file = top_files[0][1] if top_files else 1
        total = sum(data.file_patterns.values())

        for i, (ext, count) in enumerate(top_files):
            if y_start + 2 + i >= height - 4:
                break
            pct = (count / total * 100) if total > 0 else 0
            try:
                win.addstr(y_start + 1 + i, 4, f"{ext:20} {count:6} ({pct:5.1f}%)")
                self.draw_bar(win, y_start + 1 + i, 42, count, max_file, width - 48, 4)
            except curses.error:
                pass

    def draw_commands_view(self, win, height: int, width: int, data: SessionData):
        """Draw commands view."""
        y_start = 4
        self.draw_box(win, y_start, 2, height - 6, width - 4, "💻 BASH COMMANDS")

        top_cmds = data.command_patterns.most_common(20)
        max_cmd = top_cmds[0][1] if top_cmds else 1

        for i, (cmd, count) in enumerate(top_cmds):
            if y_start + 2 + i >= height - 4:
                break
            try:
                win.addstr(y_start + 1 + i, 4, f"{cmd:20} {count:6}")
                self.draw_bar(win, y_start + 1 + i, 35, count, max_cmd, width - 42, 5)
            except curses.error:
                pass

    def draw_activity_view(self, win, height: int, width: int, data: SessionData):
        """Draw activity patterns view."""
        y_start = 4

        # Daily activity
        self.draw_box(win, y_start, 2, 10, width - 4, "📅 DAILY ACTIVITY")
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        max_day = max(data.daily_activity.values()) if data.daily_activity else 1

        for i, day in enumerate(days):
            count = data.daily_activity.get(day, 0)
            try:
                win.addstr(y_start + 1 + i, 4, f"{day}  {count:4}")
                self.draw_bar(win, y_start + 1 + i, 14, count, max_day, width - 22, 6)
            except curses.error:
                pass

        # Hourly heatmap
        y_start += 11
        self.draw_box(win, y_start, 2, height - y_start - 2, width - 4, "⏰ 24-HOUR HEATMAP")

        max_hour = max(data.hourly_activity.values()) if data.hourly_activity else 1

        for hour in range(24):
            count = data.hourly_activity.get(hour, 0)
            intensity = int((count / max_hour) * 4) if max_hour > 0 else 0
            chars = [' ', '░', '▒', '▓', '█']
            char = chars[min(intensity, 4)]

            try:
                win.addstr(y_start + 2, 4 + hour * 3, f"{hour:02}", curses.A_DIM)
                win.addstr(y_start + 3, 4 + hour * 3, char * 2, curses.color_pair(4))
                win.addstr(y_start + 4, 4 + hour * 3, f"{count:2}", curses.A_DIM if count < max_hour // 2 else curses.A_BOLD)
            except curses.error:
                pass

    def draw_projects_view(self, win, height: int, width: int, data: SessionData):
        """Draw projects breakdown view."""
        y_start = 4
        self.draw_box(win, y_start, 2, height - 6, width - 4, "📂 PROJECTS")

        top_projects = data.projects.most_common(20)
        max_proj = top_projects[0][1] if top_projects else 1

        for i, (proj, count) in enumerate(top_projects):
            if y_start + 2 + i >= height - 4:
                break
            try:
                win.addstr(y_start + 1 + i, 4, f"{proj:25} {count:4} sessions")
                self.draw_bar(win, y_start + 1 + i, 42, count, max_proj, width - 48, 2)
            except curses.error:
                pass

    def draw_footer(self, win, height: int, width: int):
        """Draw footer with last update time."""
        if self.analyzer.last_scan:
            footer = f"Last updated: {self.analyzer.last_scan.strftime('%H:%M:%S')} | Scanning {self.analyzer.data.total_sessions} sessions"
        else:
            footer = "Scanning..."
        try:
            win.addstr(height - 1, 2, footer, curses.A_DIM)
        except curses.error:
            pass

    def run(self, stdscr):
        """Main dashboard loop."""
        # Setup colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)

        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(100)  # Refresh every 100ms

        # Initial scan
        self.analyzer.scan_sessions()

        last_refresh = time.time()
        refresh_interval = 30  # Refresh data every 30 seconds

        while self.running:
            height, width = stdscr.getmaxyx()
            stdscr.clear()

            # Auto-refresh data
            if time.time() - last_refresh > refresh_interval:
                self.analyzer.scan_sessions()
                last_refresh = time.time()

            # Draw components
            self.draw_header(stdscr, width)

            data = self.analyzer.data
            view = self.views[self.view_index]

            if view == 'overview':
                self.draw_overview(stdscr, height, width, data)
            elif view == 'tools':
                self.draw_tools_view(stdscr, height, width, data)
            elif view == 'files':
                self.draw_files_view(stdscr, height, width, data)
            elif view == 'commands':
                self.draw_commands_view(stdscr, height, width, data)
            elif view == 'activity':
                self.draw_activity_view(stdscr, height, width, data)
            elif view == 'projects':
                self.draw_projects_view(stdscr, height, width, data)

            self.draw_footer(stdscr, height, width)

            stdscr.refresh()

            # Handle input
            try:
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    self.running = False
                elif key == curses.KEY_RIGHT or key == ord('l'):
                    self.view_index = (self.view_index + 1) % len(self.views)
                elif key == curses.KEY_LEFT or key == ord('h'):
                    self.view_index = (self.view_index - 1) % len(self.views)
                elif key == ord('r') or key == ord('R'):
                    self.analyzer.scan_sessions()
                    last_refresh = time.time()
            except:
                pass


def main():
    """Launch the dashboard."""
    projects_dir = Path.home() / ".claude" / "projects"

    if len(sys.argv) > 1:
        projects_dir = Path(sys.argv[1])

    if not projects_dir.exists():
        print(f"Error: {projects_dir} does not exist")
        sys.exit(1)

    print("🚀 Launching Claude Code Analytics Dashboard...")
    print("   Press 'q' to quit, ← → to navigate views, 'r' to refresh")
    time.sleep(1)

    analyzer = DashboardAnalyzer(projects_dir)
    dashboard = Dashboard(analyzer)

    try:
        curses.wrapper(dashboard.run)
    except KeyboardInterrupt:
        pass

    print("\n👋 Dashboard closed. Happy coding!")


if __name__ == "__main__":
    main()
