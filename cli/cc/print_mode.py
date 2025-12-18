"""Non-interactive print mode for piping and scripting."""

import json
import sys
from typing import Literal

from .conversation import Conversation

OutputFormat = Literal["text", "json", "stream-json"]
InputFormat = Literal["text", "stream-json"]


class PrintMode:
    """Non-interactive single-shot mode for CLI piping and scripting."""

    def __init__(
        self,
        conversation: Conversation,
        output_format: OutputFormat = "text",
        input_format: InputFormat = "text",
    ) -> None:
        """Initialize print mode.

        Args:
            conversation: Conversation manager
            output_format: Output format (text, json, stream-json)
            input_format: Input format (text, stream-json)
        """
        self.conversation = conversation
        self.output_format = output_format
        self.input_format = input_format

    async def run(self, prompt: str) -> int:
        """Execute a single prompt and print result.

        Args:
            prompt: User prompt to process

        Returns:
            Exit code
        """
        try:
            if self.output_format == "json":
                return await self._run_json(prompt)
            elif self.output_format == "stream-json":
                return await self._run_stream_json(prompt)
            else:
                return await self._run_text(prompt)
        except Exception as e:
            self._print_error(str(e))
            return 1

    async def _run_text(self, prompt: str) -> int:
        """Run in text output mode.

        Args:
            prompt: User prompt

        Returns:
            Exit code
        """
        async for event in self.conversation.send_message(prompt):
            event_type = event.get("type")

            if event_type == "text":
                text = event.get("text", "")
                sys.stdout.write(text)
                sys.stdout.flush()

            elif event_type == "tool_use":
                # In print mode, just note tool usage
                tool_name = event.get("tool_name", "")
                sys.stderr.write(f"\n[Tool: {tool_name}]\n")
                sys.stderr.flush()

            elif event_type == "stop":
                sys.stdout.write("\n")
                sys.stdout.flush()

        return 0

    async def _run_json(self, prompt: str) -> int:
        """Run in JSON output mode.

        Collects the full response and outputs as JSON.

        Args:
            prompt: User prompt

        Returns:
            Exit code
        """
        full_text = ""
        tool_uses = []

        async for event in self.conversation.send_message(prompt):
            event_type = event.get("type")

            if event_type == "text":
                full_text += event.get("text", "")

            elif event_type == "tool_use":
                tool_uses.append({
                    "name": event.get("tool_name", ""),
                    "id": event.get("tool_id", ""),
                    "input": event.get("tool_input", {}),
                })

        # Output JSON
        output = {
            "type": "response",
            "content": full_text,
            "tool_uses": tool_uses,
            "usage": self.conversation.token_count,
            "model": self.conversation.api_client.model,
        }
        print(json.dumps(output, indent=2))

        return 0

    async def _run_stream_json(self, prompt: str) -> int:
        """Run in streaming JSON output mode.

        Outputs each event as a JSON line.

        Args:
            prompt: User prompt

        Returns:
            Exit code
        """
        async for event in self.conversation.send_message(prompt):
            print(json.dumps(event))
            sys.stdout.flush()

        return 0

    def _print_error(self, message: str) -> None:
        """Print error message in appropriate format.

        Args:
            message: Error message
        """
        if self.output_format in ("json", "stream-json"):
            error_obj = {"type": "error", "message": message}
            print(json.dumps(error_obj), file=sys.stderr)
        else:
            print(f"Error: {message}", file=sys.stderr)
