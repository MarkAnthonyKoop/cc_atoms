"""Settings file management for CC CLI."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import (
    get_user_settings_path,
    get_user_settings_local_path,
    get_local_settings_path,
    get_local_settings_local_path,
    ensure_config_dirs,
)


# Default settings
DEFAULTS: Dict[str, Any] = {
    "model": "claude-sonnet-4-5-20250929",
    "maxTokens": 8192,
    "theme": "auto",
    "markdown": True,
    "toolApproval": "ask",  # "ask", "always", "never"
    "skipPermissions": False,
    "allowedTools": [],
    "disallowedTools": [],
    "hooks": {},
}


class Settings:
    """Manage settings from multiple sources.

    Settings are loaded and merged in this order (later overrides earlier):
    1. Defaults (hardcoded)
    2. User Settings (~/.cc/settings.json)
    3. User Local Settings (~/.cc/settings.local.json)
    4. Project Settings (.cc/settings.json)
    5. Project Local Settings (.cc/settings.local.json)
    6. CLI Arguments (set with scope="cli")
    """

    def __init__(
        self,
        project_path: Optional[Path] = None,
    ) -> None:
        """Initialize settings.

        Args:
            project_path: Project path (defaults to cwd)
        """
        self.project_path = project_path or Path.cwd()

        # Setting sources
        self._defaults = DEFAULTS.copy()
        self._user: Dict[str, Any] = {}
        self._user_local: Dict[str, Any] = {}
        self._project: Dict[str, Any] = {}
        self._project_local: Dict[str, Any] = {}
        self._cli: Dict[str, Any] = {}

        # Merged settings cache
        self._merged: Optional[Dict[str, Any]] = None

    def load(self) -> None:
        """Load settings from all sources."""
        ensure_config_dirs()

        # Load user settings
        self._user = self._load_file(get_user_settings_path())
        self._user_local = self._load_file(get_user_settings_local_path())

        # Load project settings
        self._project = self._load_file(get_local_settings_path(self.project_path))
        self._project_local = self._load_file(get_local_settings_local_path(self.project_path))

        # Invalidate cache
        self._merged = None

    def _load_file(self, path: Path) -> Dict[str, Any]:
        """Load settings from a JSON file with validation.

        Args:
            path: Path to settings file

        Returns:
            Settings dictionary (empty if file doesn't exist or is invalid)
        """
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()

                # Handle empty file
                if not content:
                    return {}

                settings = json.loads(content)

                # Validate that it's a dictionary
                if not isinstance(settings, dict):
                    print(f"Warning: Settings file {path} is not a JSON object. Ignoring.")
                    return {}

                # Validate specific settings
                validated = self._validate_settings(settings, path)
                return validated

        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {path}: {e}")
            print(f"  Ignoring settings from this file.")
            return {}
        except IOError as e:
            print(f"Warning: Could not read {path}: {e}")
            return {}

    def _validate_settings(self, settings: Dict[str, Any], source_path: Path) -> Dict[str, Any]:
        """Validate and sanitize settings.

        Args:
            settings: Raw settings dictionary
            source_path: Path to source file (for error messages)

        Returns:
            Validated settings dictionary
        """
        validated = {}

        for key, value in settings.items():
            # Validate maxTokens
            if key == "maxTokens":
                if not isinstance(value, int):
                    print(f"Warning: maxTokens in {source_path} must be an integer. Ignoring.")
                    continue
                if value < 1 or value > 200000:
                    print(f"Warning: maxTokens in {source_path} must be between 1 and 200000. Ignoring.")
                    continue

            # Validate markdown
            elif key == "markdown":
                if not isinstance(value, bool):
                    print(f"Warning: markdown in {source_path} must be boolean. Ignoring.")
                    continue

            # Validate skipPermissions
            elif key == "skipPermissions":
                if not isinstance(value, bool):
                    print(f"Warning: skipPermissions in {source_path} must be boolean. Ignoring.")
                    continue

            # Validate allowedTools/disallowedTools
            elif key in ("allowedTools", "disallowedTools"):
                if not isinstance(value, list):
                    print(f"Warning: {key} in {source_path} must be a list. Ignoring.")
                    continue
                if not all(isinstance(item, str) for item in value):
                    print(f"Warning: {key} in {source_path} must be a list of strings. Ignoring.")
                    continue

            # Validate hooks
            elif key == "hooks":
                if not isinstance(value, dict):
                    print(f"Warning: hooks in {source_path} must be an object. Ignoring.")
                    continue

            # Validate model
            elif key == "model":
                if not isinstance(value, str):
                    print(f"Warning: model in {source_path} must be a string. Ignoring.")
                    continue
                if not value.strip():
                    print(f"Warning: model in {source_path} cannot be empty. Ignoring.")
                    continue

            # Accept all other settings (for forward compatibility)
            validated[key] = value

        return validated

    def _merge_settings(self) -> Dict[str, Any]:
        """Merge settings from all sources.

        Returns:
            Merged settings dictionary
        """
        merged = self._defaults.copy()

        # Merge in order of precedence
        for source in [
            self._user,
            self._user_local,
            self._project,
            self._project_local,
            self._cli,
        ]:
            for key, value in source.items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    # Deep merge for dicts
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value

        return merged

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value with fallback chain.

        Args:
            key: Setting key (supports dot notation like "hooks.PreToolUse")
            default: Default value if not found

        Returns:
            Setting value
        """
        if self._merged is None:
            self._merged = self._merge_settings()

        # Handle dot notation
        if "." in key:
            parts = key.split(".")
            value = self._merged
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return default
            return value if value is not None else default

        return self._merged.get(key, default)

    def set(self, key: str, value: Any, scope: str = "user") -> None:
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            scope: "user", "user_local", "project", "project_local", or "cli"
        """
        target = {
            "user": self._user,
            "user_local": self._user_local,
            "project": self._project,
            "project_local": self._project_local,
            "cli": self._cli,
        }.get(scope, self._user)

        # Handle dot notation
        if "." in key:
            parts = key.split(".")
            current = target
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            target[key] = value

        # Invalidate cache
        self._merged = None

    def save(self, scope: str = "user") -> None:
        """Save settings to specified scope.

        Args:
            scope: "user", "user_local", "project", or "project_local"
        """
        target, path = {
            "user": (self._user, get_user_settings_path()),
            "user_local": (self._user_local, get_user_settings_local_path()),
            "project": (self._project, get_local_settings_path(self.project_path)),
            "project_local": (self._project_local, get_local_settings_local_path(self.project_path)),
        }.get(scope, (self._user, get_user_settings_path()))

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(target, f, indent=2)

    def all(self) -> Dict[str, Any]:
        """Get all merged settings.

        Returns:
            Dictionary of all settings
        """
        if self._merged is None:
            self._merged = self._merge_settings()
        return self._merged.copy()

    def reset(self, scope: str = "user") -> None:
        """Reset settings in specified scope.

        Args:
            scope: Scope to reset
        """
        if scope == "user":
            self._user = {}
        elif scope == "user_local":
            self._user_local = {}
        elif scope == "project":
            self._project = {}
        elif scope == "project_local":
            self._project_local = {}
        elif scope == "cli":
            self._cli = {}

        self._merged = None

    @property
    def permission_mode(self) -> str:
        """Get current permission mode.

        Returns:
            Permission mode: "ask", "always", or "never"
        """
        if self.get("skipPermissions"):
            return "never"
        return self.get("toolApproval", "ask")

    @property
    def model(self) -> str:
        """Get current model.

        Returns:
            Model name
        """
        return self.get("model", "claude-sonnet-4-5-20250929")
