#!/usr/bin/env python3
"""
Claude Code Analytics Suite
Unified launcher for all analytics tools.
"""

import sys
from pathlib import Path


BANNER = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║    ██████╗ ██████╗     █████╗ ███╗   ██╗ █████╗ ██╗  ██╗   ██╗      ║
║   ██╔════╝██╔════╝    ██╔══██╗████╗  ██║██╔══██╗██║  ╚██╗ ██╔╝      ║
║   ██║     ██║         ███████║██╔██╗ ██║███████║██║   ╚████╔╝       ║
║   ██║     ██║         ██╔══██║██║╚██╗██║██╔══██║██║    ╚██╔╝        ║
║   ╚██████╗╚██████╗    ██║  ██║██║ ╚████║██║  ██║███████╗██║         ║
║    ╚═════╝ ╚═════╝    ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝         ║
║                                                                      ║
║              Claude Code Analytics Suite v1.0                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

HELP = """
Usage: cc-analytics <command> [options]

Commands:
  report      Generate comprehensive session analytics report
  dashboard   Launch interactive terminal dashboard
  monitor     Start real-time session monitor
  coach       Get AI-powered productivity insights and recommendations

Options:
  --help, -h  Show this help message
  --dir PATH  Custom projects directory (default: ~/.claude/projects)

Examples:
  cc-analytics report              # Generate analytics report
  cc-analytics dashboard           # Launch interactive dashboard
  cc-analytics monitor             # Watch sessions in real-time
  cc-analytics coach               # Get productivity coaching

Run any command with --help for more information.
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
        print(BANNER)
        print(HELP)
        sys.exit(0)

    command = sys.argv[1]

    # Get custom directory if specified
    projects_dir = Path.home() / ".claude" / "projects"
    if '--dir' in sys.argv:
        idx = sys.argv.index('--dir')
        if idx + 1 < len(sys.argv):
            projects_dir = Path(sys.argv[idx + 1])

    # Import and run the appropriate tool
    tools_dir = Path(__file__).parent

    if command == 'report':
        from cc.tools.conversation_analyzer import ConversationAnalyzer, main as report_main
        report_main()

    elif command == 'dashboard':
        from cc.tools.dashboard import main as dashboard_main
        dashboard_main()

    elif command == 'monitor':
        from cc.tools.live_monitor import main as monitor_main
        monitor_main()

    elif command == 'coach':
        from cc.tools.productivity_coach import main as coach_main
        coach_main()

    else:
        print(f"Unknown command: {command}")
        print("Run 'cc-analytics --help' for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
