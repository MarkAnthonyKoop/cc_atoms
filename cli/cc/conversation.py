"""Core conversation management for CC CLI."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from pathlib import Path

from .api import APIClient
from .session.manager import SessionManager
from .session.storage import SessionStorage
from .tools import ToolExecutor, PermissionChecker


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user" | "assistant"
    content: Any  # str or List[ContentBlock]
    uuid: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class Conversation:
    """Manages a multi-turn conversation with Claude."""

    def __init__(
        self,
        api_client: APIClient,
        session_manager: SessionManager,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_executor: Optional[ToolExecutor] = None,
        skip_permissions: bool = False,
        allowed_tools: Optional[List[str]] = None,
        disallowed_tools: Optional[List[str]] = None,
    ) -> None:
        """Initialize conversation.

        Args:
            api_client: API client for Anthropic
            session_manager: Session manager for persistence
            system_prompt: Optional system prompt
            session_id: Optional session ID to resume
            tool_executor: Optional tool executor (creates default if None)
            skip_permissions: Skip permission checks for tools
            allowed_tools: List of allowed tool patterns
            disallowed_tools: List of disallowed tool patterns
        """
        self.api_client = api_client
        self.session_manager = session_manager
        self.system_prompt = system_prompt

        # Set up tool executor
        if tool_executor:
            self.tool_executor = tool_executor
        else:
            permission_checker = PermissionChecker(
                allow_patterns=allowed_tools,
                deny_patterns=disallowed_tools,
                skip_permissions=skip_permissions,
            )
            self.tool_executor = ToolExecutor(permission_checker=permission_checker)

        # Callbacks for tool approval
        self._tool_approval_callback: Optional[Callable] = None

        # Conversation state
        self._messages: List[Dict[str, Any]] = []
        self._storage: Optional[SessionStorage] = None
        self._last_user_uuid: Optional[str] = None

        # Load existing session or create new one
        if session_id:
            try:
                self._storage = session_manager.load(session_id)
                self._messages = self._storage.get_messages_for_api()
            except FileNotFoundError:
                # Create new session if not found
                session_manager.create()
                self._storage = session_manager.get_storage()
        else:
            session_manager.create()
            self._storage = session_manager.get_storage()

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.session_manager.get_current()

    @property
    def cwd(self) -> str:
        """Get current working directory."""
        return os.getcwd()

    def set_tool_approval_callback(self, callback: Callable) -> None:
        """Set callback for tool approval prompts.

        Args:
            callback: Async function(tool_name, tool_input) -> bool
        """
        self._tool_approval_callback = callback

    async def send_message(
        self,
        content: str,
        stream: bool = True,
        auto_execute_tools: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a message and yield streaming response chunks.

        Args:
            content: User message content
            stream: Whether to stream the response
            auto_execute_tools: Whether to automatically execute tools

        Yields:
            Response chunks with type, content, etc.
        """
        # Add user message (only if content is not empty)
        if content:
            user_entry = SessionStorage.create_user_entry(
                content=content,
                session_id=self.session_id or "",
                cwd=self.cwd,
                parent_uuid=self._last_user_uuid,
            )
            self._last_user_uuid = user_entry["uuid"]

            # Persist user message
            if self._storage:
                self._storage.append(user_entry)

            # Add to conversation
            self._messages.append({"role": "user", "content": content})

        # Get response and handle tool use loop
        while True:
            # Get response
            full_response_content: List[Dict[str, Any]] = []
            current_text = ""
            current_tool_use: Optional[Dict[str, Any]] = None
            tool_input_json = ""
            pending_tools: List[Dict[str, Any]] = []
            stop_reason = None

            async for event in self.api_client.create_message(
                messages=self._messages,
                system=self.system_prompt,
                tools=self._get_tool_definitions(),
                stream=stream,
            ):
                event_type = event.get("type")

                if event_type == "content_block_start":
                    block_type = event.get("block_type")
                    if block_type == "text":
                        current_text = ""
                    elif block_type == "tool_use":
                        current_tool_use = {
                            "type": "tool_use",
                            "id": event.get("tool_id", ""),
                            "name": event.get("tool_name", ""),
                            "input": {},
                        }
                        tool_input_json = ""

                elif event_type == "text_delta":
                    text = event.get("text", "")
                    current_text += text
                    yield {
                        "type": "text",
                        "text": text,
                    }

                elif event_type == "input_json_delta":
                    tool_input_json += event.get("partial_json", "")

                elif event_type == "content_block_stop":
                    if current_text:
                        full_response_content.append({
                            "type": "text",
                            "text": current_text,
                        })
                        current_text = ""
                    elif current_tool_use:
                        # Parse accumulated JSON
                        try:
                            current_tool_use["input"] = json.loads(tool_input_json) if tool_input_json else {}
                        except json.JSONDecodeError:
                            current_tool_use["input"] = {}

                        full_response_content.append(current_tool_use)
                        pending_tools.append(current_tool_use)
                        yield {
                            "type": "tool_use",
                            "tool_name": current_tool_use["name"],
                            "tool_id": current_tool_use["id"],
                            "tool_input": current_tool_use["input"],
                        }
                        current_tool_use = None
                        tool_input_json = ""

                elif event_type == "message_delta":
                    stop_reason = event.get("stop_reason")

            # Add assistant message to conversation
            if full_response_content:
                self._messages.append({"role": "assistant", "content": full_response_content})

                # Persist assistant message
                if self._storage:
                    usage = self.api_client.usage
                    assistant_entry = SessionStorage.create_assistant_entry(
                        content=full_response_content,
                        session_id=self.session_id or "",
                        cwd=self.cwd,
                        parent_uuid=self._last_user_uuid or "",
                        model=self.api_client.model,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                    )
                    self._storage.append(assistant_entry)

            # Handle tool execution if needed
            if pending_tools and auto_execute_tools:
                tool_results = []

                for tool in pending_tools:
                    tool_name = tool["name"]
                    tool_input = tool["input"]
                    tool_id = tool["id"]

                    # Execute tool
                    yield {
                        "type": "tool_executing",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_id": tool_id,
                    }

                    result = await self.tool_executor.execute(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_id=tool_id,
                    )

                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "tool_id": tool_id,
                        "result": result.to_string(),
                        "is_error": result.is_error,
                    }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result.to_string(),
                        "is_error": result.is_error,
                    })

                    # Persist tool result
                    if self._storage:
                        tool_result_entry = SessionStorage.create_tool_result_entry(
                            tool_id=tool_id,
                            result=result.to_string(),
                            is_error=result.is_error,
                            session_id=self.session_id or "",
                            cwd=self.cwd,
                            parent_uuid=self._last_user_uuid or "",
                        )
                        self._storage.append(tool_result_entry)

                # Add tool results to messages
                self._messages.append({"role": "user", "content": tool_results})

                # Continue the loop to get the next response
                continue

            # No more tools to execute, signal completion and break
            yield {
                "type": "stop",
                "stop_reason": stop_reason,
            }
            break

    async def send_tool_result(
        self,
        tool_id: str,
        result: Any,
        is_error: bool = False,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a tool result back to the model.

        Args:
            tool_id: Tool use ID from the model
            result: Tool execution result
            is_error: Whether the result is an error

        Yields:
            Response chunks
        """
        # Persist tool result
        if self._storage:
            tool_result_entry = SessionStorage.create_tool_result_entry(
                tool_id=tool_id,
                result=result,
                is_error=is_error,
                session_id=self.session_id or "",
                cwd=self.cwd,
                parent_uuid=self._last_user_uuid or "",
            )
            self._storage.append(tool_result_entry)

        # Add tool result to messages
        tool_result_content = {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": str(result),
        }
        if is_error:
            tool_result_content["is_error"] = True

        self._messages.append({"role": "user", "content": [tool_result_content]})

        # Continue conversation
        async for event in self.send_message("", stream=True):
            yield event

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for the API.

        Returns:
            List of tool definitions
        """
        return self.tool_executor.get_tool_definitions()

    def get_messages(self) -> List[Message]:
        """Get all messages in the conversation.

        Returns:
            List of messages
        """
        messages = []
        for msg in self._messages:
            content = msg.get("content", "")
            messages.append(Message(
                role=msg.get("role", ""),
                content=content,
            ))
        return messages

    def clear(self) -> None:
        """Clear the conversation history."""
        self._messages = []
        # Create new session
        self.session_manager.create()
        self._storage = self.session_manager.get_storage()
        self._last_user_uuid = None

    def compact(self) -> None:
        """Compact the conversation to reduce tokens.

        This summarizes older messages while keeping recent context.
        """
        # Simple compaction: keep only the last N messages
        max_messages = 20
        if len(self._messages) > max_messages:
            # Keep first message (might have important context) and last N-1
            self._messages = [self._messages[0]] + self._messages[-(max_messages - 1):]

    @property
    def message_count(self) -> int:
        """Get number of messages in conversation."""
        return len(self._messages)

    @property
    def token_count(self) -> Dict[str, int]:
        """Get token usage for conversation."""
        return self.api_client.usage
