"""JSONL session storage for CC CLI."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


class SessionStorage:
    """Read/write session JSONL files."""

    def __init__(self, path: Path) -> None:
        """Initialize session storage.

        Args:
            path: Path to the JSONL file
        """
        self.path = path

    def read(self) -> List[Dict[str, Any]]:
        """Read all entries from session file.

        Returns:
            List of all entries
        """
        if not self.path.exists():
            return []

        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def append(self, entry: Dict[str, Any]) -> None:
        """Append an entry to session file.

        Args:
            entry: Entry to append
        """
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def write(self, entries: List[Dict[str, Any]]) -> None:
        """Write all entries to session file (overwrite).

        Args:
            entries: List of entries to write
        """
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def iter_messages(self) -> Iterator[Dict[str, Any]]:
        """Iterate over message entries only.

        Yields:
            Message entries (user and assistant messages)
        """
        for entry in self.read():
            entry_type = entry.get("type")
            if entry_type in ("user", "assistant"):
                yield entry

    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """Get messages formatted for the API.

        Returns:
            List of messages in API format
        """
        messages = []
        for entry in self.iter_messages():
            role = entry.get("type")
            if role == "user":
                content = entry.get("message", {}).get("content", "")
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                content = entry.get("message", {}).get("content", [])
                messages.append({"role": "assistant", "content": content})
        return messages

    @staticmethod
    def create_user_entry(
        content: str,
        session_id: str,
        cwd: str,
        parent_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a user message entry.

        Args:
            content: Message content
            session_id: Session ID
            cwd: Current working directory
            parent_uuid: UUID of parent message

        Returns:
            User entry dictionary
        """
        entry_uuid = str(uuid.uuid4())
        return {
            "type": "user",
            "uuid": entry_uuid,
            "parentUuid": parent_uuid,
            "sessionId": session_id,
            "timestamp": datetime.now().isoformat(),
            "cwd": cwd,
            "message": {
                "role": "user",
                "content": content,
            },
        }

    @staticmethod
    def create_assistant_entry(
        content: Any,
        session_id: str,
        cwd: str,
        parent_uuid: str,
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> Dict[str, Any]:
        """Create an assistant message entry.

        Args:
            content: Message content (string or list of content blocks)
            session_id: Session ID
            cwd: Current working directory
            parent_uuid: UUID of parent message (user message)
            model: Model used
            input_tokens: Input tokens used
            output_tokens: Output tokens used

        Returns:
            Assistant entry dictionary
        """
        entry_uuid = str(uuid.uuid4())
        return {
            "type": "assistant",
            "uuid": entry_uuid,
            "parentUuid": parent_uuid,
            "sessionId": session_id,
            "timestamp": datetime.now().isoformat(),
            "cwd": cwd,
            "message": {
                "role": "assistant",
                "content": content,
                "model": model,
            },
            "usage": {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
            },
        }

    @staticmethod
    def create_tool_use_entry(
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_id: str,
        session_id: str,
        cwd: str,
        parent_uuid: str,
    ) -> Dict[str, Any]:
        """Create a tool use entry.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            tool_id: Tool use ID from API
            session_id: Session ID
            cwd: Current working directory
            parent_uuid: UUID of parent message

        Returns:
            Tool use entry dictionary
        """
        entry_uuid = str(uuid.uuid4())
        return {
            "type": "tool_use",
            "uuid": entry_uuid,
            "parentUuid": parent_uuid,
            "sessionId": session_id,
            "timestamp": datetime.now().isoformat(),
            "cwd": cwd,
            "toolName": tool_name,
            "toolId": tool_id,
            "toolInput": tool_input,
        }

    @staticmethod
    def create_tool_result_entry(
        tool_id: str,
        result: Any,
        is_error: bool,
        session_id: str,
        cwd: str,
        parent_uuid: str,
    ) -> Dict[str, Any]:
        """Create a tool result entry.

        Args:
            tool_id: Tool use ID from API
            result: Tool result
            is_error: Whether the result is an error
            session_id: Session ID
            cwd: Current working directory
            parent_uuid: UUID of parent message

        Returns:
            Tool result entry dictionary
        """
        entry_uuid = str(uuid.uuid4())
        return {
            "type": "tool_result",
            "uuid": entry_uuid,
            "parentUuid": parent_uuid,
            "sessionId": session_id,
            "timestamp": datetime.now().isoformat(),
            "cwd": cwd,
            "toolId": tool_id,
            "result": result,
            "isError": is_error,
        }
