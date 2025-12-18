"""
Multi-Database Agent Orchestrator

Routes queries to appropriate database handlers based on semantic classification.
Synthesizes results from multiple sources using LLM.
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

from .router import classify_query, QueryRouter


class QueryType(Enum):
    """Types of database queries."""
    SQL = "sql"
    VECTOR = "vector"
    GRAPH = "graph"
    MULTI_SOURCE = "multi_source"
    ANALYTICAL = "analytical"
    ELYSIA = "elysia"  # Personal knowledge base


@dataclass
class QueryResult:
    """Result from agent query."""
    query_type: QueryType
    answer: str
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_results: Any = None

    def to_dict(self) -> Dict:
        return {
            "query_type": self.query_type.value,
            "answer": self.answer,
            "sources": self.sources,
            "metadata": self.metadata,
        }


class MultiDBAgent:
    """
    Multi-database AI agent with semantic query routing.

    Automatically routes queries to:
    - SQL databases (structured queries)
    - Vector stores (semantic search)
    - Elysia knowledge base (personal context)
    - Multiple sources (cross-database queries)

    Can use various LLM providers for synthesis.
    """

    def __init__(
        self,
        llm_provider: str = "atom",  # "atom", "anthropic", "ollama", "gemini"
        model: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize the agent.

        Args:
            llm_provider: LLM provider for synthesis
                - "atom": Use embedded cc_atoms (default, no extra deps)
                - "anthropic": Use Anthropic Claude
                - "ollama": Use local Ollama
                - "gemini": Use Google Gemini (free tier)
            model: Model name (optional, uses provider default)
            verbose: Print debug information
        """
        self.llm_provider = llm_provider
        self.model = model
        self.verbose = verbose

        # Connectors (initialized lazily)
        self._sql_connector = None
        self._vector_connector = None
        self._elysia_connector = None

        # Router
        self._router = QueryRouter()

        # LLM for synthesis
        self._llm = None

    def _log(self, msg: str):
        """Log message if verbose."""
        if self.verbose:
            print(f"[MultiDBAgent] {msg}")

    # ==========================================================================
    # Connector Registration
    # ==========================================================================

    def register_sql(self, connections: Dict[str, str]):
        """
        Register SQL database connections.

        Args:
            connections: {"db_name": "connection_uri", ...}
                Example: {"main": "sqlite:///data.db"}
        """
        from .connectors.sql_connector import MultiSQLConnector
        self._sql_connector = MultiSQLConnector(connections)
        self._log(f"Registered SQL: {list(connections.keys())}")

    def register_vector(self, configs: Dict[str, Dict]):
        """
        Register vector store connections.

        Args:
            configs: {
                "docs": {"store_type": "chroma", "collection_name": "documents"},
            }
        """
        from .connectors.vector_connector import MultiVectorConnector
        self._vector_connector = MultiVectorConnector(configs)
        self._log(f"Registered Vector: {list(configs.keys())}")

    def register_elysia(self, config=None):
        """
        Register Elysia knowledge base.

        Args:
            config: Optional ElysiaSyncConfig
        """
        from .connectors.elysia_connector import ElysiaConnector
        self._elysia_connector = ElysiaConnector(config)
        self._log(f"Registered Elysia: {self._elysia_connector.is_available}")

    def auto_register_elysia(self):
        """Auto-register Elysia if available."""
        try:
            self.register_elysia()
        except Exception as e:
            self._log(f"Elysia not available: {e}")

    # ==========================================================================
    # Query Execution
    # ==========================================================================

    def _execute_sql(self, query: str) -> Dict:
        """Execute SQL query."""
        if not self._sql_connector:
            return {"error": "No SQL connector registered"}

        results = self._sql_connector.query(query)
        # Combine results from all databases
        combined_answer = []
        all_sql = []

        for db_name, result in results.items():
            combined_answer.append(f"[{db_name}] {result.answer}")
            if result.sql:
                all_sql.append(f"-- {db_name}\n{result.sql}")

        return {
            "answer": "\n\n".join(combined_answer),
            "sql": "\n\n".join(all_sql),
            "source": "sql",
            "raw": results,
        }

    def _execute_vector(self, query: str) -> Dict:
        """Execute vector search."""
        if not self._vector_connector:
            return {"error": "No vector connector registered"}

        results = self._vector_connector.query(query)
        combined_answer = []
        all_sources = []

        for coll_name, result in results.items():
            combined_answer.append(f"[{coll_name}] {result.answer}")
            all_sources.extend(result.sources)

        return {
            "answer": "\n\n".join(combined_answer),
            "sources": all_sources,
            "source": "vector",
            "raw": results,
        }

    def _execute_elysia(self, query: str) -> Dict:
        """Execute Elysia knowledge base query."""
        if not self._elysia_connector:
            # Try auto-register
            self.auto_register_elysia()
            if not self._elysia_connector or not self._elysia_connector.is_available:
                return {"error": "Elysia not available. Run 'elysia-sync sync' first."}

        result = self._elysia_connector.query(query)
        return {
            "answer": result.answer,
            "sources": result.sources,
            "source": "elysia",
            "raw": result.documents,
        }

    def _execute_multi_source(self, query: str) -> Dict:
        """Execute query across multiple sources and synthesize."""
        results = {}

        # Gather from all available sources
        if self._sql_connector:
            results["sql"] = self._execute_sql(query)
        if self._vector_connector:
            results["vector"] = self._execute_vector(query)
        if self._elysia_connector and self._elysia_connector.is_available:
            results["elysia"] = self._execute_elysia(query)

        if not results:
            return {"error": "No data sources registered"}

        # Synthesize results
        synthesis = self._synthesize_results(query, results)

        return {
            "answer": synthesis,
            "sources": list(results.keys()),
            "source": "multi_source",
            "raw": results,
        }

    def _execute_analytical(self, query: str) -> Dict:
        """Execute analytical query with reasoning."""
        # First gather data from all sources
        data = self._execute_multi_source(query)

        if "error" in data:
            return data

        # Analyze the data
        analysis = self._analyze_data(query, data)

        return {
            "answer": analysis,
            "sources": data.get("sources", []),
            "source": "analytical",
            "raw": data.get("raw"),
        }

    def _synthesize_results(self, query: str, results: Dict) -> str:
        """Use LLM to synthesize results from multiple sources."""
        prompt = f"""Synthesize a comprehensive answer from multiple data sources.

Query: {query}

Results from different sources:
{self._format_results(results)}

Provide a unified, coherent answer that combines insights from all relevant sources.
Be concise but complete.
"""
        return self._call_llm(prompt)

    def _analyze_data(self, query: str, data: Dict) -> str:
        """Use LLM to analyze data and provide insights."""
        prompt = f"""Analyze the following data and provide insights.

Query: {query}

Data:
{self._format_results(data.get('raw', data))}

Provide:
1. Key patterns or trends
2. Notable findings
3. Actionable insights

Be specific and reference the data.
"""
        return self._call_llm(prompt)

    def _format_results(self, results: Dict) -> str:
        """Format results for LLM prompt."""
        formatted = []
        for source, result in results.items():
            if isinstance(result, dict):
                answer = result.get("answer", str(result))
            else:
                answer = str(result)
            formatted.append(f"=== {source} ===\n{answer[:2000]}")
        return "\n\n".join(formatted)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM for synthesis/analysis."""
        if self.llm_provider == "atom":
            return self._call_atom(prompt)
        elif self.llm_provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.llm_provider == "ollama":
            return self._call_ollama(prompt)
        elif self.llm_provider == "gemini":
            return self._call_gemini(prompt)
        else:
            # Fallback to atom
            return self._call_atom(prompt)

    def _call_atom(self, prompt: str) -> str:
        """Use embedded atom for LLM calls."""
        from cc_atoms.atom_core import AtomRuntime

        system_prompt = """You are a data synthesis assistant.
Given information from multiple sources, provide a clear, concise summary.
Output only the answer, then EXIT_LOOP_NOW."""

        runtime = AtomRuntime.create_ephemeral(
            system_prompt=system_prompt,
            max_iterations=3,
            verbose=False
        )

        result = runtime.run(prompt)
        output = result.get("output", "")
        return output.replace("EXIT_LOOP_NOW", "").strip()

    def _call_anthropic(self, prompt: str) -> str:
        """Use Anthropic Claude."""
        try:
            from llama_index.llms.anthropic import Anthropic
            llm = Anthropic(model=self.model or "claude-sonnet-4-20250514")
            response = llm.complete(prompt)
            return str(response)
        except ImportError:
            return self._call_atom(prompt)

    def _call_ollama(self, prompt: str) -> str:
        """Use local Ollama."""
        try:
            from llama_index.llms.ollama import Ollama
            llm = Ollama(model=self.model or "llama3.1:8b", request_timeout=120.0)
            response = llm.complete(prompt)
            return str(response)
        except ImportError:
            return self._call_atom(prompt)

    def _call_gemini(self, prompt: str) -> str:
        """Use Google Gemini (free tier)."""
        import urllib.request
        import json

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return self._call_atom(prompt)

        model = self.model or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            self._log(f"Gemini error: {e}")
            return self._call_atom(prompt)

    # ==========================================================================
    # Main Query Interface
    # ==========================================================================

    def query(self, query: str, force_type: Optional[QueryType] = None) -> QueryResult:
        """
        Execute a query with automatic routing.

        Args:
            query: Natural language query
            force_type: Override automatic routing

        Returns:
            QueryResult with answer and metadata
        """
        # Classify query
        if force_type:
            query_type = force_type
        else:
            route_name = classify_query(query)

            # Map to QueryType, defaulting to elysia for general knowledge queries
            if route_name == "vector" and self._elysia_connector:
                query_type = QueryType.ELYSIA
            else:
                try:
                    query_type = QueryType(route_name)
                except ValueError:
                    query_type = QueryType.VECTOR

        self._log(f"Query type: {query_type.value}")

        # Execute based on type
        handlers = {
            QueryType.SQL: self._execute_sql,
            QueryType.VECTOR: self._execute_vector,
            QueryType.ELYSIA: self._execute_elysia,
            QueryType.MULTI_SOURCE: self._execute_multi_source,
            QueryType.ANALYTICAL: self._execute_analytical,
            QueryType.GRAPH: self._execute_vector,  # Fallback to vector for now
        }

        handler = handlers.get(query_type, self._execute_elysia)
        result = handler(query)

        return QueryResult(
            query_type=query_type,
            answer=result.get("answer", result.get("error", "No result")),
            sources=result.get("sources", []),
            metadata={
                "sql": result.get("sql"),
                "source": result.get("source"),
            },
            raw_results=result.get("raw"),
        )

    def as_tool(self) -> Callable:
        """Return agent as a callable tool for other frameworks."""
        def query_tool(query: str, query_type: str = None) -> str:
            force = QueryType(query_type) if query_type else None
            result = self.query(query, force)
            return result.answer

        query_tool.__name__ = "multi_db_query"
        query_tool.__doc__ = """Query across SQL, vector, and knowledge base databases."""
        return query_tool


def create_agent(
    llm_provider: str = "atom",
    auto_elysia: bool = True,
    verbose: bool = False,
) -> MultiDBAgent:
    """
    Create a multi-database agent with common defaults.

    Args:
        llm_provider: LLM provider for synthesis
        auto_elysia: Automatically register Elysia if available
        verbose: Print debug info

    Returns:
        Configured MultiDBAgent
    """
    agent = MultiDBAgent(llm_provider=llm_provider, verbose=verbose)

    if auto_elysia:
        agent.auto_register_elysia()

    return agent


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-Database AI Agent - Query across heterogeneous data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  multi-db-agent query "How many users signed up?"
  multi-db-agent query "Find documents about authentication" --type vector
  multi-db-agent query "Search my conversations for API design" --type elysia
  multi-db-agent interactive
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Query command
    query_parser = subparsers.add_parser("query", help="Execute a query")
    query_parser.add_argument("query", help="Natural language query")
    query_parser.add_argument("--type", choices=["sql", "vector", "elysia", "multi_source", "analytical"],
                             help="Force query type")
    query_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Interactive mode
    interactive_parser = subparsers.add_parser("interactive", help="Interactive query mode")
    interactive_parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.command == "query":
        agent = create_agent(verbose=args.verbose)

        force_type = QueryType(args.type) if args.type else None
        result = agent.query(args.query, force_type)

        print(f"\nType: {result.query_type.value}")
        print(f"\n{result.answer}")

        if result.sources:
            print(f"\nSources: {', '.join(result.sources[:5])}")

        return 0

    elif args.command == "interactive":
        agent = create_agent(verbose=args.verbose)

        print("Multi-Database Agent (type 'quit' to exit)")
        print("=" * 50)

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() in ("quit", "exit", "q"):
                    break
                if not query:
                    continue

                result = agent.query(query)
                print(f"\n[{result.query_type.value}] {result.answer}")

            except KeyboardInterrupt:
                break
            except EOFError:
                break

        print("\nGoodbye!")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
