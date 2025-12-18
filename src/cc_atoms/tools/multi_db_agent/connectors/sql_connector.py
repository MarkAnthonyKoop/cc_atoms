"""
SQL Database Connector

Supports PostgreSQL, MySQL, SQLite via SQLAlchemy.
Uses LlamaIndex for natural language to SQL conversion when available,
falls back to embedded atom for query generation.
"""
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class SQLResult:
    """Result from SQL query."""
    answer: str
    sql: str
    rows: List[Dict]
    source: str = "sql"


class SQLConnector:
    """
    Connect to SQL databases and execute natural language queries.

    Supports:
    - SQLite (local, no setup)
    - PostgreSQL
    - MySQL

    Uses LlamaIndex NLSQLTableQueryEngine if available,
    otherwise uses embedded atom for SQL generation.
    """

    def __init__(self, connection_uri: str, tables: Optional[List[str]] = None):
        """
        Initialize SQL connector.

        Args:
            connection_uri: SQLAlchemy connection string
                - SQLite: "sqlite:///path/to/db.sqlite"
                - PostgreSQL: "postgresql://user:pass@host:5432/db"
                - MySQL: "mysql://user:pass@host:3306/db"
            tables: Optional list of tables to include (default: all)
        """
        self.connection_uri = connection_uri
        self.tables = tables
        self._engine = None
        self._metadata = None
        self._query_engine = None

        self._init_connection()

    def _init_connection(self):
        """Initialize database connection."""
        try:
            from sqlalchemy import create_engine, MetaData
            self._engine = create_engine(self.connection_uri)
            self._metadata = MetaData()
            self._metadata.reflect(bind=self._engine)

            # Use specified tables or all tables
            if self.tables is None:
                self.tables = list(self._metadata.tables.keys())

            # Try to use LlamaIndex for NL-to-SQL
            self._init_llamaindex()

        except ImportError:
            print("Warning: SQLAlchemy not installed. Install with: pip install sqlalchemy")
            raise

    def _init_llamaindex(self):
        """Initialize LlamaIndex query engine if available."""
        try:
            from llama_index.core import SQLDatabase
            from llama_index.core.query_engine import NLSQLTableQueryEngine

            self._sql_database = SQLDatabase(self._engine, include_tables=self.tables)
            self._query_engine = NLSQLTableQueryEngine(
                sql_database=self._sql_database,
                tables=self.tables,
            )
        except ImportError:
            # Will use embedded atom fallback
            pass

    def get_schema(self) -> str:
        """Get schema information for all tables."""
        schema_info = []
        for table_name in self.tables:
            table = self._metadata.tables[table_name]
            columns = [f"{col.name} ({col.type})" for col in table.columns]
            schema_info.append(f"{table_name}: {', '.join(columns)}")
        return "\n".join(schema_info)

    def execute_sql(self, sql: str) -> List[Dict]:
        """Execute raw SQL and return results."""
        from sqlalchemy import text

        with self._engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows

    def query(self, natural_language_query: str) -> SQLResult:
        """
        Execute natural language query against database.

        Args:
            natural_language_query: Question in plain English

        Returns:
            SQLResult with answer, SQL query, and raw rows
        """
        if self._query_engine:
            # Use LlamaIndex
            response = self._query_engine.query(natural_language_query)
            sql = response.metadata.get("sql_query", "")
            return SQLResult(
                answer=str(response),
                sql=sql,
                rows=self.execute_sql(sql) if sql else [],
            )
        else:
            # Use embedded atom for SQL generation
            return self._query_with_atom(natural_language_query)

    def _query_with_atom(self, query: str) -> SQLResult:
        """Generate and execute SQL using embedded atom."""
        from cc_atoms.atom_core import AtomRuntime

        schema = self.get_schema()
        system_prompt = f"""You are a SQL query generator.
Given a natural language question, generate a valid SQL query.

Database schema:
{schema}

Rules:
1. Generate only SELECT queries (no INSERT/UPDATE/DELETE)
2. Use table and column names exactly as shown in schema
3. Output ONLY the SQL query, nothing else
4. End with EXIT_LOOP_NOW

Example:
Question: How many users are there?
SELECT COUNT(*) FROM users
EXIT_LOOP_NOW
"""

        runtime = AtomRuntime.create_ephemeral(
            system_prompt=system_prompt,
            max_iterations=3,
            verbose=False
        )

        result = runtime.run(f"Question: {query}")
        output = result.get("output", "")

        # Extract SQL from output
        sql = output.replace("EXIT_LOOP_NOW", "").strip()
        sql_lines = [line for line in sql.split("\n") if line.strip() and not line.startswith("#")]
        sql = "\n".join(sql_lines)

        try:
            rows = self.execute_sql(sql)
            answer = f"Results: {rows[:10]}"  # Limit display
            if len(rows) > 10:
                answer += f"\n... and {len(rows) - 10} more rows"
        except Exception as e:
            rows = []
            answer = f"SQL Error: {e}"

        return SQLResult(answer=answer, sql=sql, rows=rows)


class MultiSQLConnector:
    """Manage multiple SQL database connections."""

    def __init__(self, connections: Dict[str, str]):
        """
        Initialize multiple SQL connections.

        Args:
            connections: {"db_name": "connection_uri", ...}
        """
        self.connectors = {
            name: SQLConnector(uri)
            for name, uri in connections.items()
        }

    def query(self, query: str, db_name: Optional[str] = None) -> Dict[str, SQLResult]:
        """
        Execute query on one or all databases.

        Args:
            query: Natural language query
            db_name: Specific database (or None for all)

        Returns:
            Dict mapping db_name to SQLResult
        """
        if db_name:
            return {db_name: self.connectors[db_name].query(query)}

        results = {}
        for name, connector in self.connectors.items():
            try:
                results[name] = connector.query(query)
            except Exception as e:
                results[name] = SQLResult(answer=f"Error: {e}", sql="", rows=[])

        return results

    def get_all_schemas(self) -> str:
        """Get schema info from all databases."""
        schemas = []
        for name, connector in self.connectors.items():
            schemas.append(f"=== {name} ===\n{connector.get_schema()}")
        return "\n\n".join(schemas)
