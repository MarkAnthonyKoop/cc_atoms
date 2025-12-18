"""
Context Hook - Automatic context injection for atom conversations

This module provides hooks that can be integrated into the atom control flow
to automatically inject relevant context from the Elysia knowledge base.

Usage in atom system prompts:
    Include a reference to call get_context_for_conversation() at the start
    of each conversation to retrieve relevant background knowledge.

Integration with AtomRuntime:
    The hook can be called before runtime.run() to prepend relevant context
    to the user's prompt.
"""
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

from .elysia_sync import (
    ElysiaSyncConfig,
    WeaviateClient,
    get_relevant_context,
    query_elysia
)


class ElysiaContextHook:
    """
    Hook for injecting Elysia context into atom conversations.

    This class provides methods to:
    1. Extract key concepts from a conversation/query
    2. Query Elysia for relevant documents
    3. Format context for injection into prompts
    """

    def __init__(self, config: Optional[ElysiaSyncConfig] = None):
        self.config = config or ElysiaSyncConfig()
        self.enabled = self._check_enabled()

    def _check_enabled(self) -> bool:
        """Check if Elysia integration is available"""
        # Check for Weaviate connection
        try:
            client = WeaviateClient(self.config)
            if client.connect():
                client.close()
                return True
        except:
            pass
        return False

    def get_context_for_conversation(
        self,
        conversation_text: str,
        max_context_length: int = 4000
    ) -> Optional[str]:
        """
        Get relevant context for a conversation.

        Args:
            conversation_text: The current conversation or query
            max_context_length: Maximum length of context to return

        Returns:
            Formatted context string or None if no relevant context found
        """
        if not self.enabled:
            return None

        # Use the embedded atom to intelligently extract context
        result = get_relevant_context(
            query=conversation_text[:2000],  # Limit query size
            config=self.config,
            max_iterations=3,
            verbose=False
        )

        if not result['found']:
            return None

        # Format context for injection
        context = f"""## Relevant Context from Knowledge Base

{result['context']}

**Sources:** {', '.join(result['sources'][:3])}

---

"""
        return context[:max_context_length]

    def quick_context_lookup(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Quick context lookup without embedded atom processing.

        Faster but less intelligent than get_context_for_conversation.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of relevant documents
        """
        if not self.enabled:
            return []

        return query_elysia(query, config=self.config, limit=limit)

    def format_context_block(
        self,
        documents: List[Dict[str, Any]],
        max_length: int = 3000
    ) -> str:
        """
        Format a list of documents into a context block.

        Args:
            documents: List of documents from query_elysia
            max_length: Maximum total length

        Returns:
            Formatted context string
        """
        if not documents:
            return ""

        parts = ["## Background Context\n"]
        current_length = len(parts[0])

        for doc in documents:
            content = doc.get('content', '')[:500]
            source = doc.get('source', 'unknown')
            doc_type = doc.get('type', 'unknown')

            block = f"\n**[{doc_type}]** {source}\n{content}\n"

            if current_length + len(block) > max_length:
                break

            parts.append(block)
            current_length += len(block)

        parts.append("\n---\n")
        return ''.join(parts)


def inject_context_into_prompt(
    user_prompt: str,
    config: Optional[ElysiaSyncConfig] = None,
    max_context_length: int = 4000
) -> str:
    """
    Convenience function to inject context into a user prompt.

    This can be called before passing a prompt to AtomRuntime.run().

    Args:
        user_prompt: The original user prompt
        config: Elysia configuration
        max_context_length: Maximum context length

    Returns:
        Modified prompt with context prepended (or original if no context found)
    """
    hook = ElysiaContextHook(config)

    context = hook.get_context_for_conversation(
        user_prompt,
        max_context_length=max_context_length
    )

    if context:
        return f"{context}\n{user_prompt}"

    return user_prompt


def create_context_aware_runtime(
    system_prompt: str,
    user_prompt: str,
    config: Optional[ElysiaSyncConfig] = None,
    **runtime_kwargs
) -> 'AtomRuntime':
    """
    Create an AtomRuntime with context-aware prompt injection.

    This is a convenience function that:
    1. Queries Elysia for relevant context
    2. Injects context into the system prompt
    3. Returns a configured AtomRuntime

    Args:
        system_prompt: Base system prompt
        user_prompt: User's task/query
        config: Elysia configuration
        **runtime_kwargs: Additional arguments for AtomRuntime

    Returns:
        Configured AtomRuntime instance
    """
    from cc_atoms.atom_core import AtomRuntime

    hook = ElysiaContextHook(config)

    # Get context based on user prompt
    context = hook.get_context_for_conversation(user_prompt)

    if context:
        # Inject context into system prompt
        enhanced_system_prompt = f"""{system_prompt}

## Knowledge Base Context

The following relevant information was found in the user's personal knowledge base:

{context}

Use this context to inform your responses when relevant.
"""
    else:
        enhanced_system_prompt = system_prompt

    return AtomRuntime.create_ephemeral(
        system_prompt=enhanced_system_prompt,
        **runtime_kwargs
    )


# =============================================================================
# Default Atom Integration
# =============================================================================

# Environment variable to enable/disable context injection
ELYSIA_CONTEXT_ENABLED = os.getenv('ELYSIA_CONTEXT_ENABLED', 'true').lower() == 'true'


def get_startup_context(conversation_dir: Optional[Path] = None) -> Optional[str]:
    """
    Get startup context for an atom session.

    This function is designed to be called at the beginning of an atom session
    to provide relevant background knowledge.

    Args:
        conversation_dir: The conversation directory (used to infer project context)

    Returns:
        Context string or None
    """
    if not ELYSIA_CONTEXT_ENABLED:
        return None

    hook = ElysiaContextHook()

    if not hook.enabled:
        return None

    # Build a query based on the conversation directory
    if conversation_dir:
        # Extract project name from path
        project_hint = conversation_dir.name.replace('-', ' ')
        query = f"Context for project: {project_hint}"
    else:
        query = "Recent conversations and relevant code"

    # Quick lookup for startup (don't use full atom processing)
    docs = hook.quick_context_lookup(query, limit=3)

    if docs:
        return hook.format_context_block(docs, max_length=2000)

    return None
