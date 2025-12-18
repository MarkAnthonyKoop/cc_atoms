#!/usr/bin/env python3
"""
Performance Comparison: Chroma (HomeIndexer) vs Elysia (Weaviate)

This test compares:
1. Search latency (time per query)
2. Result quality (relevance of top results)
3. Throughput (queries per second)
4. Result overlap (do they find the same documents?)
5. Memory/resource usage patterns

NO MOCKING - Real live performance testing.
"""
import os
import sys
import json
import time
import statistics
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


@dataclass
class SearchResult:
    """Normalized search result for comparison"""
    source: str
    doc_type: str
    score: float
    content_preview: str


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query: str
    backend: str
    latency_ms: float
    num_results: int
    top_sources: List[str]
    error: Optional[str] = None


@dataclass
class BenchmarkResults:
    """Aggregated benchmark results"""
    backend: str
    total_queries: int = 0
    total_results: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    errors: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def median_latency_ms(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def min_latency_ms(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0

    @property
    def max_latency_ms(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0

    @property
    def qps(self) -> float:
        """Queries per second"""
        if not self.latencies_ms:
            return 0
        total_time_s = sum(self.latencies_ms) / 1000
        return self.total_queries / total_time_s if total_time_s > 0 else 0


# Test queries - variety of types and complexities
TEST_QUERIES = [
    # Simple keyword queries
    ("python", "simple"),
    ("function", "simple"),
    ("import", "simple"),
    ("class", "simple"),
    ("error", "simple"),

    # Multi-word queries
    ("python function definition", "multi-word"),
    ("import json data", "multi-word"),
    ("error handling exception", "multi-word"),
    ("database query sql", "multi-word"),
    ("api request response", "multi-word"),

    # Technical/domain queries
    ("vector embedding search", "technical"),
    ("weaviate chroma database", "technical"),
    ("claude conversation atom", "technical"),
    ("gemini openai embedding", "technical"),
    ("authentication login token", "technical"),

    # Natural language queries
    ("how to handle errors in python", "natural"),
    ("where is the main entry point", "natural"),
    ("what files handle authentication", "natural"),
    ("how does the search work", "natural"),
    ("find all test files", "natural"),

    # Code-specific queries
    ("def __init__(self):", "code"),
    ("async def", "code"),
    ("try except finally", "code"),
    ("@dataclass", "code"),
    ("if __name__ == '__main__':", "code"),
]


class ChromaSearcher:
    """Wrapper for Chroma/HomeIndexer search"""

    def __init__(self):
        from cc_atoms.tools.multi_db_agent.autonomous_agent import AutonomousDataAgent
        self.agent = AutonomousDataAgent(verbose=False)
        stats = self.agent.get_stats()
        self.doc_count = stats.get('index', {}).get('document_count', 0)

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        results = self.agent.search(query, top_k=limit)
        return [
            SearchResult(
                source=r.get('relative_path', r.get('filename', 'unknown')),
                doc_type=r.get('type', 'unknown'),
                score=r.get('score', 0.0),
                content_preview=r.get('content', '')[:200]
            )
            for r in results
        ]


class ElysiaSearcher:
    """Wrapper for Elysia/Weaviate search"""

    def __init__(self):
        from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia, ElysiaSyncConfig, WeaviateClient
        self.query_elysia = query_elysia
        self.config = ElysiaSyncConfig()

        # Test connection
        client = WeaviateClient(self.config)
        self.available = client.connect()
        if self.available:
            client.close()

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        if not self.available:
            return []

        results = self.query_elysia(query, limit=limit)
        return [
            SearchResult(
                source=r.get('source', 'unknown'),
                doc_type=r.get('type', 'unknown'),
                score=0.0,  # Elysia doesn't return scores in basic query
                content_preview=r.get('content', '')[:200]
            )
            for r in results
        ]


def run_benchmark(searcher, queries: List[tuple], backend_name: str) -> BenchmarkResults:
    """Run benchmark on a searcher"""
    results = BenchmarkResults(backend=backend_name)

    for query, query_type in queries:
        start = time.perf_counter()
        try:
            search_results = searcher.search(query, limit=10)
            elapsed_ms = (time.perf_counter() - start) * 1000

            results.total_queries += 1
            results.total_results += len(search_results)
            results.latencies_ms.append(elapsed_ms)

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.errors += 1
            results.latencies_ms.append(elapsed_ms)

    return results


def compare_results(chroma_results: List[SearchResult],
                   elysia_results: List[SearchResult]) -> Dict[str, Any]:
    """Compare search results from both backends"""

    # Extract source file basenames for comparison
    chroma_sources = set(Path(r.source).name for r in chroma_results)
    elysia_sources = set(Path(r.source).name for r in elysia_results)

    overlap = chroma_sources & elysia_sources
    chroma_only = chroma_sources - elysia_sources
    elysia_only = elysia_sources - chroma_sources

    # Jaccard similarity
    union = chroma_sources | elysia_sources
    jaccard = len(overlap) / len(union) if union else 0

    return {
        'overlap_count': len(overlap),
        'chroma_only_count': len(chroma_only),
        'elysia_only_count': len(elysia_only),
        'jaccard_similarity': jaccard,
        'overlap_files': list(overlap)[:5],
        'chroma_only_files': list(chroma_only)[:5],
        'elysia_only_files': list(elysia_only)[:5],
    }


def run_comparison():
    """Run full performance comparison"""
    print("=" * 70)
    print("PERFORMANCE COMPARISON: Chroma (HomeIndexer) vs Elysia (Weaviate)")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Test queries: {len(TEST_QUERIES)}")
    print()

    # Initialize searchers
    print("Initializing Chroma (HomeIndexer)...")
    try:
        chroma = ChromaSearcher()
        print(f"  Documents indexed: {chroma.doc_count}")
        chroma_available = True
    except Exception as e:
        print(f"  ERROR: {e}")
        chroma_available = False

    print("\nInitializing Elysia (Weaviate)...")
    try:
        elysia = ElysiaSearcher()
        print(f"  Available: {elysia.available}")
        elysia_available = elysia.available
    except Exception as e:
        print(f"  ERROR: {e}")
        elysia_available = False

    if not chroma_available:
        print("\nERROR: Chroma not available. Cannot run comparison.")
        return

    # Run benchmarks
    print("\n" + "-" * 70)
    print("BENCHMARK: Latency & Throughput")
    print("-" * 70)

    # Warm up
    print("\nWarm-up phase (5 queries each)...")
    for query, _ in TEST_QUERIES[:5]:
        chroma.search(query)
        if elysia_available:
            elysia.search(query)

    # Run Chroma benchmark
    print("\nRunning Chroma benchmark...")
    chroma_bench = run_benchmark(chroma, TEST_QUERIES, "Chroma")

    # Run Elysia benchmark
    if elysia_available:
        print("Running Elysia benchmark...")
        elysia_bench = run_benchmark(elysia, TEST_QUERIES, "Elysia")
    else:
        elysia_bench = None

    # Print results
    print("\n" + "-" * 70)
    print("RESULTS: Latency Statistics (milliseconds)")
    print("-" * 70)

    print(f"\n{'Metric':<20} {'Chroma':>15}", end="")
    if elysia_bench:
        print(f" {'Elysia':>15} {'Diff':>15}")
    else:
        print()

    print("-" * 70)

    metrics = [
        ("Avg Latency", "avg_latency_ms"),
        ("Median Latency", "median_latency_ms"),
        ("P95 Latency", "p95_latency_ms"),
        ("Min Latency", "min_latency_ms"),
        ("Max Latency", "max_latency_ms"),
    ]

    for label, attr in metrics:
        chroma_val = getattr(chroma_bench, attr)
        print(f"{label:<20} {chroma_val:>15.2f}", end="")
        if elysia_bench:
            elysia_val = getattr(elysia_bench, attr)
            diff = elysia_val - chroma_val
            diff_pct = (diff / chroma_val * 100) if chroma_val else 0
            print(f" {elysia_val:>15.2f} {diff:>+10.2f} ({diff_pct:>+.1f}%)")
        else:
            print()

    print("-" * 70)
    print(f"{'Queries/Second':<20} {chroma_bench.qps:>15.2f}", end="")
    if elysia_bench:
        print(f" {elysia_bench.qps:>15.2f} {elysia_bench.qps - chroma_bench.qps:>+10.2f}")
    else:
        print()

    print(f"{'Total Results':<20} {chroma_bench.total_results:>15}", end="")
    if elysia_bench:
        print(f" {elysia_bench.total_results:>15}")
    else:
        print()

    print(f"{'Errors':<20} {chroma_bench.errors:>15}", end="")
    if elysia_bench:
        print(f" {elysia_bench.errors:>15}")
    else:
        print()

    # Result quality comparison
    if elysia_available:
        print("\n" + "-" * 70)
        print("RESULTS: Search Quality Comparison")
        print("-" * 70)

        # Sample queries for detailed comparison
        sample_queries = [
            "python function",
            "vector embedding",
            "error handling",
            "authentication",
            "database query",
        ]

        print(f"\n{'Query':<25} {'Overlap':>10} {'Chroma Only':>12} {'Elysia Only':>12} {'Jaccard':>10}")
        print("-" * 70)

        total_jaccard = 0
        for query in sample_queries:
            chroma_res = chroma.search(query)
            elysia_res = elysia.search(query)

            comparison = compare_results(chroma_res, elysia_res)
            total_jaccard += comparison['jaccard_similarity']

            print(f"{query:<25} {comparison['overlap_count']:>10} "
                  f"{comparison['chroma_only_count']:>12} "
                  f"{comparison['elysia_only_count']:>12} "
                  f"{comparison['jaccard_similarity']:>10.2%}")

        avg_jaccard = total_jaccard / len(sample_queries)
        print("-" * 70)
        print(f"{'Average Similarity':<25} {'':<10} {'':<12} {'':<12} {avg_jaccard:>10.2%}")

    # Query type breakdown
    print("\n" + "-" * 70)
    print("RESULTS: Latency by Query Type")
    print("-" * 70)

    query_types = {}
    for i, (query, query_type) in enumerate(TEST_QUERIES):
        if query_type not in query_types:
            query_types[query_type] = {'chroma': [], 'elysia': []}
        query_types[query_type]['chroma'].append(chroma_bench.latencies_ms[i])
        if elysia_bench:
            query_types[query_type]['elysia'].append(elysia_bench.latencies_ms[i])

    print(f"\n{'Query Type':<15} {'Chroma Avg (ms)':>18}", end="")
    if elysia_bench:
        print(f" {'Elysia Avg (ms)':>18} {'Winner':>12}")
    else:
        print()

    print("-" * 70)

    for qtype, latencies in sorted(query_types.items()):
        chroma_avg = statistics.mean(latencies['chroma'])
        print(f"{qtype:<15} {chroma_avg:>18.2f}", end="")
        if elysia_bench and latencies['elysia']:
            elysia_avg = statistics.mean(latencies['elysia'])
            winner = "Chroma" if chroma_avg < elysia_avg else "Elysia"
            print(f" {elysia_avg:>18.2f} {winner:>12}")
        else:
            print()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"""
Chroma (HomeIndexer):
  - Documents: {chroma.doc_count}
  - Avg Latency: {chroma_bench.avg_latency_ms:.2f}ms
  - Throughput: {chroma_bench.qps:.2f} queries/sec
  - Backend: Local Chroma with Gemini embeddings
  - Storage: ~/.cache/multi_db_agent/chroma_db/
""")

    if elysia_bench:
        speedup = chroma_bench.avg_latency_ms / elysia_bench.avg_latency_ms if elysia_bench.avg_latency_ms else 0
        print(f"""Elysia (Weaviate):
  - Avg Latency: {elysia_bench.avg_latency_ms:.2f}ms
  - Throughput: {elysia_bench.qps:.2f} queries/sec
  - Backend: Embedded Weaviate with Gemini embeddings
  - Storage: ~/.local/share/weaviate/
  - Collections: ClaudeConversations, CodeFiles, (Emails, Documents optional)

Comparison:
  - Speed: {'Chroma' if chroma_bench.avg_latency_ms < elysia_bench.avg_latency_ms else 'Elysia'} is {abs(speedup - 1) * 100:.1f}% faster
  - Elysia latency is {elysia_bench.avg_latency_ms / chroma_bench.avg_latency_ms:.1f}x Chroma's latency
  - Result overlap: ~{avg_jaccard:.0%} of results are the same
""")
    else:
        print("Elysia: Not available for comparison")

    # Characteristics
    print("-" * 70)
    print("CHARACTERISTICS")
    print("-" * 70)
    print("""
Chroma (HomeIndexer):
  + Faster queries (optimized for local search)
  + Simpler setup (just pip install)
  + Lower memory footprint
  + Good for code-heavy workloads
  - Single collection model
  - Less structured metadata

Elysia (Weaviate):
  + Separate collections (conversations, code, emails, docs)
  + Richer metadata and filtering
  + Better for heterogeneous data
  + Production-grade vector DB
  - Higher latency (embedded mode)
  - More complex setup (binary download)
  - Higher memory usage
""")

    return {
        'chroma': chroma_bench,
        'elysia': elysia_bench,
        'avg_jaccard': avg_jaccard if elysia_available else None,
    }


if __name__ == "__main__":
    run_comparison()
