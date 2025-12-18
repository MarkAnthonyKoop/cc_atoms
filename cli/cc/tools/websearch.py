"""WebSearch tool for web search capability."""

from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult, create_tool_definition


class WebSearchTool(BaseTool):
    """Tool for searching the web."""

    name = "WebSearch"
    description = """Search the web and return results.

Allows searching the web to find up-to-date information.
Returns search results with titles, URLs, and snippets.

Usage notes:
- Provide a clear search query
- Can optionally filter by allowed or blocked domains
- Returns structured search results"""

    def __init__(self, cwd: Optional[str] = None) -> None:
        """Initialize WebSearch tool.

        Args:
            cwd: Working directory (not used, but kept for consistency)
        """
        self.cwd = cwd

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute a web search.

        Args:
            query: The search query
            allowed_domains: Optional list of domains to include
            blocked_domains: Optional list of domains to exclude

        Returns:
            ToolResult with search results
        """
        query = kwargs.get("query", "")
        allowed_domains = kwargs.get("allowed_domains", [])
        blocked_domains = kwargs.get("blocked_domains", [])

        if not query:
            return ToolResult(
                success=False,
                output="",
                error="No search query provided",
            )

        if len(query) < 2:
            return ToolResult(
                success=False,
                output="",
                error="Search query must be at least 2 characters",
            )

        # Try to perform actual search using available methods
        try:
            # Try DuckDuckGo HTML (no API key needed)
            results = await self._search_duckduckgo(query, allowed_domains, blocked_domains)

            if results:
                return self._format_results(query, results)
            else:
                return ToolResult(
                    success=True,
                    output=f"No results found for: {query}",
                    metadata={"query": query, "results": []},
                )

        except Exception as e:
            # Fallback: return a message that search couldn't be performed
            return ToolResult(
                success=False,
                output="",
                error=f"Search failed: {e}. Web search requires network access.",
            )

    async def _search_duckduckgo(
        self,
        query: str,
        allowed_domains: List[str],
        blocked_domains: List[str],
    ) -> List[Dict[str, str]]:
        """Search using DuckDuckGo HTML interface."""
        import re
        from urllib.parse import quote_plus, urlparse

        # Modify query for domain filtering
        search_query = query
        if allowed_domains:
            site_filter = " OR ".join(f"site:{d}" for d in allowed_domains)
            search_query = f"({site_filter}) {query}"

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"

        try:
            import aiohttp

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return []
                    html = await response.text()

        except ImportError:
            # Fallback to urllib
            import urllib.request
            import ssl

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html",
            }
            request = urllib.request.Request(url, headers=headers)
            context = ssl.create_default_context()

            with urllib.request.urlopen(request, timeout=10, context=context) as response:
                html = response.read().decode("utf-8", errors="replace")

        # Parse results from HTML
        results = []

        # Find result blocks
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'

        matches = re.findall(result_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (result_url, title) in enumerate(matches[:10]):
            # Clean up URL (DuckDuckGo uses redirects)
            if "uddg=" in result_url:
                actual_url_match = re.search(r"uddg=([^&]+)", result_url)
                if actual_url_match:
                    from urllib.parse import unquote
                    result_url = unquote(actual_url_match.group(1))

            # Apply domain filtering
            parsed = urlparse(result_url)
            domain = parsed.netloc.lower()

            if blocked_domains:
                if any(blocked in domain for blocked in blocked_domains):
                    continue

            # Clean title
            title = title.strip()
            if not title:
                continue

            snippet = snippets[i] if i < len(snippets) else ""

            results.append({
                "title": title,
                "url": result_url,
                "snippet": snippet.strip(),
            })

        return results

    def _format_results(self, query: str, results: List[Dict[str, str]]) -> ToolResult:
        """Format search results into readable output."""
        output_parts = [
            f"Search results for: {query}",
            f"Found {len(results)} results:",
            "",
        ]

        for i, result in enumerate(results, 1):
            output_parts.append(f"{i}. {result['title']}")
            output_parts.append(f"   URL: {result['url']}")
            if result.get("snippet"):
                output_parts.append(f"   {result['snippet']}")
            output_parts.append("")

        return ToolResult(
            success=True,
            output="\n".join(output_parts),
            metadata={
                "query": query,
                "result_count": len(results),
                "results": results,
            },
        )

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """Get the tool definition for the API."""
        return create_tool_definition(
            name=cls.name,
            description=cls.description,
            properties={
                "query": {
                    "type": "string",
                    "description": "The search query",
                    "minLength": 2,
                },
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Only include results from these domains",
                },
                "blocked_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exclude results from these domains",
                },
            },
            required=["query"],
        )
