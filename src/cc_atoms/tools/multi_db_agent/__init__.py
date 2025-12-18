"""
Multi-Database Agent - Semantic query routing across heterogeneous databases

Uses Semantic Router for fast query classification and LlamaIndex for database operations.
Integrates with cc_atoms for autonomous multi-source queries.

Architecture:
    Query -> Semantic Router -> Specialized Agent -> Database -> Response Synthesizer

Supported databases:
    - SQL: PostgreSQL, MySQL, SQLite
    - Vector: Weaviate, Chroma (local)
    - Elysia: Personal knowledge base (conversations, code, emails)

Usage:
    from cc_atoms.tools.multi_db_agent import MultiDBAgent, create_agent

    agent = create_agent()
    agent.register_sql({"main": "sqlite:///data.db"})
    agent.register_vector({"docs": {"store_type": "chroma"}})

    result = agent.query("How many users signed up last month?")

CLI:
    multi-db-agent query "Find code about authentication"
    multi-db-agent interactive
"""
from .orchestrator import (
    MultiDBAgent,
    QueryResult,
    QueryType,
    create_agent,
    main,
)
from .router import (
    QueryRouter,
    classify_query,
)
from .home_indexer import (
    HomeIndexer,
    HomeIndexerConfig,
)
from .conversational_agent import (
    ConversationalAgent,
    create_conversational_agent,
)
from .autonomous_agent import (
    AutonomousDataAgent,
    ActionType,
    ActionResult,
)
from .capability_registry import (
    CapabilityRegistry,
    CapabilityMetadata,
    CapabilityType,
    ExecutionResult,
)
from .workflow_engine import (
    WorkflowEngine,
    Workflow,
    WorkflowStep,
    WorkflowResult,
    WorkflowContext,
    StepStatus,
    NodeType,
)
from .intelligent_retrieval import (
    IntelligentRetrieval,
    SearchResult,
    RetrievedDocument,
    QueryExpander,
    SmartChunker,
    CrossEncoderReranker,
)
from .smart_search import (
    SmartSearchEngine,
    SearchResult as SmartSearchResult,
    SearchResponse,
    QueryIntent,
    QueryAnalyzer,
    SmartChunker as IntentAwareChunker,
    ReRanker,
)

__all__ = [
    # Orchestrator
    'MultiDBAgent',
    'QueryResult',
    'QueryType',
    'create_agent',
    'main',
    # Router
    'QueryRouter',
    'classify_query',
    # Indexer
    'HomeIndexer',
    'HomeIndexerConfig',
    # Agents
    'ConversationalAgent',
    'create_conversational_agent',
    'AutonomousDataAgent',
    'ActionType',
    'ActionResult',
    # Capability Registry (Gen 1)
    'CapabilityRegistry',
    'CapabilityMetadata',
    'CapabilityType',
    'ExecutionResult',
    # Workflow Engine (Gen 2)
    'WorkflowEngine',
    'Workflow',
    'WorkflowStep',
    'WorkflowResult',
    'WorkflowContext',
    'StepStatus',
    'NodeType',
    # Intelligent Retrieval (Gen 3) - THE NEXT LEVEL
    'IntelligentRetrieval',
    'SearchResult',
    'RetrievedDocument',
    'QueryExpander',
    'SmartChunker',
    'CrossEncoderReranker',
    # Smart Search Engine (Gen 3+) - Intent-aware retrieval
    'SmartSearchEngine',
    'SmartSearchResult',
    'SearchResponse',
    'QueryIntent',
    'QueryAnalyzer',
    'IntentAwareChunker',
    'ReRanker',
]
