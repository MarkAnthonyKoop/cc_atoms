#!/usr/bin/env python3
"""
Claude Code Productivity Coach
AI-powered insights and recommendations based on your Claude Code usage patterns.
"""

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import math


@dataclass
class ProductivityMetrics:
    """Computed productivity metrics."""
    total_sessions: int = 0
    total_hours: float = 0
    avg_session_length_min: float = 0
    tools_per_session: float = 0
    error_rate: float = 0
    read_edit_ratio: float = 0
    bash_percentage: float = 0
    peak_hour: int = 0
    peak_day: str = ""
    most_used_tool: str = ""
    most_edited_filetype: str = ""
    productivity_score: float = 0
    focus_score: float = 0
    efficiency_score: float = 0


@dataclass
class Insight:
    """A productivity insight."""
    category: str  # efficiency, focus, learning, optimization
    title: str
    description: str
    recommendation: str
    priority: int  # 1-5, 5 being highest
    icon: str


class ProductivityCoach:
    """Analyze patterns and generate productivity insights."""

    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self.tool_frequency: Counter = Counter()
        self.file_patterns: Counter = Counter()
        self.command_patterns: Counter = Counter()
        self.hourly_activity: Counter = Counter()
        self.daily_activity: Counter = Counter()
        self.session_lengths: List[float] = []
        self.error_count: int = 0
        self.total_tool_uses: int = 0
        self.total_sessions: int = 0
        self.total_messages: int = 0

        # Pattern tracking
        self.long_sessions: List[float] = []  # Sessions > 60 min
        self.short_sessions: List[float] = []  # Sessions < 5 min
        self.error_patterns: Counter = Counter()  # Tools that cause errors
        self.project_activity: Counter = Counter()

    def parse_timestamp(self, ts: str) -> Optional[datetime]:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00').replace('+00:00', ''))
        except:
            return None

    def analyze_sessions(self, max_files: int = 1000):
        """Analyze all sessions to build metrics."""
        files_processed = 0

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name.split('-')[-1][:30]

            for session_file in sorted(project_dir.glob("*.jsonl"),
                                      key=lambda x: x.stat().st_mtime,
                                      reverse=True):
                if files_processed >= max_files:
                    break

                try:
                    self._process_session(session_file, project_name)
                    files_processed += 1
                except Exception:
                    continue

    def _process_session(self, path: Path, project_name: str):
        """Process a single session file."""
        timestamps = []
        session_tools = 0
        session_errors = 0
        session_messages = 0

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
                    timestamps.append(ts)

                if entry_type == 'user':
                    session_messages += 1
                    msg = entry.get('message', {})
                    content = msg.get('content', [])

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
                                self.total_tool_uses += 1
                                tool_name = block.get('name', 'unknown')
                                self.tool_frequency[tool_name] += 1

                                tool_input = block.get('input', {})

                                if tool_name in ('Read', 'Write', 'Edit'):
                                    file_path = tool_input.get('file_path', '')
                                    if file_path:
                                        ext = Path(file_path).suffix or '(no ext)'
                                        self.file_patterns[ext] += 1

                                elif tool_name == 'Bash':
                                    cmd = tool_input.get('command', '')
                                    if cmd:
                                        base_cmd = cmd.split()[0] if cmd.split() else ''
                                        self.command_patterns[base_cmd] += 1

        # Calculate session metrics
        if session_messages > 0:
            self.total_sessions += 1
            self.total_messages += session_messages
            self.error_count += session_errors
            self.project_activity[project_name] += 1

            if len(timestamps) >= 2:
                duration = (max(timestamps) - min(timestamps)).total_seconds() / 60
                self.session_lengths.append(duration)

                if duration > 60:
                    self.long_sessions.append(duration)
                elif duration < 5:
                    self.short_sessions.append(duration)

                first_ts = min(timestamps)
                self.hourly_activity[first_ts.hour] += 1
                self.daily_activity[first_ts.strftime('%A')] += 1

    def compute_metrics(self) -> ProductivityMetrics:
        """Compute productivity metrics from raw data."""
        metrics = ProductivityMetrics()

        metrics.total_sessions = self.total_sessions
        metrics.total_hours = sum(self.session_lengths) / 60 if self.session_lengths else 0
        metrics.avg_session_length_min = (sum(self.session_lengths) / len(self.session_lengths)
                                          if self.session_lengths else 0)
        metrics.tools_per_session = (self.total_tool_uses / self.total_sessions
                                     if self.total_sessions > 0 else 0)
        metrics.error_rate = (self.error_count / self.total_tool_uses * 100
                              if self.total_tool_uses > 0 else 0)

        # Read/Edit ratio
        reads = self.tool_frequency.get('Read', 0)
        edits = self.tool_frequency.get('Edit', 0)
        metrics.read_edit_ratio = reads / edits if edits > 0 else reads

        # Bash percentage
        bash = self.tool_frequency.get('Bash', 0)
        metrics.bash_percentage = bash / self.total_tool_uses * 100 if self.total_tool_uses > 0 else 0

        # Peak times
        if self.hourly_activity:
            metrics.peak_hour = max(self.hourly_activity.items(), key=lambda x: x[1])[0]
        if self.daily_activity:
            metrics.peak_day = max(self.daily_activity.items(), key=lambda x: x[1])[0]

        # Most used
        if self.tool_frequency:
            metrics.most_used_tool = self.tool_frequency.most_common(1)[0][0]
        if self.file_patterns:
            metrics.most_edited_filetype = self.file_patterns.most_common(1)[0][0]

        # Compute scores (0-100)
        # Efficiency: based on error rate and tools per session
        efficiency = 100 - (metrics.error_rate * 5)  # Penalize errors
        efficiency = max(0, min(100, efficiency))
        metrics.efficiency_score = efficiency

        # Focus: based on session length distribution
        if self.session_lengths:
            # Optimal session is 20-45 minutes
            optimal_sessions = sum(1 for s in self.session_lengths if 20 <= s <= 45)
            focus = (optimal_sessions / len(self.session_lengths)) * 100
        else:
            focus = 50
        metrics.focus_score = focus

        # Overall productivity score
        metrics.productivity_score = (metrics.efficiency_score * 0.4 +
                                      metrics.focus_score * 0.3 +
                                      min(metrics.tools_per_session * 5, 30))  # Cap tools contribution

        return metrics

    def generate_insights(self, metrics: ProductivityMetrics) -> List[Insight]:
        """Generate actionable insights based on metrics."""
        insights = []

        # Error rate insights
        if metrics.error_rate > 10:
            insights.append(Insight(
                category="efficiency",
                title="High Error Rate Detected",
                description=f"Your error rate is {metrics.error_rate:.1f}%, which is above the optimal threshold.",
                recommendation="Consider reading files before editing, and running commands with --dry-run first.",
                priority=5,
                icon="🔴"
            ))
        elif metrics.error_rate < 5:
            insights.append(Insight(
                category="efficiency",
                title="Excellent Error Rate!",
                description=f"Your error rate is only {metrics.error_rate:.1f}%. Great attention to detail!",
                recommendation="Keep up the careful approach - it's paying off.",
                priority=1,
                icon="🟢"
            ))

        # Session length insights
        if metrics.avg_session_length_min > 120:
            insights.append(Insight(
                category="focus",
                title="Long Sessions Detected",
                description=f"Your average session is {metrics.avg_session_length_min:.0f} minutes.",
                recommendation="Consider breaking tasks into smaller chunks. The Pomodoro technique (25-min sessions) can boost focus.",
                priority=4,
                icon="⏰"
            ))
        elif metrics.avg_session_length_min < 10:
            insights.append(Insight(
                category="focus",
                title="Very Short Sessions",
                description=f"Your average session is only {metrics.avg_session_length_min:.0f} minutes.",
                recommendation="Short sessions might indicate frequent context switching. Try batching similar tasks.",
                priority=3,
                icon="⚡"
            ))

        # Tool usage insights
        if metrics.bash_percentage > 60:
            insights.append(Insight(
                category="optimization",
                title="Heavy Bash Usage",
                description=f"{metrics.bash_percentage:.0f}% of your tool usage is Bash commands.",
                recommendation="Consider using dedicated tools like Read/Edit/Glob for file operations - they're faster and safer.",
                priority=3,
                icon="💻"
            ))

        if metrics.read_edit_ratio > 5:
            insights.append(Insight(
                category="learning",
                title="Code Explorer Mode",
                description=f"You read {metrics.read_edit_ratio:.1f}x more than you edit.",
                recommendation="Great for learning! When ready to make changes, trust your understanding and edit more confidently.",
                priority=2,
                icon="📚"
            ))
        elif metrics.read_edit_ratio < 1:
            insights.append(Insight(
                category="efficiency",
                title="Edit-Heavy Pattern",
                description="You edit more than you read.",
                recommendation="Reading code before editing can prevent errors. Consider using Read tool first for context.",
                priority=4,
                icon="✏️"
            ))

        # Peak time insights
        if metrics.peak_hour in range(0, 6):
            insights.append(Insight(
                category="focus",
                title="Night Owl Detected 🦉",
                description=f"Your peak coding hour is {metrics.peak_hour}:00 AM.",
                recommendation="Late-night coding can be productive but watch for fatigue. Consider shifting some work earlier.",
                priority=2,
                icon="🌙"
            ))
        elif metrics.peak_hour in range(6, 10):
            insights.append(Insight(
                category="focus",
                title="Early Bird! 🐦",
                description=f"Your peak coding hour is {metrics.peak_hour}:00 AM.",
                recommendation="Morning coding is great for complex tasks. Protect this time from meetings!",
                priority=1,
                icon="☀️"
            ))

        # Weekend warrior
        if metrics.peak_day in ('Saturday', 'Sunday'):
            insights.append(Insight(
                category="focus",
                title="Weekend Warrior",
                description=f"Your most active day is {metrics.peak_day}.",
                recommendation="Weekend coding can be productive, but ensure you're getting rest. Consider automating routine tasks.",
                priority=2,
                icon="🏋️"
            ))

        # Productivity score insight
        if metrics.productivity_score >= 80:
            insights.append(Insight(
                category="efficiency",
                title="Power User Status!",
                description=f"Productivity score: {metrics.productivity_score:.0f}/100",
                recommendation="You're using Claude Code effectively! Consider sharing your workflow with others.",
                priority=1,
                icon="🏆"
            ))
        elif metrics.productivity_score < 50:
            insights.append(Insight(
                category="efficiency",
                title="Room for Growth",
                description=f"Productivity score: {metrics.productivity_score:.0f}/100",
                recommendation="Try using TodoWrite to plan tasks, and batch similar operations together.",
                priority=4,
                icon="📈"
            ))

        # Tool-specific recommendations
        if self.tool_frequency.get('TodoWrite', 0) < self.total_sessions * 0.3:
            insights.append(Insight(
                category="optimization",
                title="Use Todo Lists More",
                description="TodoWrite is underutilized in your workflow.",
                recommendation="Todo lists help Claude track progress and ensure nothing is missed. Try them for multi-step tasks!",
                priority=3,
                icon="📝"
            ))

        if self.tool_frequency.get('Grep', 0) < self.tool_frequency.get('Bash', 0) * 0.1:
            insights.append(Insight(
                category="optimization",
                title="Try the Grep Tool",
                description="You might be using bash grep instead of the native Grep tool.",
                recommendation="The Grep tool is optimized for Claude - it's faster and provides better formatted results.",
                priority=2,
                icon="🔍"
            ))

        # Sort by priority
        insights.sort(key=lambda x: x.priority, reverse=True)

        return insights

    def format_report(self, metrics: ProductivityMetrics, insights: List[Insight]) -> str:
        """Format a beautiful productivity report."""
        lines = []

        # Header
        lines.append("")
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║          🧠 CLAUDE CODE PRODUCTIVITY COACH 🧠               ║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        lines.append("")

        # Score cards
        lines.append("┌─────────────────────────────────────────────────────────────┐")
        lines.append("│                    📊 YOUR SCORES                           │")
        lines.append("├─────────────────────────────────────────────────────────────┤")

        # Productivity score bar
        prod_bar = self._make_bar(metrics.productivity_score)
        lines.append(f"│  Productivity:  {prod_bar} {metrics.productivity_score:.0f}/100  │")

        eff_bar = self._make_bar(metrics.efficiency_score)
        lines.append(f"│  Efficiency:    {eff_bar} {metrics.efficiency_score:.0f}/100  │")

        focus_bar = self._make_bar(metrics.focus_score)
        lines.append(f"│  Focus:         {focus_bar} {metrics.focus_score:.0f}/100  │")

        lines.append("└─────────────────────────────────────────────────────────────┘")
        lines.append("")

        # Key metrics
        lines.append("┌─────────────────────────────────────────────────────────────┐")
        lines.append("│                    📈 KEY METRICS                           │")
        lines.append("├─────────────────────────────────────────────────────────────┤")
        lines.append(f"│  Sessions Analyzed:     {metrics.total_sessions:>6}                          │")
        lines.append(f"│  Total Hours Coded:     {metrics.total_hours:>6.1f}                          │")
        lines.append(f"│  Avg Session Length:    {metrics.avg_session_length_min:>6.0f} min                       │")
        lines.append(f"│  Tools per Session:     {metrics.tools_per_session:>6.1f}                          │")
        lines.append(f"│  Error Rate:            {metrics.error_rate:>6.1f}%                         │")
        lines.append(f"│  Peak Hour:             {metrics.peak_hour:>6}:00                        │")
        lines.append(f"│  Peak Day:              {metrics.peak_day:>12}                   │")
        lines.append("└─────────────────────────────────────────────────────────────┘")
        lines.append("")

        # Insights
        lines.append("┌─────────────────────────────────────────────────────────────┐")
        lines.append("│                    💡 INSIGHTS & TIPS                       │")
        lines.append("└─────────────────────────────────────────────────────────────┘")

        for insight in insights[:7]:  # Top 7 insights
            lines.append("")
            priority_indicator = "!" * insight.priority
            lines.append(f"  {insight.icon} {insight.title} [{priority_indicator}]")
            lines.append(f"     {insight.description}")
            lines.append(f"     → {insight.recommendation}")

        lines.append("")
        lines.append("═" * 65)
        lines.append("")

        return "\n".join(lines)

    def _make_bar(self, value: float, width: int = 30) -> str:
        """Create a progress bar."""
        filled = int(value / 100 * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"


def main():
    """Run the productivity coach."""
    projects_dir = Path.home() / ".claude" / "projects"

    if len(sys.argv) > 1:
        projects_dir = Path(sys.argv[1])

    if not projects_dir.exists():
        print(f"Error: {projects_dir} does not exist")
        sys.exit(1)

    print("🧠 Analyzing your Claude Code usage patterns...")
    print("   This may take a moment...\n")

    coach = ProductivityCoach(projects_dir)
    coach.analyze_sessions()

    metrics = coach.compute_metrics()
    insights = coach.generate_insights(metrics)

    print(coach.format_report(metrics, insights))


if __name__ == "__main__":
    main()
