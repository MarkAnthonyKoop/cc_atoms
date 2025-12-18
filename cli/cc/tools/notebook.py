"""NotebookEdit tool for Jupyter notebook editing."""

import json
import os
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class NotebookEditTool(BaseTool):
    """Tool for editing Jupyter notebook cells."""

    name = "NotebookEdit"
    description = """Edit Jupyter notebook (.ipynb) cells.

Completely replaces the contents of a specific cell or inserts/deletes cells.
Jupyter notebooks are interactive documents that combine code, text, and visualizations.

Usage:
- notebook_path: Absolute path to the notebook file
- cell_id or cell_number: Identify which cell to edit (0-indexed)
- new_source: The new content for the cell
- cell_type: "code" or "markdown" (for insert mode)
- edit_mode: "replace" (default), "insert", or "delete"

For insert mode, the new cell is inserted after the specified cell.
For delete mode, the specified cell is removed."""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize NotebookEdit tool.

        Args:
            cwd: Working directory for relative paths
        """
        self.cwd = cwd or os.getcwd()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Edit a Jupyter notebook cell.

        Args:
            notebook_path: Path to the notebook file
            new_source: New content for the cell
            cell_id: Optional cell ID to edit
            cell_type: "code" or "markdown" (for insert mode)
            edit_mode: "replace", "insert", or "delete"

        Returns:
            ToolResult with edit status
        """
        notebook_path = kwargs.get("notebook_path", "")
        new_source = kwargs.get("new_source", "")
        cell_id = kwargs.get("cell_id")
        cell_type = kwargs.get("cell_type", "code")
        edit_mode = kwargs.get("edit_mode", "replace")

        if not notebook_path:
            return ToolResult(
                success=False,
                output="",
                error="No notebook path provided",
            )

        # Resolve path
        if not os.path.isabs(notebook_path):
            notebook_path = os.path.join(self.cwd, notebook_path)

        # Validate file extension
        if not notebook_path.endswith(".ipynb"):
            return ToolResult(
                success=False,
                output="",
                error="File must be a Jupyter notebook (.ipynb)",
            )

        # Validate edit mode
        valid_modes = {"replace", "insert", "delete"}
        if edit_mode not in valid_modes:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid edit_mode '{edit_mode}'. Must be one of: {', '.join(valid_modes)}",
            )

        # Validate cell type
        valid_types = {"code", "markdown"}
        if cell_type not in valid_types:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid cell_type '{cell_type}'. Must be one of: {', '.join(valid_types)}",
            )

        # For replace and insert, new_source is required
        if edit_mode in ("replace", "insert") and not new_source and new_source != "":
            return ToolResult(
                success=False,
                output="",
                error="new_source is required for replace and insert modes",
            )

        try:
            # Read existing notebook or create new one
            if os.path.exists(notebook_path):
                with open(notebook_path, "r", encoding="utf-8") as f:
                    notebook = json.load(f)
            else:
                # Create new notebook structure
                notebook = {
                    "cells": [],
                    "metadata": {
                        "kernelspec": {
                            "display_name": "Python 3",
                            "language": "python",
                            "name": "python3"
                        },
                        "language_info": {
                            "name": "python",
                            "version": "3.9.0"
                        }
                    },
                    "nbformat": 4,
                    "nbformat_minor": 4
                }

            cells = notebook.get("cells", [])

            # Find cell by ID or use index
            cell_index = None
            if cell_id is not None:
                for i, cell in enumerate(cells):
                    if cell.get("id") == cell_id:
                        cell_index = i
                        break
                if cell_index is None and cells:
                    # cell_id might be numeric string meaning index
                    try:
                        cell_index = int(cell_id)
                    except (ValueError, TypeError):
                        pass

            # Handle each edit mode
            if edit_mode == "delete":
                if cell_index is None:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No cell specified for deletion. Provide cell_id.",
                    )
                if cell_index < 0 or cell_index >= len(cells):
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Cell index {cell_index} out of range (0-{len(cells)-1})",
                    )

                deleted_cell = cells.pop(cell_index)
                action = f"Deleted cell {cell_index}"

            elif edit_mode == "insert":
                # Create new cell
                new_cell = self._create_cell(new_source, cell_type)

                if cell_index is not None:
                    # Insert after specified cell
                    insert_pos = cell_index + 1
                    cells.insert(insert_pos, new_cell)
                    action = f"Inserted new {cell_type} cell at position {insert_pos}"
                else:
                    # Insert at beginning if no cell specified
                    cells.insert(0, new_cell)
                    action = f"Inserted new {cell_type} cell at position 0"

            else:  # replace
                if cell_index is None:
                    if not cells:
                        # No cells exist, create first cell
                        new_cell = self._create_cell(new_source, cell_type)
                        cells.append(new_cell)
                        action = f"Created first {cell_type} cell"
                    else:
                        return ToolResult(
                            success=False,
                            output="",
                            error="No cell specified for replacement. Provide cell_id.",
                        )
                else:
                    if cell_index < 0 or cell_index >= len(cells):
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Cell index {cell_index} out of range (0-{len(cells)-1})",
                        )

                    # Update the cell source
                    cells[cell_index]["source"] = self._format_source(new_source)
                    if cell_type:
                        cells[cell_index]["cell_type"] = cell_type
                    action = f"Replaced cell {cell_index}"

            notebook["cells"] = cells

            # Write the notebook back
            os.makedirs(os.path.dirname(notebook_path), exist_ok=True)
            with open(notebook_path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=1)

            return ToolResult(
                success=True,
                output=f"{action} in {notebook_path}. Total cells: {len(cells)}",
                metadata={
                    "notebook_path": notebook_path,
                    "action": edit_mode,
                    "cell_index": cell_index,
                    "total_cells": len(cells),
                },
            )

        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid notebook JSON: {e}",
            )
        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: {notebook_path}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error editing notebook: {e}",
            )

    def _create_cell(self, source: str, cell_type: str) -> Dict[str, Any]:
        """Create a new notebook cell."""
        import uuid

        cell = {
            "cell_type": cell_type,
            "id": str(uuid.uuid4())[:8],
            "metadata": {},
            "source": self._format_source(source),
        }

        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

        return cell

    def _format_source(self, source: str) -> list:
        """Format source content as a list of lines."""
        if not source:
            return []
        lines = source.split("\n")
        # Add newlines to all but the last line
        formatted = [line + "\n" for line in lines[:-1]]
        if lines[-1]:
            formatted.append(lines[-1])
        return formatted

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API."""
        return create_tool_definition(
            name=cls.name,
            description=cls.description,
            properties={
                "notebook_path": {
                    "type": "string",
                    "description": "Absolute path to the Jupyter notebook file",
                },
                "new_source": {
                    "type": "string",
                    "description": "The new source content for the cell",
                },
                "cell_id": {
                    "type": "string",
                    "description": "The ID of the cell to edit (or cell index as string)",
                },
                "cell_type": {
                    "type": "string",
                    "enum": ["code", "markdown"],
                    "description": "The type of cell (code or markdown)",
                },
                "edit_mode": {
                    "type": "string",
                    "enum": ["replace", "insert", "delete"],
                    "description": "Edit mode: replace (default), insert, or delete",
                },
            },
            required=["notebook_path", "new_source"],
        )
