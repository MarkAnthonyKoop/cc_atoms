"""
Semantic Router - Fast query classification without LLM calls

Uses sentence embeddings to classify queries into database types:
- sql: Structured data queries (counts, aggregations, joins)
- vector: Semantic search queries (find similar, search for)
- graph: Relationship queries (connected to, path between)
- multi_source: Cross-database queries
- analytical: Analysis and insights
"""
import os
from typing import Optional
from dataclasses import dataclass

# Try to import semantic-router, fall back to simple keyword matching
try:
    from semantic_router import Route, RouteLayer
    from semantic_router.encoders import HuggingFaceEncoder
    SEMANTIC_ROUTER_AVAILABLE = True
except ImportError:
    SEMANTIC_ROUTER_AVAILABLE = False


@dataclass
class RouteResult:
    """Result from query classification."""
    name: str
    confidence: float = 1.0


class QueryRouter:
    """
    Classify queries using semantic embeddings or keyword fallback.

    Uses local HuggingFace encoder (free) for fast classification (~10ms).
    Falls back to keyword matching if semantic-router not installed.
    """

    def __init__(self, use_semantic: bool = True):
        self.use_semantic = use_semantic and SEMANTIC_ROUTER_AVAILABLE
        self._router = None

        if self.use_semantic:
            self._init_semantic_router()
        else:
            self._init_keyword_router()

    def _init_semantic_router(self):
        """Initialize semantic router with HuggingFace encoder."""
        # Local encoder - free, no API calls
        encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")

        # Define routes with example utterances
        sql_route = Route(
            name="sql",
            utterances=[
                "how many users signed up last month",
                "what's the total revenue by quarter",
                "show me orders where status is pending",
                "count of products in each category",
                "average order value by customer segment",
                "list all transactions from yesterday",
                "which customers have spent more than 1000",
                "join users with their orders",
                "select all records from the database",
                "group by category and sum the totals",
                "filter where date is greater than",
                "count distinct values in column",
            ],
        )

        vector_route = Route(
            name="vector",
            utterances=[
                "find documents similar to this topic",
                "search for content about machine learning",
                "what articles discuss climate change",
                "find related research papers",
                "semantic search for customer feedback about shipping",
                "documents that mention product quality issues",
                "find content semantically related to AI ethics",
                "search for similar conversations",
                "find code files related to authentication",
                "look up documentation about APIs",
            ],
        )

        graph_route = Route(
            name="graph",
            utterances=[
                "how is person A connected to person B",
                "what's the relationship between these entities",
                "show me the network of dependencies",
                "find all paths between nodes",
                "who are the common connections",
                "trace the supply chain from source to destination",
                "what entities are related to this concept",
                "show the dependency tree",
                "find linked records",
                "traverse the graph from this node",
            ],
        )

        multi_source_route = Route(
            name="multi_source",
            utterances=[
                "combine customer data with their support tickets",
                "match sales records with product descriptions",
                "correlate user behavior with feedback sentiment",
                "find customers in database who mentioned issues in tickets",
                "cross-reference inventory with supplier documents",
                "join structured data with unstructured notes",
                "combine information from multiple sources",
                "aggregate data across databases",
            ],
        )

        analytical_route = Route(
            name="analytical",
            utterances=[
                "analyze trends in the data",
                "what patterns exist in customer behavior",
                "summarize the key insights from this dataset",
                "compare performance across regions",
                "identify anomalies in the metrics",
                "provide insights about the data",
                "what can we learn from this",
                "explain the trends",
            ],
        )

        routes = [sql_route, vector_route, graph_route, multi_source_route, analytical_route]
        self._router = RouteLayer(encoder=encoder, routes=routes)

    def _init_keyword_router(self):
        """Initialize simple keyword-based router as fallback."""
        self._keywords = {
            "sql": [
                "count", "sum", "average", "total", "how many", "list all",
                "select", "where", "group by", "order by", "join", "filter",
                "records", "rows", "database", "table", "column",
                "signed up", "registered", "purchased", "ordered",
            ],
            "vector": [
                "find similar", "search for", "semantic", "related to",
                "documents about", "articles", "content", "look up",
                "find code", "search", "similar",
            ],
            "graph": [
                "connected", "relationship", "path between", "linked",
                "network", "dependencies", "traverse", "graph",
                "related entities", "connections",
            ],
            "multi_source": [
                "combine", "correlate", "cross-reference", "match",
                "join", "aggregate across", "multiple sources",
            ],
            "analytical": [
                "analyze", "patterns", "trends", "insights",
                "anomalies", "summarize", "compare", "explain",
            ],
        }

    def classify(self, query: str) -> RouteResult:
        """
        Classify a query into a route type.

        Args:
            query: Natural language query

        Returns:
            RouteResult with name and confidence
        """
        if self.use_semantic:
            result = self._router(query)
            if result.name:
                return RouteResult(name=result.name, confidence=0.9)
            # Fallback to keyword matching
            return self._keyword_classify(query)
        else:
            return self._keyword_classify(query)

    def _keyword_classify(self, query: str) -> RouteResult:
        """Classify using keyword matching."""
        query_lower = query.lower()

        scores = {}
        for route, keywords in self._keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[route] = score

        if max(scores.values()) > 0:
            best_route = max(scores, key=scores.get)
            return RouteResult(name=best_route, confidence=0.7)

        # Default to vector search
        return RouteResult(name="vector", confidence=0.5)


# Global router instance
_router: Optional[QueryRouter] = None


def get_router() -> QueryRouter:
    """Get or create global router instance."""
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router


def classify_query(query: str) -> str:
    """
    Classify a query and return the route name.

    Args:
        query: Natural language query

    Returns:
        Route name: 'sql', 'vector', 'graph', 'multi_source', or 'analytical'
    """
    router = get_router()
    result = router.classify(query)
    return result.name


if __name__ == "__main__":
    # Test classification
    test_queries = [
        "How many orders were placed last week?",
        "Find documents about renewable energy",
        "What's the connection between Company A and Company B?",
        "Match customer complaints with their purchase history",
        "Analyze the sales trends and identify patterns",
    ]

    router = QueryRouter()
    print(f"Using semantic router: {router.use_semantic}")
    print()

    for q in test_queries:
        result = router.classify(q)
        print(f"{q[:50]:50} -> {result.name} ({result.confidence:.2f})")
