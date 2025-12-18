"""Anthropic API client wrapper with streaming support."""

import asyncio
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import anthropic
from anthropic import APIError, APIConnectionError, RateLimitError, APIStatusError

from .models import resolve_model


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class APIKeyError(APIClientError):
    """Raised when API key is missing or invalid."""
    pass


class NetworkError(APIClientError):
    """Raised when network connection fails."""
    pass


class RateLimitExceededError(APIClientError):
    """Raised when API rate limit is exceeded."""
    pass


class APIClient:
    """Wrapper around Anthropic SDK with streaming support.

    This client provides automatic retry logic for transient errors,
    better error messages, and usage tracking.

    Example:
        >>> client = APIClient(model="sonnet")
        >>> async for event in client.create_message(
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... ):
        ...     if event["type"] == "text_delta":
        ...         print(event["text"], end="")
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
    ) -> None:
        """Initialize client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use (can be alias or full name)

        Raises:
            APIKeyError: If API key is not provided
            ValueError: If model name is invalid
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise APIKeyError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter.\n\n"
                "Get your API key at: https://console.anthropic.com/settings/keys"
            )

        try:
            self._model = resolve_model(model)
        except Exception as e:
            raise ValueError(f"Invalid model name '{model}': {e}")

        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

        # Token usage tracking
        self._input_tokens = 0
        self._output_tokens = 0
        self._cache_creation_input_tokens = 0
        self._cache_read_input_tokens = 0

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        max_tokens: int = 8192,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Create a message with streaming and automatic retry logic.

        Args:
            messages: Conversation messages
            system: System prompt
            tools: Tool definitions
            stream: Whether to stream the response
            max_tokens: Maximum tokens in response

        Yields:
            Response events

        Raises:
            RateLimitExceededError: If rate limit is exceeded after retries
            NetworkError: If network connection fails after retries
            APIClientError: For other API errors
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        # Retry logic for transient errors
        for attempt in range(self.MAX_RETRIES):
            try:
                if stream:
                    async with self._client.messages.stream(**kwargs) as stream_response:
                        async for event in stream_response:
                            yield self._process_stream_event(event)

                        # Get final message for usage stats
                        final_message = await stream_response.get_final_message()
                        self._update_usage(final_message.usage)
                else:
                    response = await self._client.messages.create(**kwargs)
                    self._update_usage(response.usage)
                    yield {
                        "type": "message",
                        "content": response.content,
                        "stop_reason": response.stop_reason,
                        "usage": {
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                        },
                    }
                # Success - break retry loop
                return

            except RateLimitError as e:
                if attempt < self.MAX_RETRIES - 1:
                    # Wait and retry
                    wait_time = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise RateLimitExceededError(
                        f"Rate limit exceeded. Please try again later.\n"
                        f"Error: {str(e)}"
                    )

            except APIConnectionError as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise NetworkError(
                        f"Network connection failed after {self.MAX_RETRIES} attempts.\n"
                        f"Please check your internet connection.\n"
                        f"Error: {str(e)}"
                    )

            except APIStatusError as e:
                if e.status_code == 401:
                    raise APIKeyError(
                        f"Invalid API key. Please check your ANTHROPIC_API_KEY.\n"
                        f"Get your API key at: https://console.anthropic.com/settings/keys"
                    )
                elif e.status_code == 429:
                    # Rate limit - already handled above
                    raise RateLimitExceededError(f"Rate limit exceeded: {str(e)}")
                elif e.status_code >= 500:
                    # Server error - retry
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = self.RETRY_DELAY * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise APIClientError(
                            f"Anthropic API server error (status {e.status_code}).\n"
                            f"Please try again later.\n"
                            f"Error: {str(e)}"
                        )
                else:
                    raise APIClientError(
                        f"API error (status {e.status_code}): {str(e)}"
                    )

            except APIError as e:
                # Generic API error
                raise APIClientError(f"API error: {str(e)}")

            except Exception as e:
                # Unexpected error
                raise APIClientError(f"Unexpected error: {str(e)}")

    def _process_stream_event(self, event: Any) -> Dict[str, Any]:
        """Process a streaming event into a normalized format.

        Args:
            event: Raw streaming event

        Returns:
            Normalized event dictionary
        """
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            return {
                "type": "message_start",
                "message_id": event.message.id,
                "model": event.message.model,
            }
        elif event_type == "content_block_start":
            block = event.content_block
            if block.type == "text":
                return {
                    "type": "content_block_start",
                    "block_type": "text",
                    "index": event.index,
                }
            elif block.type == "tool_use":
                return {
                    "type": "content_block_start",
                    "block_type": "tool_use",
                    "index": event.index,
                    "tool_name": block.name,
                    "tool_id": block.id,
                }
        elif event_type == "content_block_delta":
            delta = event.delta
            if delta.type == "text_delta":
                return {
                    "type": "text_delta",
                    "text": delta.text,
                    "index": event.index,
                }
            elif delta.type == "input_json_delta":
                return {
                    "type": "input_json_delta",
                    "partial_json": delta.partial_json,
                    "index": event.index,
                }
        elif event_type == "content_block_stop":
            return {
                "type": "content_block_stop",
                "index": event.index,
            }
        elif event_type == "message_delta":
            return {
                "type": "message_delta",
                "stop_reason": event.delta.stop_reason,
            }
        elif event_type == "message_stop":
            return {
                "type": "message_stop",
            }

        # Return raw event for unknown types
        return {
            "type": "unknown",
            "raw_type": event_type,
        }

    def _update_usage(self, usage: Any) -> None:
        """Update cumulative usage statistics.

        Args:
            usage: Usage object from API response
        """
        self._input_tokens += getattr(usage, "input_tokens", 0)
        self._output_tokens += getattr(usage, "output_tokens", 0)
        self._cache_creation_input_tokens += getattr(usage, "cache_creation_input_tokens", 0)
        self._cache_read_input_tokens += getattr(usage, "cache_read_input_tokens", 0)

    def set_model(self, model: str) -> None:
        """Change the active model.

        Args:
            model: Model name or alias
        """
        self._model = resolve_model(model)

    @property
    def model(self) -> str:
        """Get current model name."""
        return self._model

    @property
    def usage(self) -> Dict[str, int]:
        """Get cumulative token usage."""
        return {
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "cache_creation_input_tokens": self._cache_creation_input_tokens,
            "cache_read_input_tokens": self._cache_read_input_tokens,
            "total_tokens": self._input_tokens + self._output_tokens,
        }

    def reset_usage(self) -> None:
        """Reset usage statistics."""
        self._input_tokens = 0
        self._output_tokens = 0
        self._cache_creation_input_tokens = 0
        self._cache_read_input_tokens = 0
