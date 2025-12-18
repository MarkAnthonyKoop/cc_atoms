"""
Elysia Connector - Integration with elysia_sync knowledge base

Provides access to the personal knowledge base synced via elysia_sync,
including Claude conversations, code files, and emails.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ElysiaResult:
    """Result from Elysia query."""
    answer: str
    sources: List[str]
    documents: List[Dict]
    source: str = "elysia"


class ElysiaConnector:
    """
    Connect to Elysia/Weaviate knowledge base.

    Uses the existing elysia_sync tool's configuration and data.
    Queries across conversations, code files, and emails.
    """

    def __init__(self, config=None):
        """
        Initialize Elysia connector.

        Args:
            config: Optional ElysiaSyncConfig (uses default if None)
        """
        self.config = config
        self._client = None
        self._collections = []

        self._init_connection()

    def _init_connection(self):
        """Initialize connection to Elysia."""
        try:
            from cc_atoms.tools.elysia_sync import (
                ElysiaSyncConfig,
                query_elysia,
            )
            from cc_atoms.tools.elysia_sync.elysia_sync import WeaviateClient

            self.config = self.config or ElysiaSyncConfig()
            self._query_elysia = query_elysia

            # Get available collections
            self._collections = [
                self.config.conversations_collection,
                self.config.code_collection,
                self.config.emails_collection,
                self.config.documents_collection,
            ]

            self._available = True

        except ImportError:
            print("Warning: elysia_sync not available")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if Elysia is available and synced."""
        return self._available

    def query(self, query: str, collections: Optional[List[str]] = None, limit: int = 10) -> ElysiaResult:
        """
        Query the Elysia knowledge base.

        Args:
            query: Natural language query
            collections: Specific collections to query (default: all)
            limit: Max results per collection

        Returns:
            ElysiaResult with documents and sources
        """
        if not self._available:
            return ElysiaResult(
                answer="Elysia not available. Run 'elysia-sync sync' first.",
                sources=[],
                documents=[]
            )

        # Use collections or default to all
        target_collections = collections or self._collections

        try:
            results = self._query_elysia(
                query,
                collections=target_collections,
                config=self.config,
                limit=limit
            )

            documents = []
            sources = []

            for doc in results:
                documents.append({
                    "content": doc.get("content", ""),
                    "type": doc.get("type", ""),
                    "source": doc.get("source", ""),
                    "timestamp": doc.get("timestamp", ""),
                    "metadata": doc.get("metadata", {}),
                })
                sources.append(doc.get("source", ""))

            # Generate answer summary
            if documents:
                answer = f"Found {len(documents)} relevant items from knowledge base:\n"
                for i, doc in enumerate(documents[:5], 1):
                    doc_type = doc["type"]
                    source = doc["source"].split("/")[-1] if "/" in doc["source"] else doc["source"]
                    preview = doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"]
                    answer += f"\n{i}. [{doc_type}] {source}: {preview}"
            else:
                answer = "No relevant items found in knowledge base."

            return ElysiaResult(answer=answer, sources=sources, documents=documents)

        except Exception as e:
            return ElysiaResult(
                answer=f"Elysia query error: {e}",
                sources=[],
                documents=[]
            )

    def query_conversations(self, query: str, limit: int = 10) -> ElysiaResult:
        """Query only Claude conversations."""
        return self.query(query, collections=[self.config.conversations_collection], limit=limit)

    def query_code(self, query: str, limit: int = 10) -> ElysiaResult:
        """Query only code files."""
        return self.query(query, collections=[self.config.code_collection], limit=limit)

    def query_emails(self, query: str, limit: int = 10) -> ElysiaResult:
        """Query only emails."""
        return self.query(query, collections=[self.config.emails_collection], limit=limit)

    def get_context_for_prompt(self, prompt: str, max_length: int = 4000) -> Optional[str]:
        """
        Get relevant context from knowledge base for a prompt.

        Useful for context injection into atom prompts.

        Args:
            prompt: The prompt to find context for
            max_length: Maximum context length

        Returns:
            Formatted context string or None
        """
        if not self._available:
            return None

        try:
            from cc_atoms.tools.elysia_sync import get_relevant_context

            result = get_relevant_context(
                query=prompt[:2000],
                config=self.config,
                max_iterations=3,
                verbose=False
            )

            if result.get("found"):
                context = result.get("context", "")
                sources = result.get("sources", [])

                formatted = f"## Relevant Context\n\n{context}\n\nSources: {', '.join(sources[:3])}"
                return formatted[:max_length]

        except Exception:
            pass

        return None
