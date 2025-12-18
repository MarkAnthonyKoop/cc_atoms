"""
Elysia Sync Tool - Personal knowledge base synchronization via Weaviate/Elysia

Syncs OS data (emails, code, conversations) to Elysia for RAG-based retrieval.
Provides context injection into atom conversations.

Usage:
    # Sync data to Elysia
    from cc_atoms.tools.elysia_sync import sync_to_elysia
    sync_to_elysia(sources=['conversations', 'code'])

    # Query knowledge base
    from cc_atoms.tools.elysia_sync import query_elysia
    results = query_elysia("authentication")

    # Inject context into atom prompts
    from cc_atoms.tools.elysia_sync import inject_context_into_prompt
    enhanced_prompt = inject_context_into_prompt(user_prompt)

    # Create context-aware runtime
    from cc_atoms.tools.elysia_sync import create_context_aware_runtime
    runtime = create_context_aware_runtime(system_prompt, user_prompt)
"""
from .elysia_sync import (
    sync_to_elysia,
    query_elysia,
    get_relevant_context,
    ElysiaSyncConfig,
    main
)

from .context_hook import (
    ElysiaContextHook,
    inject_context_into_prompt,
    create_context_aware_runtime,
    get_startup_context
)

__all__ = [
    # Core sync functions
    'sync_to_elysia',
    'query_elysia',
    'get_relevant_context',
    'ElysiaSyncConfig',
    'main',

    # Context injection
    'ElysiaContextHook',
    'inject_context_into_prompt',
    'create_context_aware_runtime',
    'get_startup_context',
]
