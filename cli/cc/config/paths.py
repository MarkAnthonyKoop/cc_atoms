"""Path constants and utilities for CC CLI."""

import hashlib
import os
from pathlib import Path
from typing import Optional


def get_config_dir() -> Path:
    """Get ~/.cc/ config directory.

    Returns:
        Path to config directory
    """
    return Path.home() / ".cc"


def get_user_settings_path() -> Path:
    """Get path to user settings file.

    Returns:
        Path to ~/.cc/settings.json
    """
    return get_config_dir() / "settings.json"


def get_user_settings_local_path() -> Path:
    """Get path to user local settings file.

    Returns:
        Path to ~/.cc/settings.local.json
    """
    return get_config_dir() / "settings.local.json"


def get_projects_dir() -> Path:
    """Get projects directory.

    Returns:
        Path to ~/.cc/projects/
    """
    return get_config_dir() / "projects"


def get_project_dir(project_path: Path) -> Path:
    """Get project-specific directory under ~/.cc/projects/.

    Args:
        project_path: Path to the project

    Returns:
        Path to project directory in ~/.cc/projects/
    """
    # Create a hash of the absolute path
    abs_path = str(project_path.absolute())
    path_hash = hashlib.sha256(abs_path.encode()).hexdigest()[:16]

    # Use the directory name plus hash for uniqueness
    dir_name = project_path.name
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in dir_name)

    return get_projects_dir() / f"{safe_name}-{path_hash}"


def get_session_dir(project_path: Path) -> Path:
    """Get session directory for a project.

    Args:
        project_path: Path to the project

    Returns:
        Path to sessions directory
    """
    return get_project_dir(project_path) / "sessions"


def get_session_file(session_id: str, project_path: Path) -> Path:
    """Get path to session JSONL file.

    Args:
        session_id: Session ID
        project_path: Path to the project

    Returns:
        Path to session file
    """
    return get_session_dir(project_path) / f"{session_id}.jsonl"


def get_history_file() -> Path:
    """Get path to history.jsonl.

    Returns:
        Path to history file
    """
    return get_config_dir() / "history.jsonl"


def get_local_config_dir(project_path: Optional[Path] = None) -> Path:
    """Get .cc/ directory in project.

    Args:
        project_path: Project path (defaults to cwd)

    Returns:
        Path to .cc/ in project
    """
    if project_path is None:
        project_path = Path.cwd()
    return project_path / ".cc"


def get_local_settings_path(project_path: Optional[Path] = None) -> Path:
    """Get path to local settings in project.

    Args:
        project_path: Project path (defaults to cwd)

    Returns:
        Path to .cc/settings.json
    """
    return get_local_config_dir(project_path) / "settings.json"


def get_local_settings_local_path(project_path: Optional[Path] = None) -> Path:
    """Get path to local private settings in project.

    Args:
        project_path: Project path (defaults to cwd)

    Returns:
        Path to .cc/settings.local.json
    """
    return get_local_config_dir(project_path) / "settings.local.json"


def find_claude_md(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find CLAUDE.md file starting from path.

    Searches up the directory tree for CLAUDE.md.

    Args:
        start_path: Starting path (defaults to cwd)

    Returns:
        Path to CLAUDE.md or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.absolute()

    while current != current.parent:
        claude_md = current / "CLAUDE.md"
        if claude_md.exists():
            return claude_md
        current = current.parent

    # Check root
    claude_md = current / "CLAUDE.md"
    if claude_md.exists():
        return claude_md

    return None


def find_all_claude_md(start_path: Optional[Path] = None) -> list[Path]:
    """Find all CLAUDE.md files in the path hierarchy.

    Args:
        start_path: Starting path (defaults to cwd)

    Returns:
        List of paths to CLAUDE.md files (closest first)
    """
    if start_path is None:
        start_path = Path.cwd()

    results = []
    current = start_path.absolute()

    while current != current.parent:
        claude_md = current / "CLAUDE.md"
        if claude_md.exists():
            results.append(claude_md)
        current = current.parent

    # Check root
    claude_md = current / "CLAUDE.md"
    if claude_md.exists():
        results.append(claude_md)

    return results


def ensure_config_dirs() -> None:
    """Ensure all required config directories exist."""
    dirs = [
        get_config_dir(),
        get_projects_dir(),
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
