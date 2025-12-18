#!/usr/bin/env python3
"""
Home Oracle - Your Personal Knowledge Agent

An autonomous retrieval-augmented agent that uses your entire home directory
as its knowledge base. It combines semantic search with iterative reasoning
to provide accurate, contextual answers.

Usage:
    home_oracle "What is the architecture of cc_atoms?"
    home_oracle --quick "Where is AtomRuntime defined?"
    home_oracle -v "How do I create a new atom tool?"

Architecture:
    User Prompt → Intent Analysis → Query Planning → Iterative Retrieval → Synthesis → Answer
"""
import os
import sys
import json
import argparse
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class OracleConfig:
    """Configuration for Home Oracle."""

    # Search settings
    index_path: str = field(default_factory=lambda: str(
        Path.home() / '.cache' / 'multi_db_agent' / 'home_index'
    ))
    collection_name: str = 'home_directory'

    # Retrieval settings
    max_search_iterations: int = 5
    initial_top_k: int = 10
    refinement_top_k: int = 5
    confidence_threshold: float = 0.7  # Stop iterating when confident

    # Generation settings
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY'))
    generation_model: str = 'gemini-2.0-flash'
    embedding_model: str = 'text-embedding-004'

    # Output settings
    max_context_chars: int = 30000
    verbose: bool = False


# =============================================================================
# CORE CLASSES
# =============================================================================

@dataclass
class SearchResult:
    """A single search result."""
    content: str
    source: str
    doc_type: str
    score: float
    relative_path: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalState:
    """Tracks state across retrieval iterations."""
    original_query: str
    gathered_context: List[SearchResult] = field(default_factory=list)
    queries_executed: List[str] = field(default_factory=list)
    seen_sources: set = field(default_factory=set)
    iteration: int = 0
    confidence: float = 0.0
    reasoning_log: List[str] = field(default_factory=list)

    def add_results(self, query: str, results: List[SearchResult]):
        """Add new results, deduplicating by source."""
        self.queries_executed.append(query)
        new_count = 0
        for r in results:
            if r.source not in self.seen_sources:
                self.gathered_context.append(r)
                self.seen_sources.add(r.source)
                new_count += 1
        return new_count

    def get_context_summary(self) -> str:
        """Get summary of gathered context for reasoning."""
        parts = []
        for i, r in enumerate(self.gathered_context[:20], 1):
            parts.append(f"{i}. [{r.doc_type}] {r.relative_path or r.source} (score: {r.score:.2f})")
        return '\n'.join(parts)


class OracleSearch:
    """
    Search interface for Home Oracle.

    Wraps the SmartSearchEngine (if available) or falls back to direct
    Chroma queries with Gemini embeddings.
    """

    def __init__(self, config: OracleConfig):
        self.config = config
        self._search_engine = None
        self._indexer = None
        self._init_search()

    def _init_search(self):
        """Initialize search backend."""
        # Try to use SmartSearchEngine if available
        try:
            sys.path.insert(0, str(Path.home() / 'claude' / 'cc' / 'src'))
            from cc_atoms.tools.multi_db_agent.smart_search import SmartSearchEngine
            self._search_engine = SmartSearchEngine(
                persist_dir=self.config.index_path,
                collection_name=self.config.collection_name,
                verbose=self.config.verbose
            )
            if self.config.verbose:
                print("[Oracle] Using SmartSearchEngine for retrieval")
            return
        except ImportError as e:
            if self.config.verbose:
                print(f"[Oracle] SmartSearchEngine not available: {e}")

        # Fallback to HomeIndexer
        try:
            from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexer, HomeIndexerConfig
            index_config = HomeIndexerConfig(
                persist_dir=self.config.index_path,
                collection_name=self.config.collection_name,
            )
            self._indexer = HomeIndexer(config=index_config, verbose=self.config.verbose)
            if self.config.verbose:
                print("[Oracle] Using HomeIndexer for retrieval")
        except ImportError:
            # Final fallback: direct Chroma + Gemini
            if self.config.verbose:
                print("[Oracle] Using direct Chroma queries")

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_types: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Execute search and return results.

        Args:
            query: Search query
            top_k: Number of results
            doc_types: Filter by type ('code', 'document', 'conversation')

        Returns:
            List of SearchResult objects
        """
        results = []

        if self._search_engine:
            # Use SmartSearchEngine (best)
            response = self._search_engine.search(
                query,
                top_k=top_k,
                doc_types=doc_types,
                rerank=True,
                expand_queries=True
            )
            for r in response.results:
                results.append(SearchResult(
                    content=r.content,
                    source=r.source,
                    doc_type=r.doc_type,
                    score=r.relevance_score,
                    relative_path=r.relative_path,
                    metadata=r.metadata
                ))

        elif self._indexer:
            # Use HomeIndexer directly
            raw_results = self._indexer.query(query, top_k=top_k)
            for r in raw_results:
                doc_type = r.get('type', r.get('metadata', {}).get('type', 'unknown'))
                if doc_types and doc_type not in doc_types:
                    continue
                results.append(SearchResult(
                    content=r.get('content', ''),
                    source=r.get('source', ''),
                    doc_type=doc_type,
                    score=r.get('score', 0.0),
                    relative_path=r.get('relative_path', ''),
                    metadata=r.get('metadata', {})
                ))

        else:
            # Direct Chroma (last resort)
            results = self._direct_chroma_search(query, top_k, doc_types)

        return results

    def _direct_chroma_search(
        self,
        query: str,
        top_k: int,
        doc_types: Optional[List[str]]
    ) -> List[SearchResult]:
        """Direct Chroma search without SmartSearchEngine."""
        try:
            import chromadb
        except ImportError:
            print("Error: chromadb not installed. Run: pip install chromadb")
            return []

        # Connect to Chroma
        client = chromadb.PersistentClient(path=self.config.index_path)
        try:
            collection = client.get_collection(name=self.config.collection_name)
        except Exception as e:
            print(f"Error: Collection not found. Run home-indexer first: {e}")
            return []

        # Get query embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []

        # Query
        raw_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )

        results = []
        if raw_results['documents'] and raw_results['documents'][0]:
            for i, doc in enumerate(raw_results['documents'][0]):
                metadata = raw_results['metadatas'][0][i] if raw_results['metadatas'] else {}
                distance = raw_results['distances'][0][i] if raw_results['distances'] else 0

                doc_type = metadata.get('type', 'unknown')
                if doc_types and doc_type not in doc_types:
                    continue

                results.append(SearchResult(
                    content=doc,
                    source=metadata.get('source', ''),
                    doc_type=doc_type,
                    score=1 - distance,  # Convert distance to similarity
                    relative_path=metadata.get('relative_path', ''),
                    metadata=metadata
                ))

        return results

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using Gemini."""
        if not self.config.gemini_api_key:
            print("Error: GEMINI_API_KEY not set")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.embedding_model}:embedContent?key={self.config.gemini_api_key}"

        payload = json.dumps({
            "model": f"models/{self.config.embedding_model}",
            "content": {"parts": [{"text": text[:8000]}]}
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("embedding", {}).get("values", None)
        except Exception as e:
            print(f"Embedding error: {e}")
            return None


class OracleAgent:
    """
    The core Oracle agent that performs iterative retrieval and synthesis.

    This is the brain of Home Oracle. It:
    1. Analyzes the user's intent
    2. Plans what to search for
    3. Iteratively retrieves until confident
    4. Synthesizes a comprehensive answer
    """

    def __init__(self, config: Optional[OracleConfig] = None):
        self.config = config or OracleConfig()
        self.search = OracleSearch(self.config)

    def _log(self, msg: str):
        if self.config.verbose:
            print(f"[Oracle] {msg}")

    def ask(self, question: str, quick: bool = False) -> Dict[str, Any]:
        """
        Ask a question and get a comprehensive answer.

        Args:
            question: User's question
            quick: If True, do single search (faster but less thorough)

        Returns:
            {
                "answer": str,
                "sources": List[dict],
                "confidence": float,
                "queries_used": List[str],
                "iterations": int
            }
        """
        if quick:
            return self._quick_answer(question)
        else:
            return self._iterative_answer(question)

    def _quick_answer(self, question: str) -> Dict[str, Any]:
        """Quick single-search answer."""
        self._log(f"Quick mode: searching for '{question}'")

        results = self.search.search(question, top_k=self.config.initial_top_k)

        if not results:
            return {
                "answer": "I couldn't find relevant information to answer that question.",
                "sources": [],
                "confidence": 0.0,
                "queries_used": [question],
                "iterations": 1
            }

        # Build context and generate answer
        context = self._format_context(results[:5])
        answer = self._generate_answer(question, context)

        return {
            "answer": answer,
            "sources": [{"path": r.relative_path or r.source, "type": r.doc_type, "score": r.score} for r in results[:5]],
            "confidence": sum(r.score for r in results[:5]) / len(results[:5]) if results else 0,
            "queries_used": [question],
            "iterations": 1
        }

    def _iterative_answer(self, question: str) -> Dict[str, Any]:
        """
        Iterative retrieval with reasoning.

        This is the magic - the agent decides what to search for based on
        what it has found so far.
        """
        state = RetrievalState(original_query=question)

        # Initial search
        self._log(f"Starting iterative retrieval for: '{question}'")
        initial_results = self.search.search(question, top_k=self.config.initial_top_k)
        state.add_results(question, initial_results)
        state.iteration = 1

        self._log(f"Initial search found {len(initial_results)} results")

        # Iterative refinement loop
        while state.iteration < self.config.max_search_iterations:
            # Analyze what we have and decide next step
            analysis = self._analyze_and_plan(state)

            state.confidence = analysis['confidence']
            state.reasoning_log.append(analysis['reasoning'])

            self._log(f"Iteration {state.iteration}: confidence={state.confidence:.2f}")
            self._log(f"Reasoning: {analysis['reasoning'][:100]}...")

            # Check if we're confident enough
            if state.confidence >= self.config.confidence_threshold:
                self._log("Confidence threshold met, generating answer")
                break

            # Check if we have follow-up queries
            if not analysis.get('follow_up_queries'):
                self._log("No more queries to execute")
                break

            # Execute follow-up queries
            state.iteration += 1
            for follow_up in analysis['follow_up_queries'][:2]:  # Max 2 per iteration
                self._log(f"Executing follow-up: '{follow_up}'")
                new_results = self.search.search(follow_up, top_k=self.config.refinement_top_k)
                new_count = state.add_results(follow_up, new_results)
                self._log(f"Found {new_count} new unique results")

        # Generate final answer from all gathered context
        context = self._format_context(state.gathered_context[:15])  # Top 15 sources
        answer = self._generate_answer(question, context, state)

        return {
            "answer": answer,
            "sources": [
                {"path": r.relative_path or r.source, "type": r.doc_type, "score": r.score}
                for r in state.gathered_context[:10]
            ],
            "confidence": state.confidence,
            "queries_used": state.queries_executed,
            "iterations": state.iteration,
            "reasoning_log": state.reasoning_log
        }

    def _analyze_and_plan(self, state: RetrievalState) -> Dict[str, Any]:
        """
        Use LLM to analyze current context and plan next queries.

        This is where the agent "thinks" about what it has found and
        what it still needs to find.
        """
        context_summary = state.get_context_summary()

        prompt = f"""You are analyzing search results to answer a question.

ORIGINAL QUESTION: {state.original_query}

SEARCHES EXECUTED SO FAR:
{chr(10).join(f"- {q}" for q in state.queries_executed)}

DOCUMENTS FOUND (top 20):
{context_summary}

TASK: Analyze the search results and determine:
1. How confident you are (0.0-1.0) that you have enough context to answer the question
2. What specific information is still missing
3. What follow-up searches would help fill the gaps

Respond in JSON format:
{{
    "confidence": 0.7,
    "reasoning": "Brief explanation of confidence level and what we have/need",
    "follow_up_queries": ["specific query 1", "specific query 2"]
}}

If confidence is high (>= 0.7), the follow_up_queries can be empty.
Be specific with follow-up queries - use filenames, function names, or technical terms from the context."""

        response = self._call_gemini(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response
            if '```' in response:
                json_str = response.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
                json_str = json_str.strip()

            result = json.loads(json_str)
            return {
                'confidence': float(result.get('confidence', 0.5)),
                'reasoning': result.get('reasoning', 'No reasoning provided'),
                'follow_up_queries': result.get('follow_up_queries', [])
            }
        except (json.JSONDecodeError, ValueError) as e:
            self._log(f"Failed to parse analysis response: {e}")
            return {
                'confidence': 0.5,
                'reasoning': response[:200],
                'follow_up_queries': []
            }

    def _format_context(self, results: List[SearchResult]) -> str:
        """Format search results as context for generation."""
        parts = []
        total_chars = 0

        for i, r in enumerate(results, 1):
            # Truncate content if needed
            content = r.content
            remaining = self.config.max_context_chars - total_chars - 500  # Buffer for formatting
            if len(content) > remaining:
                content = content[:remaining] + "...[truncated]"

            part = f"""
--- Source {i}: {r.relative_path or r.source} ({r.doc_type}, score: {r.score:.2f}) ---
{content}
"""
            parts.append(part)
            total_chars += len(part)

            if total_chars >= self.config.max_context_chars:
                break

        return '\n'.join(parts)

    def _generate_answer(
        self,
        question: str,
        context: str,
        state: Optional[RetrievalState] = None
    ) -> str:
        """Generate final answer using gathered context."""

        # Build meta-information about the search process
        meta = ""
        if state:
            meta = f"""
Search Process:
- Executed {len(state.queries_executed)} search queries
- Found {len(state.gathered_context)} unique documents
- Final confidence: {state.confidence:.0%}
"""

        prompt = f"""You are Home Oracle, a knowledgeable assistant with access to the user's home directory.
{meta}

QUESTION: {question}

RELEVANT CONTEXT FROM USER'S FILES:
{context}

INSTRUCTIONS:
1. Answer the question based on the context provided
2. Be specific and cite files when relevant (use relative paths like ~/claude/cc/...)
3. If the context partially answers the question, explain what was found and what might be missing
4. If code is involved, you can include brief snippets
5. Be concise but comprehensive

Answer:"""

        return self._call_gemini(prompt)

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for generation."""
        if not self.config.gemini_api_key:
            return "Error: GEMINI_API_KEY not set"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.generation_model}:generateContent?key={self.config.gemini_api_key}"

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,  # Lower for more focused answers
                "maxOutputTokens": 4096,
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"Error generating answer: {e}"


# =============================================================================
# CLI
# =============================================================================

def main():
    """Command-line interface for Home Oracle."""
    parser = argparse.ArgumentParser(
        description="Home Oracle - Your Personal Knowledge Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  home_oracle "What is the architecture of cc_atoms?"
  home_oracle --quick "Where is AtomRuntime defined?"
  home_oracle -v "How do I create a new atom tool?"
  home_oracle --json "What Python projects do I have?"

The oracle searches your home directory index and provides accurate,
well-sourced answers using iterative retrieval.
        """
    )

    parser.add_argument('question', nargs='?', help='Your question')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='Quick mode: single search, faster but less thorough')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed search progress')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output as JSON')
    parser.add_argument('--max-iterations', '-i', type=int, default=5,
                       help='Maximum search iterations (default: 5)')
    parser.add_argument('--confidence', '-c', type=float, default=0.7,
                       help='Confidence threshold to stop iterating (default: 0.7)')

    args = parser.parse_args()

    if not args.question:
        parser.print_help()
        return 1

    # Check for API key
    if not os.getenv('GEMINI_API_KEY'):
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Get a free API key at: https://makersuite.google.com/app/apikey")
        return 1

    # Configure
    config = OracleConfig(
        max_search_iterations=args.max_iterations,
        confidence_threshold=args.confidence,
        verbose=args.verbose
    )

    # Create agent and ask
    agent = OracleAgent(config)
    result = agent.ask(args.question, quick=args.quick)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Pretty print
        print("\n" + "="*60)
        print("ANSWER")
        print("="*60 + "\n")
        print(result['answer'])

        print("\n" + "-"*60)
        print(f"Confidence: {result['confidence']:.0%}")
        print(f"Iterations: {result['iterations']}")
        print(f"Queries: {', '.join(result['queries_used'][:5])}")

        if result['sources']:
            print("\nSources:")
            for s in result['sources'][:5]:
                print(f"  • [{s['type']}] {s['path']} (score: {s['score']:.2f})")

        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
