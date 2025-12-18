"""WebFetch tool for fetching and parsing web pages."""

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .base import BaseTool, ToolResult, create_tool_definition


class WebFetchTool(BaseTool):
    """Tool for fetching content from URLs and processing it."""

    name = "WebFetch"
    description = """Fetch content from a URL and process it.

Takes a URL and a prompt as input, fetches the URL content,
converts HTML to markdown, and returns the processed content.

Usage notes:
- The URL must be a fully-formed valid URL
- HTTP URLs will be automatically upgraded to HTTPS
- The prompt should describe what information you want to extract
- Results may be summarized if the content is very large"""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize WebFetch tool.

        Args:
            cwd: Working directory (not used, but kept for consistency)
        """
        self.cwd = cwd

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Fetch content from a URL.

        Args:
            url: The URL to fetch content from
            prompt: What information to extract from the page

        Returns:
            ToolResult with fetched and processed content
        """
        url = kwargs.get("url", "")
        prompt = kwargs.get("prompt", "")

        if not url:
            return ToolResult(
                success=False,
                output="",
                error="No URL provided",
            )

        if not prompt:
            return ToolResult(
                success=False,
                output="",
                error="No prompt provided. Please specify what information to extract.",
            )

        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
                parsed = urlparse(url)

            if parsed.scheme not in ("http", "https"):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid URL scheme: {parsed.scheme}. Must be http or https.",
                )

            if not parsed.netloc:
                return ToolResult(
                    success=False,
                    output="",
                    error="Invalid URL: no host specified",
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid URL format: {e}",
            )

        # Upgrade HTTP to HTTPS
        if parsed.scheme == "http":
            url = url.replace("http://", "https://", 1)

        try:
            # Try to import aiohttp for async HTTP requests
            try:
                import aiohttp
                return await self._fetch_with_aiohttp(url, prompt)
            except ImportError:
                # Fallback to urllib if aiohttp not available
                return await self._fetch_with_urllib(url, prompt)

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error fetching URL: {e}",
            )

    async def _fetch_with_aiohttp(self, url: str, prompt: str) -> ToolResult:
        """Fetch using aiohttp (async)."""
        import aiohttp

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CCBot/1.0; +https://github.com/anthropics/claude-code)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                if response.status != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status}: {response.reason}",
                    )

                content = await response.text()
                return self._process_content(url, content, prompt)

    async def _fetch_with_urllib(self, url: str, prompt: str) -> ToolResult:
        """Fetch using urllib (sync, fallback)."""
        import urllib.request
        import ssl

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CCBot/1.0; +https://github.com/anthropics/claude-code)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        request = urllib.request.Request(url, headers=headers)
        context = ssl.create_default_context()

        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            content = response.read().decode("utf-8", errors="replace")
            return self._process_content(url, content, prompt)

    def _process_content(self, url: str, content: str, prompt: str) -> ToolResult:
        """Process HTML content into a cleaner format."""
        # Simple HTML to text conversion
        text = self._html_to_text(content)

        # Truncate if too long
        max_length = 50000  # Characters
        truncated = False
        if len(text) > max_length:
            text = text[:max_length]
            truncated = True

        output_parts = [
            f"URL: {url}",
            f"Prompt: {prompt}",
            "",
            "--- Content ---",
            text,
        ]

        if truncated:
            output_parts.append("\n[Content truncated due to length]")

        return ToolResult(
            success=True,
            output="\n".join(output_parts),
            metadata={
                "url": url,
                "content_length": len(content),
                "text_length": len(text),
                "truncated": truncated,
            },
        )

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple implementation)."""
        # Remove script and style content
        html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)

        # Convert common HTML elements
        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</div>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</li>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</h[1-6]>", "\n\n", html, flags=re.IGNORECASE)

        # Remove all remaining tags
        html = re.sub(r"<[^>]+>", "", html)

        # Decode HTML entities
        html = html.replace("&nbsp;", " ")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&amp;", "&")
        html = html.replace("&quot;", '"')
        html = html.replace("&#39;", "'")

        # Clean up whitespace
        lines = []
        for line in html.split("\n"):
            line = " ".join(line.split())
            if line:
                lines.append(line)

        return "\n".join(lines)

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API."""
        return create_tool_definition(
            name=cls.name,
            description=cls.description,
            properties={
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "The URL to fetch content from",
                },
                "prompt": {
                    "type": "string",
                    "description": "Description of what information to extract from the page",
                },
            },
            required=["url", "prompt"],
        )
