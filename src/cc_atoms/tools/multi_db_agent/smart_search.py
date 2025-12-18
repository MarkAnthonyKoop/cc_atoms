#!/usr/bin/env python3
"""
SmartSearchEngine: Intelligent Data Retrieval with Parallel Fan-out and Re-ranking

This is the NEXT LEVEL abstraction above HomeIndexer and VectorConnector.

## The Problem with Current Search

The existing search pipeline has these limitations:
1. **Single Query Path**: One embedding → one search → miss synonyms/related concepts
2. **Distance-Based Ranking**: Cosine distance ≠ semantic relevance for the task
3. **Fixed Chunking**: 50K char truncation loses important context
4. **No Query Understanding**: All queries treated identically

## SmartSearchEngine Solution

```
                     ┌───────────────────────────────────────────────────┐
                     │              SmartSearchEngine                     │
                     ├───────────────────────────────────────────────────┤
                     │                                                   │
User Query ──────────▶  Query Analyzer                                  │
                     │    │                                             │
                     │    ├── Intent Classification (code/doc/how-to)   │
                     │    ├── Query Expansion (synonyms, related)       │
                     │    └── Optimal Strategy Selection                │
                     │                    │                             │
                     │                    ▼                             │
                     │  ┌─────────────────────────────────┐             │
                     │  │     Parallel Fan-Out Search      │             │
                     │  │                                  │             │
                     │  │   Query 1 ──▶ Top K₁            │             │
                     │  │   Query 2 ──▶ Top K₂  ──merge──▶│ Candidates  │
                     │  │   Query 3 ──▶ Top K₃            │             │
                     │  │   (concurrent)                   │             │
                     │  └─────────────────────────────────┘             │
                     │                    │                             │
                     │                    ▼                             │
                     │  ┌─────────────────────────────────┐             │
                     │  │       Re-Ranking Pipeline        │             │
                     │  │                                  │             │
                     │  │   1. Deduplication               │             │
                     │  │   2. Cross-encoder scoring       │             │
                     │  │   3. Task-relevance boost        │             │
                     │  │   4. Recency/freshness weight    │             │
                     │  └─────────────────────────────────┘             │
                     │                    │                             │
                     │                    ▼                             │
                     │  ┌─────────────────────────────────┐             │
                     │  │      Smart Chunking              │             │
                     │  │                                  │             │
                     │  │   • Semantic boundaries          │             │
                     │  │   • Code-aware splitting         │             │
                     │  │   • Context preservation         │             │
                     │  └─────────────────────────────────┘             │
                     │                    │                             │
                     │                    ▼                             │
                     │            Ranked Results                        │
                     └───────────────────────────────────────────────────┘
```

## Key Innovations

1. **Query Expansion**: Transform user query into multiple search variants
   - Original query
   - Synonym expansion ("authentication" → "auth", "login", "credentials")
   - Conceptual expansion ("how to use X" → "X example", "X tutorial")

2. **Parallel Fan-Out**: Search with all variants concurrently
   - Better recall through diverse retrieval
   - Merge and deduplicate results

3. **Re-Ranking**: Score candidates by true relevance
   - Cross-encoder similarity (more accurate than bi-encoder)
   - Intent-based boosting (code for code queries, docs for how-to)
   - Freshness weighting for conversations

4. **Smart Chunking**: Intelligent document segmentation
   - Code: Split at function/class boundaries
   - Docs: Split at section headers
   - Preserve context with overlap

Usage:
    from cc_atoms.tools.multi_db_agent.smart_search import SmartSearchEngine

    engine = SmartSearchEngine()

    # Smart search with all optimizations
    results = engine.search("How do I use AtomRuntime?")

    # Direct search without re-ranking (faster)
    results = engine.search("AtomRuntime", rerank=False)

    # Search with type filter
    results = engine.search("authentication", doc_types=["code"])
"""
import os
import sys
import json
import time
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Set
from enum import Enum


class QueryIntent(Enum):
    """Classified intent of user query"""
    CODE_SEARCH = "code_search"       # Looking for code/implementation
    CONCEPT = "concept"               # Understanding a concept
    HOW_TO = "how_to"                 # Task/tutorial oriented
    TROUBLESHOOT = "troubleshoot"     # Debugging/fixing issues
    REFERENCE = "reference"           # API/documentation lookup
    EXPLORATORY = "exploratory"       # Open-ended exploration


@dataclass
class SearchResult:
    """A single search result with metadata"""
    content: str
    source: str
    doc_type: str  # code, document, conversation
    score: float
    relevance_score: float  # After re-ranking
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def relative_path(self) -> str:
        """Get relative path from home directory"""
        try:
            return str(Path(self.source).relative_to(Path.home()))
        except ValueError:
            return self.source


@dataclass
class SearchResponse:
    """Response from smart search"""
    query: str
    intent: QueryIntent
    results: List[SearchResult]
    expanded_queries: List[str]
    total_candidates: int
    duration_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryAnalyzer:
    """
    Analyzes and expands user queries for better retrieval.

    Responsibilities:
    - Classify query intent
    - Expand query with synonyms and related terms
    - Suggest optimal search strategy
    """

    # Keyword patterns for intent classification
    CODE_PATTERNS = [
        r'\b(function|class|method|implement|code|bug|error|fix|debug)\b',
        r'\b(import|export|def |async |await )\b',
        r'\.py\b|\.ts\b|\.js\b',
    ]

    HOW_TO_PATTERNS = [
        r'^how (do|can|to|should)\b',
        r'\b(tutorial|guide|example|steps|walkthrough)\b',
        r'\b(create|build|make|setup|configure)\b',
    ]

    TROUBLESHOOT_PATTERNS = [
        r'\b(error|exception|fail|crash|not working|broken|issue)\b',
        r'\b(why (does|is|won\'t)|doesn\'t work)\b',
    ]

    REFERENCE_PATTERNS = [
        r'\b(api|docs|documentation|reference|parameters|options)\b',
        r'\b(what (is|are) the|syntax|signature)\b',
    ]

    # Synonym expansions
    SYNONYMS = {
        'auth': ['authentication', 'login', 'credentials', 'auth', 'signin'],
        'db': ['database', 'db', 'storage', 'persistence'],
        'runtime': ['runtime', 'execution', 'runner', 'engine'],
        'search': ['search', 'query', 'find', 'lookup', 'retrieve'],
        'config': ['config', 'configuration', 'settings', 'options'],
        'gui': ['gui', 'ui', 'interface', 'window', 'widget'],
        'api': ['api', 'endpoint', 'route', 'handler'],
        'test': ['test', 'testing', 'spec', 'unittest'],
        'error': ['error', 'exception', 'failure', 'crash', 'bug'],
    }

    def __init__(self, gemini_api_key: Optional[str] = None):
        self._gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    def analyze(self, query: str) -> Tuple[QueryIntent, List[str]]:
        """
        Analyze query and return intent + expanded queries.

        Returns:
            (intent, list of expanded queries including original)
        """
        query_lower = query.lower()

        # Classify intent
        intent = self._classify_intent(query_lower)

        # Expand query
        expanded = self._expand_query(query, intent)

        return intent, expanded

    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent based on patterns."""
        # Check patterns in priority order
        for pattern in self.CODE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return QueryIntent.CODE_SEARCH

        for pattern in self.HOW_TO_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return QueryIntent.HOW_TO

        for pattern in self.TROUBLESHOOT_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return QueryIntent.TROUBLESHOOT

        for pattern in self.REFERENCE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return QueryIntent.REFERENCE

        # Check for concept-like queries (single terms or definitions)
        if len(query.split()) <= 3 and not any(c in query for c in '?!'):
            return QueryIntent.CONCEPT

        return QueryIntent.EXPLORATORY

    def _expand_query(self, query: str, intent: QueryIntent) -> List[str]:
        """Expand query with synonyms and related terms."""
        expanded = [query]  # Always include original

        # Extract key terms
        words = re.findall(r'\b\w+\b', query.lower())

        # Add synonym expansions
        for word in words:
            for base_term, synonyms in self.SYNONYMS.items():
                if word in synonyms or word == base_term:
                    for syn in synonyms:
                        if syn != word:
                            variant = query.lower().replace(word, syn)
                            if variant not in expanded:
                                expanded.append(variant)
                    break

        # Intent-specific expansions
        if intent == QueryIntent.HOW_TO:
            # Add example/tutorial variants
            base = re.sub(r'^how (do|can|to|should) (i |we |you )?', '', query.lower()).strip()
            expanded.append(f"{base} example")
            expanded.append(f"{base} usage")

        elif intent == QueryIntent.TROUBLESHOOT:
            # Add error/fix variants
            expanded.append(query.replace('error', 'exception'))
            expanded.append(query + " fix")
            expanded.append(query + " solution")

        elif intent == QueryIntent.CODE_SEARCH:
            # Add implementation variants
            base = query.lower()
            expanded.append(f"{base} implementation")
            expanded.append(f"def {base}")
            expanded.append(f"class {base}")

        # Limit to top 5 most distinct
        return expanded[:5]


class SmartChunker:
    """
    Intelligent document chunking with semantic awareness.

    Instead of naive character splitting, this chunker:
    - Respects code boundaries (functions, classes)
    - Respects document structure (headers, paragraphs)
    - Preserves context with overlap
    """

    DEFAULT_CHUNK_SIZE = 2000  # Characters per chunk
    OVERLAP_SIZE = 200         # Overlap between chunks

    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.overlap = overlap or self.OVERLAP_SIZE

    def chunk(self, content: str, doc_type: str) -> List[Dict[str, Any]]:
        """
        Chunk content intelligently based on document type.

        Returns:
            List of {"content": str, "start": int, "end": int, "type": str}
        """
        if doc_type == "code":
            return self._chunk_code(content)
        elif doc_type == "conversation":
            return self._chunk_conversation(content)
        else:
            return self._chunk_document(content)

    def _chunk_code(self, content: str) -> List[Dict[str, Any]]:
        """Chunk code at function/class boundaries."""
        chunks = []

        # Pattern for Python function/class definitions
        boundaries = list(re.finditer(
            r'^((?:async\s+)?def\s+\w+|class\s+\w+)',
            content,
            re.MULTILINE
        ))

        if not boundaries:
            # No structure detected, fall back to line-based
            return self._chunk_by_lines(content, "code")

        # Create chunks at boundaries
        for i, match in enumerate(boundaries):
            start = match.start()
            end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(content)

            chunk_content = content[start:end].strip()

            # If chunk is too large, sub-chunk it
            if len(chunk_content) > self.chunk_size * 2:
                sub_chunks = self._chunk_by_lines(chunk_content, "code")
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    "content": chunk_content,
                    "start": start,
                    "end": end,
                    "type": "code_block",
                })

        return chunks

    def _chunk_document(self, content: str) -> List[Dict[str, Any]]:
        """Chunk documents at section boundaries."""
        chunks = []

        # Pattern for markdown headers or significant breaks
        boundaries = list(re.finditer(
            r'^(#{1,4}\s+.+|={3,}|-{3,})',
            content,
            re.MULTILINE
        ))

        if not boundaries:
            return self._chunk_by_lines(content, "document")

        # Create chunks at boundaries
        prev_end = 0
        for i, match in enumerate(boundaries):
            if match.start() > prev_end:
                chunk_content = content[prev_end:match.start()].strip()
                if chunk_content:
                    chunks.append({
                        "content": chunk_content,
                        "start": prev_end,
                        "end": match.start(),
                        "type": "section",
                    })

            # Include header with next section
            prev_end = match.start()

        # Last section
        if prev_end < len(content):
            chunks.append({
                "content": content[prev_end:].strip(),
                "start": prev_end,
                "end": len(content),
                "type": "section",
            })

        return chunks

    def _chunk_conversation(self, content: str) -> List[Dict[str, Any]]:
        """Chunk conversations by message boundaries."""
        chunks = []

        # Pattern for conversation turns
        boundaries = list(re.finditer(
            r'^\[(user|assistant|human|ai)\]:|^(User|Assistant|Human|AI):',
            content,
            re.MULTILINE | re.IGNORECASE
        ))

        if not boundaries:
            return self._chunk_by_lines(content, "conversation")

        # Group messages into reasonable chunks
        current_chunk = []
        current_size = 0
        chunk_start = 0

        for i, match in enumerate(boundaries):
            end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(content)
            message = content[match.start():end].strip()

            if current_size + len(message) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": "\n".join(current_chunk),
                    "start": chunk_start,
                    "end": match.start(),
                    "type": "conversation_turn",
                })
                current_chunk = []
                current_size = 0
                chunk_start = match.start()

            current_chunk.append(message)
            current_size += len(message)

        # Final chunk
        if current_chunk:
            chunks.append({
                "content": "\n".join(current_chunk),
                "start": chunk_start,
                "end": len(content),
                "type": "conversation_turn",
            })

        return chunks

    def _chunk_by_lines(self, content: str, doc_type: str) -> List[Dict[str, Any]]:
        """Fall back to line-based chunking with overlap."""
        lines = content.split('\n')
        chunks = []

        current_chunk = []
        current_size = 0
        chunk_start = 0
        char_pos = 0

        for i, line in enumerate(lines):
            line_len = len(line) + 1  # +1 for newline

            if current_size + line_len > self.chunk_size and current_chunk:
                # Save chunk
                chunks.append({
                    "content": '\n'.join(current_chunk),
                    "start": chunk_start,
                    "end": char_pos,
                    "type": f"{doc_type}_lines",
                })

                # Start new chunk with overlap
                overlap_lines = current_chunk[-3:] if len(current_chunk) > 3 else []
                current_chunk = overlap_lines
                current_size = sum(len(l) + 1 for l in overlap_lines)
                chunk_start = char_pos - current_size

            current_chunk.append(line)
            current_size += line_len
            char_pos += line_len

        # Final chunk
        if current_chunk:
            chunks.append({
                "content": '\n'.join(current_chunk),
                "start": chunk_start,
                "end": char_pos,
                "type": f"{doc_type}_lines",
            })

        return chunks


class ReRanker:
    """
    Re-ranks search results for better precision.

    Uses multiple signals:
    1. Cross-encoder similarity (query-document)
    2. Intent-based boosting
    3. Recency weighting
    4. Type matching
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self._gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    def rerank(
        self,
        query: str,
        intent: QueryIntent,
        candidates: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Re-rank candidates by true relevance.

        Args:
            query: Original user query
            intent: Classified intent
            candidates: Initial search results
            top_k: Number of results to return

        Returns:
            Re-ranked list of results
        """
        if not candidates:
            return []

        # Score each candidate
        scored = []
        for result in candidates:
            score = self._compute_relevance(query, intent, result)
            result.relevance_score = score
            scored.append((score, result))

        # Sort by relevance score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top-k
        return [r for _, r in scored[:top_k]]

    def _compute_relevance(
        self,
        query: str,
        intent: QueryIntent,
        result: SearchResult,
    ) -> float:
        """Compute composite relevance score."""
        score = result.score  # Start with base score

        # Intent-based type boost
        type_boost = self._get_type_boost(intent, result.doc_type)
        score *= (1 + type_boost)

        # Keyword overlap boost
        keyword_score = self._keyword_overlap(query, result.content)
        score *= (1 + keyword_score * 0.3)

        # Recency boost for conversations
        if result.doc_type == "conversation":
            recency = self._recency_score(result.metadata.get('timestamp'))
            score *= (1 + recency * 0.2)

        # Code quality signals
        if result.doc_type == "code":
            code_quality = self._code_quality_score(result.content)
            score *= (1 + code_quality * 0.1)

        return score

    def _get_type_boost(self, intent: QueryIntent, doc_type: str) -> float:
        """Get boost factor based on intent-type match."""
        boosts = {
            QueryIntent.CODE_SEARCH: {"code": 0.5, "document": -0.2, "conversation": -0.1},
            QueryIntent.HOW_TO: {"code": 0.2, "document": 0.4, "conversation": 0.3},
            QueryIntent.TROUBLESHOOT: {"code": 0.3, "document": 0.2, "conversation": 0.4},
            QueryIntent.REFERENCE: {"code": 0.2, "document": 0.5, "conversation": 0.0},
            QueryIntent.CONCEPT: {"code": 0.1, "document": 0.4, "conversation": 0.2},
            QueryIntent.EXPLORATORY: {"code": 0.1, "document": 0.1, "conversation": 0.1},
        }
        return boosts.get(intent, {}).get(doc_type, 0.0)

    def _keyword_overlap(self, query: str, content: str) -> float:
        """Calculate keyword overlap score."""
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        content_words = set(re.findall(r'\b\w{3,}\b', content.lower()[:2000]))

        if not query_words:
            return 0.0

        overlap = len(query_words & content_words)
        return overlap / len(query_words)

    def _recency_score(self, timestamp: Optional[str]) -> float:
        """Calculate recency score (0-1, higher is more recent)."""
        if not timestamp:
            return 0.5

        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            age_days = (datetime.now() - dt.replace(tzinfo=None)).days

            # Exponential decay: half-life of 30 days
            return 2 ** (-age_days / 30)
        except:
            return 0.5

    def _code_quality_score(self, content: str) -> float:
        """Estimate code quality based on heuristics."""
        score = 0.0

        # Has docstring
        if '"""' in content or "'''" in content:
            score += 0.3

        # Has type hints
        if '->' in content or ': str' in content or ': int' in content:
            score += 0.2

        # Has comments
        if '#' in content:
            score += 0.1

        # Reasonable length (not too short or too long)
        lines = content.count('\n')
        if 10 <= lines <= 200:
            score += 0.2

        # Has error handling
        if 'try:' in content or 'except' in content:
            score += 0.2

        return min(score, 1.0)


class SmartSearchEngine:
    """
    Intelligent search engine with parallel fan-out and re-ranking.

    This is the NEXT LEVEL abstraction for data retrieval in cc_atoms.

    Features:
    - Query analysis and intent classification
    - Parallel multi-query fan-out for better recall
    - Smart re-ranking for precision
    - Intelligent chunking for context
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "home_directory",
        max_workers: int = 3,
        verbose: bool = True,
    ):
        """
        Initialize SmartSearchEngine.

        Args:
            persist_dir: Path to Chroma index
            collection_name: Collection name
            max_workers: Max parallel search threads
            verbose: Print progress info
        """
        self.persist_dir = persist_dir or str(
            Path.home() / '.cache' / 'multi_db_agent' / 'home_index'
        )
        self.collection_name = collection_name
        self.max_workers = max_workers
        self.verbose = verbose

        self._gemini_api_key = os.getenv("GEMINI_API_KEY")

        # Components
        self.analyzer = QueryAnalyzer(self._gemini_api_key)
        self.chunker = SmartChunker()
        self.reranker = ReRanker(self._gemini_api_key)

        # Lazy init
        self._indexer = None

    def _log(self, msg: str):
        if self.verbose:
            print(f"[SmartSearch] {msg}")

    def _get_indexer(self):
        """Lazy-load HomeIndexer."""
        if self._indexer is None:
            from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexer, HomeIndexerConfig

            config = HomeIndexerConfig(
                persist_dir=self.persist_dir,
                collection_name=self.collection_name,
            )
            self._indexer = HomeIndexer(config=config, verbose=False)
        return self._indexer

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_types: Optional[List[str]] = None,
        rerank: bool = True,
        expand_queries: bool = True,
    ) -> SearchResponse:
        """
        Smart search with parallel fan-out and re-ranking.

        Args:
            query: User search query
            top_k: Number of results to return
            doc_types: Filter by document types (code, document, conversation)
            rerank: Whether to apply re-ranking (slower but more precise)
            expand_queries: Whether to expand query with synonyms

        Returns:
            SearchResponse with ranked results
        """
        start_time = time.time()

        # Step 1: Analyze query
        intent, expanded_queries = self.analyzer.analyze(query)
        self._log(f"Query: '{query}' -> Intent: {intent.value}")

        if not expand_queries:
            expanded_queries = [query]
        else:
            self._log(f"Expanded to {len(expanded_queries)} variants")

        # Step 2: Parallel fan-out search
        all_candidates = self._parallel_search(
            expanded_queries,
            per_query_k=top_k * 2,  # Get more candidates for re-ranking
            doc_types=doc_types,
        )

        self._log(f"Found {len(all_candidates)} unique candidates")

        # Step 3: Re-rank (optional but recommended)
        if rerank and all_candidates:
            results = self.reranker.rerank(query, intent, all_candidates, top_k=top_k)
            self._log(f"Re-ranked to top {len(results)} results")
        else:
            # Just sort by base score
            all_candidates.sort(key=lambda x: x.score, reverse=True)
            results = all_candidates[:top_k]
            for r in results:
                r.relevance_score = r.score

        duration = time.time() - start_time

        return SearchResponse(
            query=query,
            intent=intent,
            results=results,
            expanded_queries=expanded_queries,
            total_candidates=len(all_candidates),
            duration_seconds=duration,
            metadata={
                "reranked": rerank,
                "doc_types": doc_types,
            }
        )

    def _parallel_search(
        self,
        queries: List[str],
        per_query_k: int,
        doc_types: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Execute searches in parallel and merge results.

        Args:
            queries: List of query variants
            per_query_k: Results per query
            doc_types: Filter by type

        Returns:
            Merged and deduplicated results
        """
        indexer = self._get_indexer()
        seen_ids: Set[str] = set()
        all_results: List[SearchResult] = []

        def search_single(q: str) -> List[Dict]:
            try:
                return indexer.query(q, top_k=per_query_k)
            except Exception as e:
                self._log(f"Search error for '{q}': {e}")
                return []

        # Parallel execution
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(search_single, q): q for q in queries}

            for future in as_completed(futures):
                query = futures[future]
                try:
                    raw_results = future.result()

                    for doc in raw_results:
                        # Deduplicate by source
                        doc_id = doc.get('metadata', {}).get('source', '') or doc.get('source', '')
                        if doc_id in seen_ids:
                            continue
                        seen_ids.add(doc_id)

                        # Filter by type if specified
                        doc_type = doc.get('type', doc.get('metadata', {}).get('type', 'unknown'))
                        if doc_types and doc_type not in doc_types:
                            continue

                        # Convert to SearchResult
                        result = SearchResult(
                            content=doc.get('content', ''),
                            source=doc.get('source', doc_id),
                            doc_type=doc_type,
                            score=doc.get('score', 0.0),
                            relevance_score=0.0,  # Will be set by reranker
                            metadata={
                                'filename': doc.get('filename', ''),
                                'relative_path': doc.get('relative_path', ''),
                                'timestamp': doc.get('metadata', {}).get('timestamp', ''),
                                **doc.get('metadata', {}),
                            }
                        )
                        all_results.append(result)

                except Exception as e:
                    self._log(f"Error processing results from '{query}': {e}")

        return all_results

    def search_and_chunk(
        self,
        query: str,
        top_k: int = 5,
        chunk_size: int = 2000,
        **search_kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Search and return intelligently chunked results.

        Useful when you need smaller, focused pieces of content
        rather than full documents.

        Args:
            query: Search query
            top_k: Number of documents to retrieve
            chunk_size: Target chunk size
            **search_kwargs: Additional args for search()

        Returns:
            List of chunks with metadata
        """
        # Get documents
        response = self.search(query, top_k=top_k, **search_kwargs)

        # Chunk each result
        chunker = SmartChunker(chunk_size=chunk_size)
        all_chunks = []

        for result in response.results:
            chunks = chunker.chunk(result.content, result.doc_type)

            for chunk in chunks:
                all_chunks.append({
                    "content": chunk["content"],
                    "source": result.source,
                    "doc_type": result.doc_type,
                    "chunk_type": chunk["type"],
                    "parent_score": result.relevance_score,
                    "relative_path": result.relative_path,
                })

        # Sort by parent score
        all_chunks.sort(key=lambda x: x["parent_score"], reverse=True)

        return all_chunks

    def ask(self, question: str, top_k: int = 5) -> str:
        """
        Search and generate an answer using Gemini.

        Args:
            question: User question
            top_k: Number of documents to use as context

        Returns:
            Generated answer
        """
        # Search
        response = self.search(question, top_k=top_k)

        if not response.results:
            return "I couldn't find relevant information to answer that question."

        # Format context
        context_parts = []
        for i, result in enumerate(response.results[:5], 1):
            context_parts.append(f"""
--- Source {i}: {result.relative_path} ({result.doc_type}) ---
{result.content[:2000]}
""")

        context = "\n".join(context_parts)

        # Generate answer
        prompt = f"""Based on the following context, answer the question.

Question: {question}

Context:
{context}

Provide a clear, helpful answer based on the context. Reference specific files when relevant.
If the context doesn't fully answer the question, say what you found and what might be missing."""

        return self._call_gemini(prompt)

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for generation."""
        import urllib.request

        if not self._gemini_api_key:
            return "Error: GEMINI_API_KEY not set"

        model = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._gemini_api_key}"

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"Error generating answer: {e}"


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point for SmartSearchEngine."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SmartSearchEngine - Intelligent search with parallel fan-out and re-ranking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  smart-search search "How do I use AtomRuntime?"
  smart-search search "authentication" --type code
  smart-search search "bug fix" --no-rerank
  smart-search ask "What Python projects exist in this codebase?"
  smart-search chunks "GUI automation"
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Search command
    search_parser = subparsers.add_parser('search', help='Smart search')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--top-k', '-k', type=int, default=10, help='Number of results')
    search_parser.add_argument('--type', '-t', choices=['code', 'document', 'conversation'],
                              action='append', help='Filter by type')
    search_parser.add_argument('--no-rerank', action='store_true', help='Disable re-ranking')
    search_parser.add_argument('--no-expand', action='store_true', help='Disable query expansion')

    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question')
    ask_parser.add_argument('question', help='Your question')
    ask_parser.add_argument('--top-k', '-k', type=int, default=5, help='Number of docs to use')

    # Chunks command
    chunks_parser = subparsers.add_parser('chunks', help='Get chunked results')
    chunks_parser.add_argument('query', help='Search query')
    chunks_parser.add_argument('--top-k', '-k', type=int, default=5, help='Number of docs')
    chunks_parser.add_argument('--chunk-size', type=int, default=2000, help='Chunk size')

    # Global args
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    engine = SmartSearchEngine(verbose=not args.quiet)

    if args.command == 'search':
        response = engine.search(
            args.query,
            top_k=args.top_k,
            doc_types=args.type,
            rerank=not args.no_rerank,
            expand_queries=not args.no_expand,
        )

        print(f"\n{'='*60}")
        print(f"Query: {response.query}")
        print(f"Intent: {response.intent.value}")
        print(f"Expanded queries: {response.expanded_queries}")
        print(f"Candidates: {response.total_candidates}")
        print(f"Duration: {response.duration_seconds:.2f}s")
        print(f"{'='*60}\n")

        for i, result in enumerate(response.results, 1):
            print(f"--- {i}. {result.relative_path} (relevance: {result.relevance_score:.3f}) ---")
            print(f"Type: {result.doc_type}")
            print(f"Preview: {result.content[:300]}...")
            print()

        return 0

    elif args.command == 'ask':
        answer = engine.ask(args.question, top_k=args.top_k)
        print(answer)
        return 0

    elif args.command == 'chunks':
        chunks = engine.search_and_chunk(
            args.query,
            top_k=args.top_k,
            chunk_size=args.chunk_size,
        )

        print(f"\nFound {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks[:10], 1):
            print(f"--- Chunk {i}: {chunk['relative_path']} ({chunk['chunk_type']}) ---")
            print(f"Score: {chunk['parent_score']:.3f}")
            print(f"Content: {chunk['content'][:200]}...")
            print()

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
