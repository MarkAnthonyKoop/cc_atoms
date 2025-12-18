"""TodoWrite tool for task list management."""

import json
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult, create_tool_definition


# Global todo storage - persists across tool calls in a session
_todo_list: List[Dict[str, Any]] = []


class TodoWriteTool(BaseTool):
    """Tool for managing a todo list during agentic work."""

    name = "TodoWrite"
    description = """Create and manage a structured task list for the current session.

Use this tool to track progress, organize complex tasks, and demonstrate thoroughness.
It helps the user understand overall progress of their requests.

Usage:
- Create todos with content, status, and activeForm
- Status can be: "pending", "in_progress", "completed"
- activeForm is the present continuous form shown during execution (e.g., "Running tests")
- Update task status in real-time as you work
- Mark tasks complete IMMEDIATELY after finishing

Task States:
- pending: Task not yet started
- in_progress: Currently working on (limit to ONE task at a time)
- completed: Task finished successfully"""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize todo tool.

        Args:
            cwd: Working directory (not used, but kept for consistency)
        """
        self.cwd = cwd

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Update the todo list.

        Args:
            todos: List of todo items, each with:
                - content: Task description (imperative form, e.g., "Run tests")
                - status: "pending" | "in_progress" | "completed"
                - activeForm: Present continuous form (e.g., "Running tests")

        Returns:
            ToolResult with updated todo list status
        """
        global _todo_list

        todos = kwargs.get("todos", [])

        if not isinstance(todos, list):
            return ToolResult(
                success=False,
                output="",
                error="'todos' must be a list of todo items",
            )

        # Validate each todo item
        valid_statuses = {"pending", "in_progress", "completed"}
        validated_todos = []

        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Todo item {i} must be an object",
                )

            content = todo.get("content", "")
            status = todo.get("status", "pending")
            active_form = todo.get("activeForm", content)

            if not content:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Todo item {i} must have 'content'",
                )

            if status not in valid_statuses:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Todo item {i} has invalid status '{status}'. "
                          f"Must be one of: {', '.join(valid_statuses)}",
                )

            validated_todos.append({
                "content": content,
                "status": status,
                "activeForm": active_form,
            })

        # Update the global todo list
        _todo_list = validated_todos

        # Generate summary
        pending = sum(1 for t in validated_todos if t["status"] == "pending")
        in_progress = sum(1 for t in validated_todos if t["status"] == "in_progress")
        completed = sum(1 for t in validated_todos if t["status"] == "completed")
        total = len(validated_todos)

        # Find current task (in_progress)
        current_task = next(
            (t for t in validated_todos if t["status"] == "in_progress"),
            None
        )

        summary_parts = [
            f"Todo list updated: {total} items",
            f"  - Completed: {completed}",
            f"  - In Progress: {in_progress}",
            f"  - Pending: {pending}",
        ]

        if current_task:
            summary_parts.append(f"\nCurrently: {current_task['activeForm']}")

        return ToolResult(
            success=True,
            output="\n".join(summary_parts),
            metadata={
                "total": total,
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "todos": validated_todos,
            },
        )

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API."""
        return create_tool_definition(
            name=cls.name,
            description=cls.description,
            properties={
                "todos": {
                    "type": "array",
                    "description": "The updated todo list",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Task description in imperative form (e.g., 'Run tests')",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Task status",
                            },
                            "activeForm": {
                                "type": "string",
                                "description": "Present continuous form shown during execution (e.g., 'Running tests')",
                            },
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                },
            },
            required=["todos"],
        )


def get_todos() -> List[Dict[str, Any]]:
    """Get the current todo list.

    Returns:
        List of todo items
    """
    return _todo_list.copy()


def clear_todos() -> None:
    """Clear the todo list."""
    global _todo_list
    _todo_list = []
