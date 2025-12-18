#!/usr/bin/env python3
"""
Conversation Analyzer - Mine insights from Claude Code session data.

Analyzes JSONL session files to extract patterns, statistics, and insights
about tool usage, conversation patterns, common tasks, and productivity metrics.
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SessionStats:
    """Statistics for a single session."""
    session_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tool_uses: int = 0
    tool_results: int = 0
    tools_used: Counter = field(default_factory=Counter)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    files_edited: List[str] = field(default_factory=list)
    bash_commands: List[str] = field(default_factory=list)
    errors: int = 0

    @property
    def duration_minutes(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


@dataclass
class AggregateStats:
    """Aggregate statistics across all sessions."""
    total_sessions: int = 0
    total_messages: int = 0
    total_tool_uses: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    tool_frequency: Counter = field(default_factory=Counter)
    file_patterns: Counter = field(default_factory=Counter)
    command_patterns: Counter = field(default_factory=Counter)
    hourly_activity: Counter = field(default_factory=Counter)
    daily_activity: Counter = field(default_factory=Counter)
    session_durations: List[float] = field(default_factory=list)
    common_prompts: List[str] = field(default_factory=list)


class ConversationAnalyzer:
    """Analyze Claude Code conversation session files."""

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.sessions: List[SessionStats] = []
        self.aggregate = AggregateStats()

    def parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse various timestamp formats."""
        if not ts:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
        try:
            # Try common formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        except (ValueError, TypeError):
            pass
        return None

    def analyze_session(self, session_path: Path) -> Optional[SessionStats]:
        """Analyze a single session file."""
        try:
            entries = []
            with open(session_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            if not entries:
                return None

            # Extract session ID from first entry or filename
            session_id = entries[0].get('sessionId', session_path.stem)
            stats = SessionStats(session_id=session_id)

            timestamps = []

            for entry in entries:
                entry_type = entry.get('type', '')
                ts = self.parse_timestamp(entry.get('timestamp', ''))
                if ts:
                    timestamps.append(ts)

                if entry_type == 'user':
                    stats.user_messages += 1
                    stats.message_count += 1
                    # Extract user prompt for analysis
                    msg = entry.get('message', {})
                    content = msg.get('content', '')
                    if isinstance(content, str) and len(content) > 10:
                        self.aggregate.common_prompts.append(content[:200])

                    # Check for tool_result in user messages (Claude format)
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_result':
                                stats.tool_results += 1
                                is_error = block.get('is_error', False)
                                if is_error:
                                    stats.errors += 1
                                # Check content for error indicators
                                result_content = block.get('content', '')
                                if isinstance(result_content, str):
                                    if 'error' in result_content.lower()[:100] or 'Error:' in result_content[:100]:
                                        stats.errors += 1

                elif entry_type == 'assistant':
                    stats.assistant_messages += 1
                    stats.message_count += 1
                    usage = entry.get('usage', {})
                    stats.total_input_tokens += usage.get('inputTokens', 0) or usage.get('input_tokens', 0)
                    stats.total_output_tokens += usage.get('outputTokens', 0) or usage.get('output_tokens', 0)

                    # Parse tool uses from content blocks
                    msg = entry.get('message', {})
                    content = msg.get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                stats.tool_uses += 1
                                tool_name = block.get('name', 'unknown')
                                stats.tools_used[tool_name] += 1
                                tool_input = block.get('input', {})

                                # Track file operations
                                if tool_name in ('Read', 'read'):
                                    file_path = tool_input.get('file_path', '')
                                    if file_path:
                                        stats.files_read.append(file_path)
                                        ext = Path(file_path).suffix
                                        self.aggregate.file_patterns[ext] += 1

                                elif tool_name in ('Write', 'write'):
                                    file_path = tool_input.get('file_path', '')
                                    if file_path:
                                        stats.files_written.append(file_path)
                                        ext = Path(file_path).suffix
                                        self.aggregate.file_patterns[ext] += 1

                                elif tool_name in ('Edit', 'edit'):
                                    file_path = tool_input.get('file_path', '')
                                    if file_path:
                                        stats.files_edited.append(file_path)
                                        ext = Path(file_path).suffix
                                        self.aggregate.file_patterns[ext] += 1

                                elif tool_name in ('Bash', 'bash'):
                                    command = tool_input.get('command', '')
                                    if command:
                                        stats.bash_commands.append(command)
                                        # Extract base command
                                        base_cmd = command.split()[0] if command.split() else ''
                                        self.aggregate.command_patterns[base_cmd] += 1

                                elif tool_name == 'Task':
                                    # Track Task agent usage
                                    agent_type = tool_input.get('subagent_type', 'general')
                                    self.aggregate.command_patterns[f'Task:{agent_type}'] += 1

                elif entry_type == 'tool_use':
                    stats.tool_uses += 1
                    tool_name = entry.get('toolName', 'unknown')
                    stats.tools_used[tool_name] += 1

                    tool_input = entry.get('toolInput', {})

                    # Track file operations
                    if tool_name in ('Read', 'read'):
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            stats.files_read.append(file_path)
                            ext = Path(file_path).suffix
                            self.aggregate.file_patterns[ext] += 1

                    elif tool_name in ('Write', 'write'):
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            stats.files_written.append(file_path)

                    elif tool_name in ('Edit', 'edit'):
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            stats.files_edited.append(file_path)

                    elif tool_name in ('Bash', 'bash'):
                        command = tool_input.get('command', '')
                        if command:
                            stats.bash_commands.append(command)
                            # Extract base command
                            base_cmd = command.split()[0] if command.split() else ''
                            self.aggregate.command_patterns[base_cmd] += 1

                elif entry_type == 'tool_result':
                    stats.tool_results += 1
                    if entry.get('isError', False):
                        stats.errors += 1

            # Set time bounds
            if timestamps:
                stats.start_time = min(timestamps)
                stats.end_time = max(timestamps)

                # Track activity patterns
                self.aggregate.hourly_activity[stats.start_time.hour] += 1
                self.aggregate.daily_activity[stats.start_time.strftime('%A')] += 1

            return stats

        except Exception as e:
            print(f"Error analyzing {session_path}: {e}")
            return None

    def analyze_all(self, pattern: str = "*.jsonl") -> 'ConversationAnalyzer':
        """Analyze all session files matching pattern."""
        session_files = list(self.sessions_dir.glob(pattern))

        for session_path in session_files:
            stats = self.analyze_session(session_path)
            if stats:
                self.sessions.append(stats)

                # Update aggregate stats
                self.aggregate.total_sessions += 1
                self.aggregate.total_messages += stats.message_count
                self.aggregate.total_tool_uses += stats.tool_uses
                self.aggregate.total_tokens += stats.total_tokens
                self.aggregate.total_errors += stats.errors
                self.aggregate.tool_frequency.update(stats.tools_used)

                if stats.duration_minutes > 0:
                    self.aggregate.session_durations.append(stats.duration_minutes)

        return self

    def get_top_tools(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently used tools."""
        return self.aggregate.tool_frequency.most_common(n)

    def get_file_type_distribution(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get distribution of file types accessed."""
        return self.aggregate.file_patterns.most_common(n)

    def get_top_commands(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently used bash commands."""
        return self.aggregate.command_patterns.most_common(n)

    def get_activity_by_hour(self) -> Dict[int, int]:
        """Get activity distribution by hour of day."""
        return dict(sorted(self.aggregate.hourly_activity.items()))

    def get_activity_by_day(self) -> Dict[str, int]:
        """Get activity distribution by day of week."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return {day: self.aggregate.daily_activity.get(day, 0) for day in days}

    def get_productivity_metrics(self) -> Dict[str, Any]:
        """Calculate productivity metrics."""
        durations = self.aggregate.session_durations

        return {
            'total_sessions': self.aggregate.total_sessions,
            'total_messages': self.aggregate.total_messages,
            'total_tool_uses': self.aggregate.total_tool_uses,
            'total_tokens': self.aggregate.total_tokens,
            'avg_session_duration_min': sum(durations) / len(durations) if durations else 0,
            'max_session_duration_min': max(durations) if durations else 0,
            'tools_per_session': self.aggregate.total_tool_uses / self.aggregate.total_sessions if self.aggregate.total_sessions else 0,
            'error_rate': self.aggregate.total_errors / self.aggregate.total_tool_uses if self.aggregate.total_tool_uses else 0,
        }

    def generate_report(self) -> str:
        """Generate a comprehensive analysis report."""
        metrics = self.get_productivity_metrics()

        report = []
        report.append("=" * 60)
        report.append("    CLAUDE CODE SESSION ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")

        # Overview
        report.append("📊 OVERVIEW")
        report.append("-" * 40)
        report.append(f"  Sessions analyzed:     {metrics['total_sessions']:,}")
        report.append(f"  Total messages:        {metrics['total_messages']:,}")
        report.append(f"  Total tool uses:       {metrics['total_tool_uses']:,}")
        report.append(f"  Total tokens:          {metrics['total_tokens']:,}")
        report.append(f"  Avg session duration:  {metrics['avg_session_duration_min']:.1f} min")
        report.append(f"  Max session duration:  {metrics['max_session_duration_min']:.1f} min")
        report.append(f"  Tools per session:     {metrics['tools_per_session']:.1f}")
        report.append(f"  Error rate:            {metrics['error_rate']*100:.1f}%")
        report.append("")

        # Top Tools
        report.append("🔧 TOP TOOLS USED")
        report.append("-" * 40)
        for tool, count in self.get_top_tools(10):
            bar = "█" * min(count // 10, 30)
            report.append(f"  {tool:20} {count:5}  {bar}")
        report.append("")

        # File Types
        report.append("📁 FILE TYPES ACCESSED")
        report.append("-" * 40)
        for ext, count in self.get_file_type_distribution(10):
            ext_display = ext if ext else "(no ext)"
            report.append(f"  {ext_display:20} {count:5}")
        report.append("")

        # Top Commands
        report.append("💻 TOP BASH COMMANDS")
        report.append("-" * 40)
        for cmd, count in self.get_top_commands(10):
            report.append(f"  {cmd:20} {count:5}")
        report.append("")

        # Activity by Hour
        report.append("⏰ ACTIVITY BY HOUR")
        report.append("-" * 40)
        hourly = self.get_activity_by_hour()
        max_hour_count = max(hourly.values()) if hourly else 1
        for hour, count in hourly.items():
            bar_len = int(count / max_hour_count * 20)
            bar = "█" * bar_len
            report.append(f"  {hour:02d}:00  {bar:20} {count}")
        report.append("")

        # Activity by Day
        report.append("📅 ACTIVITY BY DAY")
        report.append("-" * 40)
        daily = self.get_activity_by_day()
        max_day_count = max(daily.values()) if daily and any(daily.values()) else 1
        for day, count in daily.items():
            bar_len = int(count / max_day_count * 20) if max_day_count > 0 else 0
            bar = "█" * bar_len
            report.append(f"  {day:10} {bar:20} {count}")
        report.append("")

        # Interesting insights
        report.append("💡 INSIGHTS")
        report.append("-" * 40)
        if self.aggregate.total_tool_uses > 0:
            bash_pct = (self.aggregate.tool_frequency.get('Bash', 0) / self.aggregate.total_tool_uses) * 100
            read_pct = (self.aggregate.tool_frequency.get('Read', 0) / self.aggregate.total_tool_uses) * 100
            edit_pct = (self.aggregate.tool_frequency.get('Edit', 0) / self.aggregate.total_tool_uses) * 100

            report.append(f"  • {bash_pct:.0f}% of tool uses are Bash commands")
            report.append(f"  • Read/Edit ratio: {self.aggregate.tool_frequency.get('Read', 0) / max(self.aggregate.tool_frequency.get('Edit', 1), 1):.1f}:1")
            report.append(f"  • Most active hour: {max(self.aggregate.hourly_activity.items(), key=lambda x: x[1])[0]}:00" if self.aggregate.hourly_activity else "")
            report.append(f"  • Most active day: {max(self.aggregate.daily_activity.items(), key=lambda x: x[1])[0]}" if self.aggregate.daily_activity else "")

            # Python dominance
            py_files = self.aggregate.file_patterns.get('.py', 0)
            total_files = sum(self.aggregate.file_patterns.values())
            if total_files > 0:
                report.append(f"  • {py_files / total_files * 100:.0f}% of files accessed are Python")

        report.append("")
        report.append("=" * 60)
        return "\n".join(report)


def main():
    """Run analysis on Claude projects directory."""
    import sys

    # Default to Claude projects directory
    projects_dir = Path.home() / ".claude" / "projects"

    if len(sys.argv) > 1:
        target = sys.argv[1]
        if Path(target).is_dir():
            projects_dir = Path(target)

    print(f"Analyzing sessions in: {projects_dir}")
    print("This may take a moment...")
    print()

    # Create master aggregate analyzer
    master = ConversationAnalyzer(projects_dir)

    # Analyze all sessions across all projects
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            analyzer = ConversationAnalyzer(project_dir)
            analyzer.analyze_all()

            # Merge this analyzer's results into master
            master.sessions.extend(analyzer.sessions)

            # Merge aggregate stats
            master.aggregate.total_sessions += analyzer.aggregate.total_sessions
            master.aggregate.total_messages += analyzer.aggregate.total_messages
            master.aggregate.total_tool_uses += analyzer.aggregate.total_tool_uses
            master.aggregate.total_tokens += analyzer.aggregate.total_tokens
            master.aggregate.total_errors += analyzer.aggregate.total_errors
            master.aggregate.tool_frequency.update(analyzer.aggregate.tool_frequency)
            master.aggregate.file_patterns.update(analyzer.aggregate.file_patterns)
            master.aggregate.command_patterns.update(analyzer.aggregate.command_patterns)
            master.aggregate.hourly_activity.update(analyzer.aggregate.hourly_activity)
            master.aggregate.daily_activity.update(analyzer.aggregate.daily_activity)
            master.aggregate.session_durations.extend(analyzer.aggregate.session_durations)
            master.aggregate.common_prompts.extend(analyzer.aggregate.common_prompts)

    print(master.generate_report())


if __name__ == "__main__":
    main()
