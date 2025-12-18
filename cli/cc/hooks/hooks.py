"""Hooks system for tool execution events."""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class HookEvent(Enum):
    """Hook event types."""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SUBAGENT_START = "SubagentStart"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"


@dataclass
class HookConfig:
    """Configuration for a single hook."""
    event: HookEvent
    command: str
    matchers: Optional[List[str]] = None  # Tool patterns to match


@dataclass
class HookResult:
    """Result from hook execution."""
    success: bool
    output: str
    should_block: bool = False
    modified_input: Optional[Dict[str, Any]] = None


class HooksManager:
    """Manages hook registration and execution."""

    def __init__(self) -> None:
        """Initialize hooks manager."""
        self._hooks: Dict[HookEvent, List[HookConfig]] = {
            event: [] for event in HookEvent
        }
        self._python_hooks: Dict[HookEvent, List[Callable]] = {
            event: [] for event in HookEvent
        }

    def load_from_settings(self, settings: Dict[str, Any]) -> None:
        """Load hooks from settings configuration.

        Args:
            settings: Settings dictionary with hooks config
        """
        hooks_config = settings.get("hooks", {})

        for event_name, hooks in hooks_config.items():
            try:
                event = HookEvent(event_name)
            except ValueError:
                continue  # Unknown hook event

            for hook in hooks:
                if isinstance(hook, dict):
                    command = hook.get("command", "")
                    matchers = hook.get("matchers", [])
                    if command:
                        self._hooks[event].append(HookConfig(
                            event=event,
                            command=command,
                            matchers=matchers,
                        ))
                elif isinstance(hook, str):
                    self._hooks[event].append(HookConfig(
                        event=event,
                        command=hook,
                    ))

    def register_hook(
        self,
        event: HookEvent,
        callback: Callable,
    ) -> None:
        """Register a Python callback as a hook.

        Args:
            event: Hook event type
            callback: Async callback function
        """
        self._python_hooks[event].append(callback)

    def register_command_hook(
        self,
        event: HookEvent,
        command: str,
        matchers: Optional[List[str]] = None,
    ) -> None:
        """Register a shell command as a hook.

        Args:
            event: Hook event type
            command: Shell command to execute
            matchers: Optional tool patterns to match
        """
        self._hooks[event].append(HookConfig(
            event=event,
            command=command,
            matchers=matchers,
        ))

    async def execute(
        self,
        event: HookEvent,
        context: Dict[str, Any],
    ) -> List[HookResult]:
        """Execute all hooks for an event.

        Args:
            event: Hook event type
            context: Event context (tool_name, tool_input, etc.)

        Returns:
            List of hook results
        """
        results: List[HookResult] = []

        # Execute shell command hooks
        for hook_config in self._hooks[event]:
            # Check if hook matches the context
            if not self._matches_context(hook_config, context):
                continue

            result = await self._execute_command_hook(hook_config, context)
            results.append(result)

            # If hook blocks, stop processing
            if result.should_block:
                break

        # Execute Python callback hooks
        for callback in self._python_hooks[event]:
            try:
                result = await callback(context)
                if isinstance(result, HookResult):
                    results.append(result)
            except Exception as e:
                results.append(HookResult(
                    success=False,
                    output=str(e),
                ))

        return results

    def _matches_context(
        self,
        hook_config: HookConfig,
        context: Dict[str, Any],
    ) -> bool:
        """Check if hook matches the event context.

        Args:
            hook_config: Hook configuration
            context: Event context

        Returns:
            True if hook should be executed
        """
        if not hook_config.matchers:
            return True

        tool_name = context.get("tool_name", "")
        tool_input = context.get("tool_input", {})

        for matcher in hook_config.matchers:
            # Simple pattern matching
            if matcher == tool_name:
                return True
            if matcher.endswith("*"):
                prefix = matcher[:-1]
                if tool_name.startswith(prefix):
                    return True
            # Match Bash(command:*) patterns
            if "(" in matcher and tool_name == "Bash":
                import re
                match = re.match(r"Bash\(([^)]+)\)", matcher)
                if match:
                    pattern = match.group(1)
                    command = tool_input.get("command", "")
                    if pattern.endswith(":*"):
                        cmd_prefix = pattern[:-2]
                        if command.startswith(cmd_prefix):
                            return True

        return False

    async def _execute_command_hook(
        self,
        hook_config: HookConfig,
        context: Dict[str, Any],
    ) -> HookResult:
        """Execute a shell command hook.

        Args:
            hook_config: Hook configuration
            context: Event context

        Returns:
            Hook result
        """
        # Prepare environment with context
        env = {
            "HOOK_EVENT": hook_config.event.value,
            "HOOK_TOOL_NAME": context.get("tool_name", ""),
            "HOOK_TOOL_INPUT": json.dumps(context.get("tool_input", {})),
        }

        # Add other context values
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                env[f"HOOK_{key.upper()}"] = str(value)

        try:
            import os
            full_env = {**os.environ, **env}

            process = await asyncio.create_subprocess_shell(
                hook_config.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30,  # 30 second timeout for hooks
            )

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            # Check for special output that indicates blocking
            should_block = process.returncode != 0 or "BLOCK" in output

            return HookResult(
                success=process.returncode == 0,
                output=output.strip(),
                should_block=should_block,
            )

        except asyncio.TimeoutError:
            return HookResult(
                success=False,
                output="Hook timed out",
            )
        except Exception as e:
            return HookResult(
                success=False,
                output=str(e),
            )

    def has_hooks(self, event: HookEvent) -> bool:
        """Check if any hooks are registered for an event.

        Args:
            event: Hook event type

        Returns:
            True if hooks exist
        """
        return bool(self._hooks[event]) or bool(self._python_hooks[event])
