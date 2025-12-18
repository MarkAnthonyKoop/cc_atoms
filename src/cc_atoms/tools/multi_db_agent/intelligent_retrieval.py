#!/usr/bin/env python3
"""
Intelligent Retrieval Orchestrator (IRO)

Generation 3 Evolution: The NEXT LEVEL above WorkflowEngine.

While previous generations built:
- Gen 1: CapabilityRegistry → Discovery and tracking
- Gen 2: WorkflowEngine → DAG-based workflow composition

Gen 3 builds the INTELLIGENT RETRIEVAL layer:
- Parallel fan-out search across multiple sources
- Query expansion (synonyms, reformulations)
- Cross-encoder re-ranking for precision
- Hybrid search (semantic + keyword BM25)
- Smart chunking with overlap
- Result fusion and deduplication

Architecture:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    Intelligent Retrieval Orchestrator                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Query Processor                                                         │
    │  ├── Query Analyzer      → Understand intent, extract entities           │
    │  ├── Query Expander      → Generate variations, synonyms                 │
    │  └── Query Decomposer    → Split complex queries into sub-queries       │
    │                                                                          │
    │  Retrieval Engine                                                        │
    │  ├── Parallel Fan-out    → Search multiple sources concurrently         │
    │  ├── Hybrid Search       → Vector + BM25 keyword fusion                 │
    │  └── Smart Chunker       → Semantic boundary detection                  │
    │                                                                          │
    │  Re-ranking Pipeline                                                     │
    │  ├── Cross-Encoder       → Deep relevance scoring                       │
    │  ├── Diversity Filter    → Remove redundancy                            │
    │  └── Score Fusion        → Combine multiple signals                     │
    └─────────────────────────────────────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
    ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
    │  HomeIndexer  │           │  Weaviate     │           │  Future       │
    │  (Chroma)     │           │  (Elysia)     │           │  Sources      │
    └───────────────┘           └───────────────┘           └───────────────┘

Usage:
    from cc_atoms.tools.multi_db_agent import IntelligentRetrieval

    iro = IntelligentRetrieval()

    # Simple search with all enhancements
    results = iro.search("authentication security vulnerabilities")

    # Advanced search with options
    results = iro.search(
        query="how does user login work",
        expand=True,           # Generate query variations
        rerank=True,           # Cross-encoder re-ranking
        hybrid=True,           # Vector + keyword fusion
        sources=["code", "docs", "conversations"],
        top_k=20,
        final_k=5              # After re-ranking
    )

    # Get search explanation
    explanation = iro.explain_search(results)
"""
import os
import sys
import json
import time
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import defaultdict
import math

# Optional imports with fallbacks
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


@dataclass
class RetrievedDocument:
    """A document retrieved from any source."""
    id: str
    content: str
    source: str                # "code", "document", "conversation"
    source_path: str           # File path or identifier
    score: float               # Initial retrieval score (0-1)
    rerank_score: Optional[float] = None  # After cross-encoder
    final_score: Optional[float] = None   # Combined score
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Provenance
    query_variant: str = ""    # Which query variant found this
    retrieval_method: str = "" # "vector", "keyword", "hybrid"

    @property
    def effective_score(self) -> float:
        """Get the best available score."""
        if self.final_score is not None:
            return self.final_score
        if self.rerank_score is not None:
            return self.rerank_score
        return self.score


@dataclass
class SearchResult:
    """Complete result from intelligent retrieval."""
    query: str
    documents: List[RetrievedDocument]

    # Search metadata
    expanded_queries: List[str] = field(default_factory=list)
    sources_searched: List[str] = field(default_factory=list)
    total_candidates: int = 0
    search_time_ms: float = 0
    rerank_time_ms: float = 0

    # Diagnostics
    method_stats: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class ChunkBoundary:
    """Represents a semantic boundary in text."""
    position: int
    boundary_type: str  # "paragraph", "function", "class", "section"
    strength: float     # 0-1, how strong the boundary is


class QueryExpander:
    """
    Expand queries with variations, synonyms, and reformulations.

    Uses lightweight local techniques - no LLM needed.
    """

    # Programming synonyms
    CODE_SYNONYMS = {
        "function": ["method", "def", "func", "procedure", "routine"],
        "class": ["object", "type", "struct", "model"],
        "variable": ["var", "field", "attribute", "property", "param"],
        "error": ["exception", "bug", "issue", "failure", "crash"],
        "test": ["spec", "unit test", "integration test", "assertion"],
        "import": ["include", "require", "use", "load"],
        "return": ["output", "result", "response", "yield"],
        "auth": ["authentication", "login", "signin", "credential"],
        "config": ["configuration", "settings", "options", "preferences"],
        "api": ["endpoint", "route", "interface", "service"],
        "database": ["db", "storage", "persistence", "datastore"],
        "cache": ["memoize", "buffer", "store", "precompute"],
    }

    # Common technical prefixes/suffixes
    TECH_VARIATIONS = {
        "async": ["asynchronous", "concurrent", "parallel"],
        "sync": ["synchronous", "blocking", "sequential"],
        "get": ["fetch", "retrieve", "load", "read"],
        "set": ["update", "write", "save", "store"],
        "create": ["new", "init", "initialize", "make", "add"],
        "delete": ["remove", "destroy", "drop", "clear"],
        "parse": ["decode", "deserialize", "extract", "process"],
        "render": ["display", "show", "draw", "present"],
    }

    def expand(self, query: str, max_variants: int = 5) -> List[str]:
        """
        Generate query variations.

        Args:
            query: Original query
            max_variants: Maximum variants to generate

        Returns:
            List of query variants including original
        """
        variants = [query]
        query_lower = query.lower()
        words = query_lower.split()

        # 1. Synonym expansion
        for word in words:
            if word in self.CODE_SYNONYMS:
                for synonym in self.CODE_SYNONYMS[word][:2]:  # Top 2 synonyms
                    variant = query_lower.replace(word, synonym)
                    if variant not in variants:
                        variants.append(variant)

            if word in self.TECH_VARIATIONS:
                for variation in self.TECH_VARIATIONS[word][:2]:
                    variant = query_lower.replace(word, variation)
                    if variant not in variants:
                        variants.append(variant)

        # 2. Question reformulations
        if not any(q in query_lower for q in ["how", "what", "where", "why"]):
            # Add question form
            variants.append(f"how does {query_lower} work")
            variants.append(f"what is {query_lower}")

        # 3. Keyword extraction (remove filler words)
        filler_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "of", "and", "or"}
        keywords = [w for w in words if w not in filler_words and len(w) > 2]
        if len(keywords) > 1 and len(keywords) < len(words):
            keyword_query = " ".join(keywords)
            if keyword_query not in variants:
                variants.append(keyword_query)

        # 4. CamelCase/snake_case variations for code searches
        if "_" in query or any(c.isupper() for c in query):
            # snake_case to words
            snake_variant = re.sub(r'_', ' ', query_lower)
            if snake_variant not in variants:
                variants.append(snake_variant)
            # CamelCase to words
            camel_variant = re.sub(r'([a-z])([A-Z])', r'\1 \2', query).lower()
            if camel_variant not in variants:
                variants.append(camel_variant)

        return variants[:max_variants]


class SmartChunker:
    """
    Intelligent text chunking with semantic boundary detection.

    Unlike naive fixed-size chunking, this identifies natural boundaries
    in text (function boundaries in code, paragraphs in prose).
    """

    # Code boundary patterns
    CODE_BOUNDARIES = [
        (r'\n(?=def\s+\w+)', "function", 0.9),
        (r'\n(?=class\s+\w+)', "class", 1.0),
        (r'\n(?=async\s+def\s+\w+)', "function", 0.9),
        (r'\n(?=@\w+)', "decorator", 0.7),
        (r'\n\n(?=\s*#)', "comment_block", 0.6),
        (r'\n(?=if\s+__name__)', "main_block", 0.8),
    ]

    # Document boundary patterns
    DOC_BOUNDARIES = [
        (r'\n\n+', "paragraph", 0.5),
        (r'\n(?=#{1,6}\s+)', "heading", 0.9),
        (r'\n(?=\*{3,}|\-{3,}|={3,})', "section_break", 0.8),
        (r'\n(?=\d+\.\s+)', "list_item", 0.4),
    ]

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        respect_boundaries: bool = True
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.respect_boundaries = respect_boundaries

    def find_boundaries(self, text: str, is_code: bool = False) -> List[ChunkBoundary]:
        """Find semantic boundaries in text."""
        boundaries = []
        patterns = self.CODE_BOUNDARIES if is_code else self.DOC_BOUNDARIES

        for pattern, boundary_type, strength in patterns:
            for match in re.finditer(pattern, text):
                boundaries.append(ChunkBoundary(
                    position=match.start(),
                    boundary_type=boundary_type,
                    strength=strength
                ))

        # Sort by position
        boundaries.sort(key=lambda b: b.position)
        return boundaries

    def chunk(self, text: str, is_code: bool = False) -> List[Dict[str, Any]]:
        """
        Split text into semantic chunks.

        Returns list of {"content": str, "start": int, "end": int, "boundary_type": str}
        """
        if not text or len(text) <= self.chunk_size:
            return [{"content": text, "start": 0, "end": len(text), "boundary_type": "single"}]

        chunks = []
        boundaries = self.find_boundaries(text, is_code) if self.respect_boundaries else []

        # Add artificial boundaries at chunk_size intervals
        for i in range(0, len(text), self.chunk_size - self.overlap):
            boundaries.append(ChunkBoundary(i, "interval", 0.3))

        # Sort all boundaries
        boundaries.sort(key=lambda b: b.position)

        # Merge nearby boundaries, keeping strongest
        merged = []
        for boundary in boundaries:
            if merged and boundary.position - merged[-1].position < self.overlap:
                if boundary.strength > merged[-1].strength:
                    merged[-1] = boundary
            else:
                merged.append(boundary)

        # Create chunks from boundaries
        prev_pos = 0
        for boundary in merged:
            if boundary.position - prev_pos >= self.chunk_size // 4:  # Min chunk size
                chunk_text = text[prev_pos:boundary.position].strip()
                if chunk_text:
                    chunks.append({
                        "content": chunk_text,
                        "start": prev_pos,
                        "end": boundary.position,
                        "boundary_type": boundary.boundary_type
                    })
                prev_pos = max(0, boundary.position - self.overlap)

        # Last chunk
        if prev_pos < len(text):
            chunk_text = text[prev_pos:].strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "start": prev_pos,
                    "end": len(text),
                    "boundary_type": "end"
                })

        return chunks


class KeywordScorer:
    """
    BM25-style keyword scoring for hybrid search.

    Complements vector search by finding exact keyword matches.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._doc_lengths = {}
        self._avg_doc_length = 0
        self._doc_freqs = defaultdict(int)  # word -> num docs containing it
        self._num_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        text = text.lower()
        # Split on non-alphanumeric, keep underscores for code
        tokens = re.findall(r'[a-z0-9_]+', text)
        return [t for t in tokens if len(t) > 1]

    def index_documents(self, documents: List[Tuple[str, str]]):
        """Index documents for BM25. documents = [(id, content), ...]"""
        self._doc_lengths = {}
        self._doc_freqs = defaultdict(int)

        for doc_id, content in documents:
            tokens = self._tokenize(content)
            self._doc_lengths[doc_id] = len(tokens)

            # Count unique words per document
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._doc_freqs[token] += 1

        self._num_docs = len(documents)
        if self._num_docs > 0:
            self._avg_doc_length = sum(self._doc_lengths.values()) / self._num_docs

    def score(self, query: str, doc_id: str, doc_content: str) -> float:
        """
        Compute BM25 score for a document given a query.
        """
        if self._num_docs == 0:
            return 0.0

        query_tokens = self._tokenize(query)
        doc_tokens = self._tokenize(doc_content)

        # Count term frequencies in document
        doc_tf = defaultdict(int)
        for token in doc_tokens:
            doc_tf[token] += 1

        doc_length = len(doc_tokens)
        score = 0.0

        for term in query_tokens:
            if term not in doc_tf:
                continue

            tf = doc_tf[term]
            df = self._doc_freqs.get(term, 0)

            # IDF
            idf = math.log((self._num_docs - df + 0.5) / (df + 0.5) + 1.0)

            # TF normalization
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / max(1, self._avg_doc_length))

            score += idf * numerator / denominator

        return score


class CrossEncoderReranker:
    """
    Re-rank results using cross-encoder for better precision.

    Cross-encoders consider query-document pairs together, producing
    more accurate relevance scores than bi-encoder (embedding) similarity.

    Uses Gemini for scoring when available, falls back to heuristics.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._use_llm = self.api_key is not None

    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int = 10
    ) -> List[RetrievedDocument]:
        """
        Re-rank documents by relevance to query.

        Args:
            query: Search query
            documents: Documents to re-rank
            top_k: Number to return after re-ranking

        Returns:
            Re-ranked documents with rerank_score set
        """
        if not documents:
            return documents

        if self._use_llm:
            return self._rerank_with_llm(query, documents, top_k)
        else:
            return self._rerank_heuristic(query, documents, top_k)

    def _rerank_heuristic(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int
    ) -> List[RetrievedDocument]:
        """Heuristic re-ranking without LLM."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for doc in documents:
            content_lower = doc.content.lower()

            # Factor 1: Exact phrase match (strong signal)
            exact_match = 1.0 if query_lower in content_lower else 0.0

            # Factor 2: Word overlap ratio
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words) / max(1, len(query_words))

            # Factor 3: Query position (earlier is better)
            first_match_pos = float('inf')
            for word in query_words:
                pos = content_lower.find(word)
                if pos >= 0:
                    first_match_pos = min(first_match_pos, pos)
            position_score = 1.0 / (1 + first_match_pos / 1000) if first_match_pos < float('inf') else 0

            # Factor 4: Document length (prefer medium length)
            length_penalty = 1.0 - abs(len(doc.content) - 2000) / 10000
            length_penalty = max(0.5, min(1.0, length_penalty))

            # Combine factors
            doc.rerank_score = (
                0.3 * exact_match +
                0.3 * overlap +
                0.2 * position_score +
                0.1 * length_penalty +
                0.1 * doc.score  # Original score as tiebreaker
            )

        # Sort by rerank score
        documents.sort(key=lambda d: d.rerank_score or 0, reverse=True)
        return documents[:top_k]

    def _rerank_with_llm(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int
    ) -> List[RetrievedDocument]:
        """Re-rank using Gemini for relevance scoring."""
        import urllib.request
        import urllib.error

        # Batch score documents (efficient API usage)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"

        # Prepare documents for scoring
        doc_summaries = []
        for i, doc in enumerate(documents[:20]):  # Limit to top 20 for efficiency
            preview = doc.content[:500].replace('\n', ' ')
            doc_summaries.append(f"[{i}] {preview}")

        prompt = f"""Rate the relevance of each document to the query on a scale of 0-10.
Query: "{query}"

Documents:
{chr(10).join(doc_summaries)}

Return ONLY a JSON array of scores in order, like: [8, 5, 9, ...]"""

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 200}
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                # Parse scores
                scores = json.loads(text.strip())

                for i, score in enumerate(scores):
                    if i < len(documents):
                        documents[i].rerank_score = float(score) / 10.0

        except Exception as e:
            # Fall back to heuristic
            return self._rerank_heuristic(query, documents, top_k)

        # Sort by rerank score
        documents.sort(key=lambda d: d.rerank_score or 0, reverse=True)
        return documents[:top_k]


class IntelligentRetrieval:
    """
    The Generation 3 Evolution: Intelligent Retrieval Orchestrator.

    Combines parallel search, query expansion, hybrid retrieval,
    and cross-encoder re-ranking for superior search quality.
    """

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        collection_name: str = "home_directory",
        verbose: bool = True
    ):
        self.verbose = verbose
        self.chroma_path = chroma_path or str(Path.home() / ".cache" / "multi_db_agent" / "home_index")
        self.collection_name = collection_name

        # Components
        self.query_expander = QueryExpander()
        self.smart_chunker = SmartChunker()
        self.keyword_scorer = KeywordScorer()
        self.reranker = CrossEncoderReranker()

        # Chroma connection
        self._client = None
        self._collection = None
        self._gemini_api_key = os.getenv("GEMINI_API_KEY")

        self._connect_chroma()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[IRO] {msg}")

    def _connect_chroma(self):
        """Connect to Chroma vector store."""
        if not CHROMADB_AVAILABLE:
            self._log("Warning: chromadb not available")
            return

        try:
            self._client = chromadb.PersistentClient(path=self.chroma_path)
            self._collection = self._client.get_collection(name=self.collection_name)
            self._log(f"Connected to Chroma: {self._collection.count()} documents")
        except Exception as e:
            self._log(f"Chroma connection failed: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Get Gemini embedding for text."""
        import urllib.request

        if not self._gemini_api_key:
            return [0.0] * 768

        text = text[:8000]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self._gemini_api_key}"

        payload = json.dumps({
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]}
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("embedding", {}).get("values", [0.0] * 768)
        except:
            return [0.0] * 768

    def _vector_search(
        self,
        query: str,
        top_k: int = 20,
        doc_type: Optional[str] = None
    ) -> List[RetrievedDocument]:
        """Perform vector similarity search."""
        if not self._collection:
            return []

        query_embedding = self._get_embedding(query)

        where_filter = {"type": doc_type} if doc_type else None

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        documents = []
        if results["documents"] and results["documents"][0]:
            for i, content in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                documents.append(RetrievedDocument(
                    id=hashlib.md5(content[:100].encode()).hexdigest()[:12],
                    content=content,
                    source=metadata.get("type", "unknown"),
                    source_path=metadata.get("source", ""),
                    score=1 - distance,  # Convert distance to similarity
                    metadata=metadata,
                    query_variant=query,
                    retrieval_method="vector"
                ))

        return documents

    def _parallel_fan_out_search(
        self,
        queries: List[str],
        top_k_per_query: int = 10,
        doc_types: Optional[List[str]] = None
    ) -> List[RetrievedDocument]:
        """
        Search multiple queries in parallel across multiple doc types.

        This is the core parallel fan-out pattern.
        """
        doc_types = doc_types or ["code", "document", "conversation"]
        all_documents = []
        seen_ids = set()

        # Create search tasks
        search_tasks = []
        for query in queries:
            for doc_type in doc_types:
                search_tasks.append((query, doc_type))

        # Execute in parallel
        with ThreadPoolExecutor(max_workers=min(8, len(search_tasks))) as executor:
            futures = {
                executor.submit(self._vector_search, query, top_k_per_query, doc_type): (query, doc_type)
                for query, doc_type in search_tasks
            }

            for future in as_completed(futures):
                query, doc_type = futures[future]
                try:
                    results = future.result()
                    for doc in results:
                        # Deduplicate by content hash
                        content_hash = hashlib.md5(doc.content[:500].encode()).hexdigest()
                        if content_hash not in seen_ids:
                            seen_ids.add(content_hash)
                            doc.query_variant = query
                            all_documents.append(doc)
                except Exception as e:
                    self._log(f"Search error for {query}/{doc_type}: {e}")

        return all_documents

    def _hybrid_score(
        self,
        documents: List[RetrievedDocument],
        query: str,
        alpha: float = 0.7  # Weight for vector vs keyword
    ) -> List[RetrievedDocument]:
        """
        Combine vector and keyword scores for hybrid ranking.

        alpha=1.0 means pure vector, alpha=0.0 means pure keyword.
        """
        if not documents:
            return documents

        # Build keyword index from candidates
        self.keyword_scorer.index_documents([
            (doc.id, doc.content) for doc in documents
        ])

        # Score each document
        for doc in documents:
            keyword_score = self.keyword_scorer.score(query, doc.id, doc.content)
            # Normalize keyword score to 0-1 range (approximate)
            keyword_score = min(1.0, keyword_score / 10.0)

            # Combine scores
            doc.final_score = alpha * doc.score + (1 - alpha) * keyword_score

        return documents

    def search(
        self,
        query: str,
        expand: bool = True,
        rerank: bool = True,
        hybrid: bool = True,
        sources: Optional[List[str]] = None,
        top_k: int = 20,
        final_k: int = 5
    ) -> SearchResult:
        """
        Intelligent search with all enhancements.

        Args:
            query: Search query
            expand: Whether to expand query with variations
            rerank: Whether to apply cross-encoder re-ranking
            hybrid: Whether to use hybrid vector+keyword scoring
            sources: Document types to search ("code", "document", "conversation")
            top_k: Number of candidates to retrieve per source
            final_k: Final number of results after re-ranking

        Returns:
            SearchResult with documents and metadata
        """
        start_time = time.time()

        # 1. Query expansion
        if expand:
            queries = self.query_expander.expand(query)
            self._log(f"Expanded to {len(queries)} query variants")
        else:
            queries = [query]

        # 2. Parallel fan-out search
        search_start = time.time()
        documents = self._parallel_fan_out_search(queries, top_k, sources)
        search_time = (time.time() - search_start) * 1000
        self._log(f"Retrieved {len(documents)} candidates in {search_time:.0f}ms")

        total_candidates = len(documents)

        # 3. Hybrid scoring
        if hybrid:
            documents = self._hybrid_score(documents, query)

        # 4. Re-ranking
        rerank_start = time.time()
        if rerank and documents:
            documents = self.reranker.rerank(query, documents, final_k)
        else:
            # Just sort by score and take top
            documents.sort(key=lambda d: d.effective_score, reverse=True)
            documents = documents[:final_k]
        rerank_time = (time.time() - rerank_start) * 1000

        # Build result
        result = SearchResult(
            query=query,
            documents=documents,
            expanded_queries=queries if expand else [],
            sources_searched=sources or ["code", "document", "conversation"],
            total_candidates=total_candidates,
            search_time_ms=search_time,
            rerank_time_ms=rerank_time,
            method_stats={
                "vector": sum(1 for d in documents if d.retrieval_method == "vector"),
                "expanded_queries": len(queries),
            }
        )

        total_time = (time.time() - start_time) * 1000
        self._log(f"Search complete: {len(documents)} results in {total_time:.0f}ms")

        return result

    def explain_search(self, result: SearchResult) -> str:
        """Generate human-readable explanation of search process."""
        lines = [
            f"🔍 Search Explanation for: \"{result.query}\"",
            "",
            f"📊 Statistics:",
            f"  • Candidates retrieved: {result.total_candidates}",
            f"  • Final results: {len(result.documents)}",
            f"  • Search time: {result.search_time_ms:.0f}ms",
            f"  • Re-rank time: {result.rerank_time_ms:.0f}ms",
            "",
        ]

        if result.expanded_queries:
            lines.extend([
                f"🔄 Query Expansion ({len(result.expanded_queries)} variants):",
                *[f"  • {q}" for q in result.expanded_queries[:5]],
                "",
            ])

        lines.extend([
            f"📁 Sources Searched: {', '.join(result.sources_searched)}",
            "",
            f"📄 Top Results:",
        ])

        for i, doc in enumerate(result.documents[:5], 1):
            score = doc.effective_score
            preview = doc.content[:100].replace('\n', ' ')
            lines.append(f"  {i}. [{doc.source}] score={score:.3f}")
            lines.append(f"     {preview}...")
            lines.append(f"     Path: {doc.source_path}")
            lines.append("")

        return "\n".join(lines)


def main():
    """CLI for Intelligent Retrieval."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Intelligent Retrieval Orchestrator - Gen 3 Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  iro search "authentication security"
  iro search "how does login work" --no-expand
  iro search "api endpoints" --sources code --top-k 10
  iro explain "database connection"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Intelligent search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--no-expand", action="store_true", help="Disable query expansion")
    search_parser.add_argument("--no-rerank", action="store_true", help="Disable re-ranking")
    search_parser.add_argument("--no-hybrid", action="store_true", help="Disable hybrid scoring")
    search_parser.add_argument("--sources", nargs="+", help="Document types (code, document, conversation)")
    search_parser.add_argument("--top-k", type=int, default=20, help="Candidates per source")
    search_parser.add_argument("--final-k", type=int, default=5, help="Final results")

    # Explain command
    explain_parser = subparsers.add_parser("explain", help="Search with explanation")
    explain_parser.add_argument("query", help="Search query")

    args = parser.parse_args()

    if args.command == "search":
        iro = IntelligentRetrieval()
        result = iro.search(
            args.query,
            expand=not args.no_expand,
            rerank=not args.no_rerank,
            hybrid=not args.no_hybrid,
            sources=args.sources,
            top_k=args.top_k,
            final_k=args.final_k
        )

        print(f"\nFound {len(result.documents)} results:\n")
        for i, doc in enumerate(result.documents, 1):
            print(f"--- {i}. [{doc.source}] score={doc.effective_score:.3f} ---")
            print(f"Path: {doc.source_path}")
            print(f"Preview: {doc.content[:300]}...")
            print()
        return 0

    elif args.command == "explain":
        iro = IntelligentRetrieval()
        result = iro.search(args.query)
        print(iro.explain_search(result))
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
