#!/usr/bin/env python3
"""
Test script for atom_gui session scanner functionality.
Tests without launching the GUI.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from atom_gui import SessionScanner, SessionInfo


def test_session_scanner():
    """Test the session scanner."""
    print("Testing SessionScanner...")

    # Test with current working directory or tool directory
    root_path = Path.cwd() if len(sys.argv) > 1 else Path(__file__).parent.parent
    print(f"Scanning from: {root_path}")

    scanner = SessionScanner(root_path)
    sessions = scanner.scan()

    print(f"\nFound {len(sessions)} sessions:")
    for rel_path, session in sorted(sessions.items()):
        print(f"\n  Path: {rel_path}")
        print(f"  Status: {session.status}")
        print(f"  Overview: {session.overview[:60]}..." if len(session.overview) > 60 else f"  Overview: {session.overview}")
        print(f"  Progress items: {len(session.progress)}")

    # Test get_latest_session
    latest = scanner.get_latest_session()
    if latest:
        print(f"\n✓ Latest session: {latest.path.relative_to(root_path)}")
        print(f"  Status: {latest.status}")
    else:
        print("\n✗ No latest session found")

    return len(sessions) > 0


def test_session_info():
    """Test SessionInfo parsing."""
    print("\n\nTesting SessionInfo...")

    # Test with this tool's README
    readme_path = Path(__file__).parent.parent / "README.md"
    if not readme_path.exists():
        print("✗ README.md not found")
        return False

    session = SessionInfo(readme_path.parent, readme_path)

    print(f"Path: {session.path}")
    print(f"Status: {session.status}")
    print(f"Overview: {session.overview[:100]}..." if len(session.overview) > 100 else f"Overview: {session.overview}")
    print(f"Progress items: {len(session.progress)}")

    if session.progress:
        print("\nProgress:")
        for item in session.progress[:5]:  # Show first 5
            print(f"  {item}")

    print(f"\n✓ Successfully parsed README.md")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Atom GUI Session Scanner Tests")
    print("=" * 60)

    results = []

    try:
        results.append(("SessionInfo", test_session_info()))
    except Exception as e:
        print(f"\n✗ SessionInfo test failed: {e}")
        results.append(("SessionInfo", False))

    try:
        results.append(("SessionScanner", test_session_scanner()))
    except Exception as e:
        print(f"\n✗ SessionScanner test failed: {e}")
        results.append(("SessionScanner", False))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    print("=" * 60)

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
