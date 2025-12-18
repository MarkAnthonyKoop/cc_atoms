"""Tests for conversation management and agentic loop."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator, Dict, Any

from cc.conversation import Conversation
from cc.api import APIClient
from cc.session.manager import SessionManager
from cc.tools.executor import ToolExecutor, PermissionChecker


class MockAPIClient:
    """Mock API client for testing."""

    def __init__(self, model="claude-sonnet-4-5-20250929"):
        self.model = model
        self.usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_tokens": 150,
        }

    async def create_message(
        self,
        messages,
        system=None,
        tools=None,
        stream=True,
        max_tokens=8192,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Mock create_message that simulates tool use."""
        # Check if this is the first call (user message) or tool result
        has_tool_result = any(
            msg.get("role") == "user" and isinstance(msg.get("content"), list)
            for msg in messages
        )

        if not has_tool_result:
            # First response: return a tool use
            yield {"type": "message_start", "message_id": "msg_123", "model": self.model}
            yield {"type": "content_block_start", "block_type": "tool_use", "index": 0, "tool_name": "Bash", "tool_id": "tool_1"}
            yield {"type": "input_json_delta", "partial_json": '{"command": "echo hello"}', "index": 0}
            yield {"type": "content_block_stop", "index": 0}
            yield {"type": "message_delta", "stop_reason": "tool_use"}
            yield {"type": "message_stop"}
        else:
            # Second response: return text after tool execution
            yield {"type": "message_start", "message_id": "msg_124", "model": self.model}
            yield {"type": "content_block_start", "block_type": "text", "index": 0}
            yield {"type": "text_delta", "text": "The command output is: hello", "index": 0}
            yield {"type": "content_block_stop", "index": 0}
            yield {"type": "message_delta", "stop_reason": "end_turn"}
            yield {"type": "message_stop"}


class TestConversation:
    """Test conversation management."""

    @pytest.mark.asyncio
    async def test_conversation_initialization(self, tmp_path):
        """Test basic conversation initialization."""
        api_client = MockAPIClient()
        session_manager = SessionManager(tmp_path)

        conv = Conversation(
            api_client=api_client,
            session_manager=session_manager,
            system_prompt="Test prompt",
            skip_permissions=True,
        )

        assert conv.api_client == api_client
        assert conv.session_manager == session_manager
        assert conv.system_prompt == "Test prompt"
        assert conv.message_count == 0

    @pytest.mark.asyncio
    async def test_agentic_loop_with_tool_execution(self, tmp_path):
        """Test that the agentic loop executes tools and continues."""
        api_client = MockAPIClient()
        session_manager = SessionManager(tmp_path)

        # Create conversation with skip_permissions enabled
        conv = Conversation(
            api_client=api_client,
            session_manager=session_manager,
            system_prompt="Test",
            skip_permissions=True,
        )

        # Send a message and collect events
        events = []
        async for event in conv.send_message("Run echo hello", stream=True, auto_execute_tools=True):
            events.append(event)

        # Verify we got the expected events
        event_types = [e.get("type") for e in events]

        # Should have: tool_use, tool_executing, tool_result, text, stop
        assert "tool_use" in event_types, f"Expected tool_use in {event_types}"
        assert "tool_executing" in event_types, f"Expected tool_executing in {event_types}"
        assert "tool_result" in event_types, f"Expected tool_result in {event_types}"
        assert "text" in event_types, f"Expected text in {event_types}"
        assert "stop" in event_types, f"Expected stop in {event_types}"

        # Find the tool_use event
        tool_use_event = next(e for e in events if e.get("type") == "tool_use")
        assert tool_use_event["tool_name"] == "Bash"
        assert tool_use_event["tool_input"]["command"] == "echo hello"

        # Find the tool_result event
        tool_result_event = next(e for e in events if e.get("type") == "tool_result")
        assert "hello" in tool_result_event["result"].lower()

        # Find the final text event
        text_events = [e for e in events if e.get("type") == "text"]
        assert len(text_events) > 0
        final_text = "".join(e.get("text", "") for e in text_events)
        assert "hello" in final_text.lower()

        # Verify message history includes all parts
        assert conv.message_count > 1  # Should have user, assistant, user (tool result), assistant

    @pytest.mark.asyncio
    async def test_tool_execution_without_auto_execute(self, tmp_path):
        """Test that auto_execute_tools=False doesn't execute tools."""
        api_client = MockAPIClient()
        session_manager = SessionManager(tmp_path)

        conv = Conversation(
            api_client=api_client,
            session_manager=session_manager,
            skip_permissions=True,
        )

        # Send message with auto_execute_tools=False
        events = []
        async for event in conv.send_message("Test", stream=True, auto_execute_tools=False):
            events.append(event)

        event_types = [e.get("type") for e in events]

        # Should have tool_use but NOT tool_executing or tool_result
        assert "tool_use" in event_types
        assert "tool_executing" not in event_types
        assert "tool_result" not in event_types

    @pytest.mark.asyncio
    async def test_message_persistence(self, tmp_path):
        """Test that messages are persisted to session storage."""
        api_client = MockAPIClient()
        session_manager = SessionManager(tmp_path)

        conv = Conversation(
            api_client=api_client,
            session_manager=session_manager,
            skip_permissions=True,
        )

        # Send a message
        async for event in conv.send_message("Test message", auto_execute_tools=True):
            pass  # Just drain the events

        # Verify session was created and has messages
        assert conv.session_id is not None
        storage = session_manager.get_storage()
        assert storage is not None

        entries = storage.read()
        assert len(entries) > 0

        # Should have at least: user message, assistant message
        entry_types = [e.get("type") for e in entries]
        assert "user" in entry_types
        assert "assistant" in entry_types

    @pytest.mark.asyncio
    async def test_clear_conversation(self, tmp_path):
        """Test clearing conversation history."""
        api_client = MockAPIClient()
        session_manager = SessionManager(tmp_path)

        conv = Conversation(
            api_client=api_client,
            session_manager=session_manager,
            skip_permissions=True,
        )

        # Send a message
        async for event in conv.send_message("Test", auto_execute_tools=False):
            pass

        initial_count = conv.message_count
        assert initial_count > 0

        # Clear conversation
        conv.clear()

        assert conv.message_count == 0

    @pytest.mark.asyncio
    async def test_compact_conversation(self, tmp_path):
        """Test conversation compaction."""
        api_client = MockAPIClient()
        session_manager = SessionManager(tmp_path)

        conv = Conversation(
            api_client=api_client,
            session_manager=session_manager,
            skip_permissions=True,
        )

        # Manually add many messages
        for i in range(30):
            conv._messages.append({"role": "user", "content": f"Message {i}"})

        assert conv.message_count == 30

        # Compact
        conv.compact()

        # Should be reduced
        assert conv.message_count <= 20
