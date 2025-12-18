"""Base tool class and utilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_string(self) -> str:
        """Convert result to string for API response."""
        if self.error:
            return f"Error: {self.error}"
        return self.output

    @property
    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return not self.success or self.error is not None


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with output or error
        """
        pass

    @classmethod
    @abstractmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API.

        Returns:
            Tool definition dictionary
        """
        pass

    def validate_params(self, **kwargs: Any) -> Optional[str]:
        """Validate parameters before execution.

        Args:
            **kwargs: Parameters to validate

        Returns:
            Error message if invalid, None if valid
        """
        return None


def create_tool_definition(
    name: str,
    description: str,
    properties: Dict[str, Any],
    required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a tool definition in the format expected by the API.

    Args:
        name: Tool name
        description: Tool description
        properties: Parameter properties schema
        required: List of required parameter names

    Returns:
        Tool definition dictionary
    """
    definition = {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
        },
    }
    if required:
        definition["input_schema"]["required"] = required
    return definition
