"""
Memory Context Provider for AtomRuntime

Provides context from the home directory index when relevant to the prompt.
Uses relevance scoring to only inject context when it's actually useful.

Key design decisions:
1. Only provide context when relevance score > threshold
2. Context is prepended to system prompt, not the user prompt
3. Minimal context - just enough to be helpful, not overwhelming
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


# Relevance threshold - documents must score above this to be included
RELEVANCE_THRESHOLD = 0.50  # Cosine similarity (0-1 scale)

# Maximum context to inject
MAX_CONTEXT_DOCS = 3
MAX_CONTEXT_CHARS = 2000


class MemoryProvider:
    """
    Provides relevant context from indexed memory.

    Uses the chromadb venv for queries - works from any Python version.
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "home_directory",
        relevance_threshold: float = RELEVANCE_THRESHOLD,
        enabled: bool = True,
        verbose: bool = False
    ):
        """
        Initialize memory provider.

        Args:
            persist_dir: Path to Chroma database
            collection_name: Collection name
            relevance_threshold: Minimum relevance score (0-1)
            enabled: Whether memory is enabled
            verbose: Print debug info
        """
        self.persist_dir = persist_dir or str(Path.home() / '.cache' / 'multi_db_agent' / 'home_index')
        self.collection_name = collection_name
        self.relevance_threshold = relevance_threshold
        self.enabled = enabled
        self.verbose = verbose

        # Path to the chromadb venv Python
        self.venv_python = Path.home() / '.venvs' / 'chromadb-env' / 'bin' / 'python'

    def _log(self, msg: str):
        if self.verbose:
            print(f"[Memory] {msg}")

    def _query_via_subprocess(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the index using a subprocess (works from any Python version).

        Returns list of {content, score, source, type} dicts.
        """
        if not self.venv_python.exists():
            self._log(f"Venv not found at {self.venv_python}")
            return []

        # Python script to run in the venv
        script = f'''
import json
import os
import sys
sys.path.insert(0, str({repr(str(Path.home() / '.venvs' / 'chromadb-env' / 'lib' / 'python3.9' / 'site-packages'))}))

from pathlib import Path

# Import after path setup
from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexer, HomeIndexerConfig

config = HomeIndexerConfig(
    persist_dir={repr(self.persist_dir)},
    collection_name={repr(self.collection_name)},
)

indexer = HomeIndexer(config=config, verbose=False)

try:
    results = indexer.query({repr(query)}, top_k={top_k})
    # Convert to JSON-serializable format
    output = []
    for doc in results:
        output.append({{
            "content": doc.get("content", "")[:1500],
            "score": doc.get("score", 0),
            "source": doc.get("source", ""),
            "type": doc.get("type", ""),
            "relative_path": doc.get("relative_path", ""),
        }})
    print(json.dumps(output))
except Exception as e:
    print(json.dumps([]))
'''

        try:
            result = subprocess.run(
                [str(self.venv_python), '-c', script],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ}
            )

            if result.returncode == 0:
                return json.loads(result.stdout.strip())
            else:
                self._log(f"Query failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            self._log("Query timed out")
            return []
        except json.JSONDecodeError as e:
            self._log(f"JSON parse error: {e}")
            return []
        except Exception as e:
            self._log(f"Query error: {e}")
            return []

    def get_relevant_context(self, prompt: str) -> Tuple[Optional[str], List[Dict]]:
        """
        Get relevant context for a prompt, if any.

        Args:
            prompt: The user's prompt/query

        Returns:
            (context_string, matched_docs) where context_string is None if no relevant docs
        """
        if not self.enabled:
            return None, []

        # Skip very short prompts (likely not meaningful queries)
        if len(prompt.strip()) < 10:
            self._log(f"Prompt too short ({len(prompt.strip())} chars), skipping memory")
            return None, []

        self._log(f"Querying memory for: {prompt[:100]}...")

        # Query the index
        results = self._query_via_subprocess(prompt, top_k=5)

        if not results:
            self._log("No results from memory")
            return None, []

        # Filter by relevance threshold
        relevant = [doc for doc in results if doc.get('score', 0) >= self.relevance_threshold]

        if not relevant:
            self._log(f"No docs above threshold {self.relevance_threshold} (best: {results[0].get('score', 0):.3f})")
            return None, []

        self._log(f"Found {len(relevant)} relevant docs (best score: {relevant[0].get('score', 0):.3f})")

        # Build context string
        context_parts = []
        total_chars = 0

        for i, doc in enumerate(relevant[:MAX_CONTEXT_DOCS]):
            content = doc.get('content', '')[:800]  # Limit each doc
            source = doc.get('relative_path', doc.get('source', 'unknown'))
            doc_type = doc.get('type', 'unknown')
            score = doc.get('score', 0)

            # Only add if we have room
            if total_chars + len(content) > MAX_CONTEXT_CHARS:
                break

            context_parts.append(f"[{doc_type}] {source} (relevance: {score:.2f}):\n{content}")
            total_chars += len(content)

        if not context_parts:
            return None, []

        context = "## Relevant Context from Memory\n\n" + "\n\n---\n\n".join(context_parts)

        return context, relevant

    def enhance_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Enhance system prompt with relevant memory context.

        Only adds context if it's relevant to the user's prompt.

        Args:
            system_prompt: Original system prompt
            user_prompt: User's task/query

        Returns:
            Enhanced system prompt (or original if no relevant context)
        """
        context, docs = self.get_relevant_context(user_prompt)

        if context is None:
            return system_prompt

        # Prepend context to system prompt
        enhanced = f"{context}\n\n---\n\n{system_prompt}"

        self._log(f"Enhanced prompt with {len(docs)} memory docs")

        return enhanced


def check_memory_available() -> bool:
    """Check if the memory system is available and has data."""
    venv_python = Path.home() / '.venvs' / 'chromadb-env' / 'bin' / 'python'
    if not venv_python.exists():
        return False

    persist_dir = Path.home() / '.cache' / 'multi_db_agent' / 'home_index'
    if not persist_dir.exists():
        return False

    return True


# Singleton instance for easy access
_default_provider: Optional[MemoryProvider] = None


def get_memory_provider(verbose: bool = False) -> MemoryProvider:
    """Get or create the default memory provider."""
    global _default_provider

    if _default_provider is None:
        _default_provider = MemoryProvider(verbose=verbose)

    return _default_provider
