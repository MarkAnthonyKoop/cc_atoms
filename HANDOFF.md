# HANDOFF - cc_atoms Project Status

**Date:** 2025-11-30
**Previous Instance:** Claude Opus 4.5 (Gen 3+ Meta-Agent)
**Context:** Added SmartSearchEngine - Intent-aware retrieval with semantic re-ranking, building on Gen 3's IRO

---

## GENERATION 3+ EVOLUTION: SmartSearchEngine (Intent-Aware Retrieval)

### What Was Built

The **SmartSearchEngine** (`smart_search.py`) extends the Gen 3 Intelligent Retrieval with **intent-aware query understanding**.

**The Key Insight:** Gen 3's IRO added parallel fan-out and re-ranking, but treated all queries identically. Gen 3+ adds *intent classification* - "How do I use AtomRuntime?" should retrieve tutorials and examples, while "AtomRuntime bug" should surface code and error logs. Different intents need different retrieval strategies.

### What SmartSearchEngine Adds

| Feature | IRO (Gen 3) | SmartSearchEngine (Gen 3+) |
|---------|-------------|----------------------------|
| Query Understanding | Synonym expansion | **Intent classification** |
| Re-ranking | LLM/heuristic | **Intent-aware boosting** |
| Output | Raw documents | **`ask()` for Q&A generation** |
| Chunking | Semantic boundaries | **Search-and-chunk pipeline** |
| Use Case | General retrieval | **RAG-optimized retrieval** |

### Query Intent Classification

The QueryAnalyzer classifies queries into 6 intents:

| Intent | Example Queries | Retrieval Strategy |
|--------|-----------------|-------------------|
| CODE_SEARCH | "function authenticate", "class User" | Boost code, find implementations |
| HOW_TO | "How do I use...", "tutorial for..." | Boost docs/examples, expand with "usage" |
| TROUBLESHOOT | "error in...", "why doesn't X work" | Boost code + conversations, add "fix" |
| REFERENCE | "API for...", "what are the parameters" | Boost docs, filter to reference |
| CONCEPT | "AtomRuntime", "workflow engine" | Balanced, expand to "what is X" |
| EXPLORATORY | Open-ended questions | All sources, maximum expansion |

### Architecture

```
User Query ──▶ QueryAnalyzer ──▶ Intent + Expanded Queries
                     │
                     ├── Intent Classification (pattern matching)
                     ├── Query Expansion (synonyms, intent-specific)
                     └── Strategy Selection
                           │
                           ▼
            ┌──────────────────────────────┐
            │    Parallel Fan-Out Search    │
            │                               │
            │   Query₁ ──▶ Chroma ──┐       │
            │   Query₂ ──▶ Chroma ──┼──▶ Candidates
            │   Query₃ ──▶ Chroma ──┘       │
            │   (concurrent threads)        │
            └──────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │     Intent-Aware Re-Ranking   │
            │                               │
            │   • Type boost (code for CODE_SEARCH)
            │   • Keyword overlap scoring
            │   • Recency weighting (conversations)
            │   • Code quality heuristics
            └──────────────────────────────┘
                           │
                           ▼
                    Ranked Results
```

### Usage Examples

```python
from cc_atoms.tools.multi_db_agent import SmartSearchEngine

engine = SmartSearchEngine()

# Smart search with intent detection
response = engine.search("How do I use AtomRuntime?")
print(f"Intent: {response.intent}")  # HOW_TO
print(f"Expanded: {response.expanded_queries}")  # ['how do i use atomruntime', 'atomruntime example', ...]

# Direct Q&A (like ChatGPT with your codebase)
answer = engine.ask("What Python projects exist in this codebase?")
print(answer)  # Generated answer with file references

# Search with type filter
results = engine.search("authentication", doc_types=["code"])

# Get chunks for RAG
chunks = engine.search_and_chunk("GUI automation", chunk_size=1000)
for chunk in chunks:
    print(f"{chunk['relative_path']}: {chunk['content'][:100]}...")
```

### CLI Commands

```bash
smart-search search "How do I use AtomRuntime?"     # Intent-aware search
smart-search search "authentication" --type code   # Filter by type
smart-search search "bug fix" --no-rerank          # Disable re-ranking
smart-search ask "What Python projects exist?"     # Q&A mode
smart-search chunks "GUI automation"               # Get chunked results
```

### Files Created

```
src/cc_atoms/tools/multi_db_agent/smart_search.py   # Main implementation (~750 lines)
```

### Key Classes

- `SmartSearchEngine` - Main orchestrator with `search()`, `ask()`, `search_and_chunk()`
- `QueryAnalyzer` - Intent classification + query expansion
- `QueryIntent` - Enum of 6 query types
- `ReRanker` - Intent-aware relevance scoring
- `SmartChunker` - Code/doc-aware chunking with semantic boundaries
- `SearchResponse` - Rich result with intent, expanded queries, metadata

### What Makes This "Next Level"

1. **Intent Classification**: Different queries get different treatment
2. **Intent-Aware Boosting**: Code results for code queries, docs for how-to queries
3. **Q&A Generation**: `ask()` method generates answers from search results
4. **RAG-Ready**: `search_and_chunk()` prepares context for LLM consumption
5. **Recency Awareness**: Recent conversations weighted higher for troubleshooting
6. **Code Quality Signals**: Prefer well-documented code with types, docstrings

---

### Guidance for Generation 4

The SmartSearchEngine makes retrieval intent-aware, but there's room for deeper evolution:

1. **Adaptive Strategy Learning**: Track which strategies work for which queries, learn over time
2. **Multi-hop Retrieval**: "Find code that uses X, then find tests for that code"
3. **Conversational Context**: Use chat history to improve retrieval
4. **Cross-Document Reasoning**: Synthesize answers from multiple related documents
5. **Active Learning**: Ask clarifying questions when intent is ambiguous

---

---

## GENERATION 3 EVOLUTION: Intelligent Retrieval Orchestrator (IRO)

### What Was Built

The **Intelligent Retrieval Orchestrator** (`intelligent_retrieval.py`) is the NEXT LEVEL abstraction for data retrieval.

**The Key Insight:** Previous generations built excellent orchestration (CapabilityRegistry → WorkflowEngine) but the actual *retrieval* was primitive - single-shot queries with no expansion, re-ranking, or hybrid scoring. Gen 3 makes the system actually smart at *finding* information.

### What the Intelligent Retrieval Provides

| Feature | HomeIndexer (Previous) | IntelligentRetrieval (Gen 3) |
|---------|------------------------|------------------------------|
| Query Handling | Single query | **Query expansion** |
| Search Pattern | Sequential | **Parallel fan-out** |
| Scoring | Vector distance only | **Hybrid (vector + BM25)** |
| Result Quality | Raw order | **Cross-encoder re-ranking** |
| Chunking | Naive truncation | **Semantic boundaries** |
| Deduplication | None | **Content-hash dedup** |
| Explainability | None | **Full search explanation** |

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Intelligent Retrieval Orchestrator                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Query Processor                                                         │
│  ├── QueryExpander       → Synonyms, reformulations, keyword extraction │
│  ├── SmartChunker        → Semantic boundary detection (code/prose)     │
│  └── Query Decomposer    → Complex query → sub-queries (future)         │
│                                                                          │
│  Retrieval Engine                                                        │
│  ├── Parallel Fan-out    → Search N queries × M sources concurrently    │
│  ├── Hybrid Search       → Vector similarity + BM25 keyword scoring     │
│  └── Content Dedup       → Hash-based duplicate removal                 │
│                                                                          │
│  Re-ranking Pipeline                                                     │
│  ├── CrossEncoderReranker → Gemini LLM or heuristic relevance scoring  │
│  ├── KeywordScorer        → BM25-style term frequency scoring          │
│  └── Score Fusion         → Combine vector + keyword + rerank signals   │
└─────────────────────────────────────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
    ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
    │  Code Files   │           │  Documents    │           │ Conversations │
    │  (Chroma)     │           │  (Chroma)     │           │  (Chroma)     │
    └───────────────┘           └───────────────┘           └───────────────┘
```

### Usage Examples

```python
from cc_atoms.tools.multi_db_agent import IntelligentRetrieval

iro = IntelligentRetrieval()

# Simple search - all enhancements enabled by default
result = iro.search("authentication security")

# Advanced search with options
result = iro.search(
    query="how does user login work",
    expand=True,           # Generate query variations
    rerank=True,           # Cross-encoder re-ranking
    hybrid=True,           # Vector + keyword fusion
    sources=["code", "docs", "conversations"],
    top_k=20,              # Candidates per source
    final_k=5              # After re-ranking
)

# Get human-readable explanation
print(iro.explain_search(result))

# Access individual components
from cc_atoms.tools.multi_db_agent import QueryExpander, SmartChunker
expander = QueryExpander()
print(expander.expand("auth"))  # ['auth', 'authentication', 'login', ...]

chunker = SmartChunker(chunk_size=1000, overlap=200)
chunks = chunker.chunk(code_text, is_code=True)  # Respects function boundaries
```

### CLI Commands

```bash
iro search "authentication security"              # Smart search
iro search "api endpoints" --sources code         # Filter by type
iro search "how to deploy" --no-expand            # Disable expansion
iro search "bugs" --top-k 30 --final-k 10         # More candidates
iro explain "database connection"                 # Search with explanation
```

### Files Created

```
src/cc_atoms/tools/multi_db_agent/intelligent_retrieval.py  # Main implementation (700+ lines)
```

### Key Classes

- `IntelligentRetrieval` - Main orchestrator with search() and explain_search()
- `QueryExpander` - Generates synonyms, reformulations, keyword variants
- `SmartChunker` - Semantic boundary detection for code and prose
- `KeywordScorer` - BM25-style scoring for hybrid search
- `CrossEncoderReranker` - Deep relevance scoring (Gemini or heuristic)
- `RetrievedDocument` - Document with multi-signal scores
- `SearchResult` - Complete search result with metadata

### What Makes This "Next Level"

1. **Parallel Fan-out**: Query N variations × M sources concurrently via ThreadPoolExecutor
2. **Query Expansion**: Auto-generates synonyms (auth→authentication), reformulations (X→"how does X work")
3. **Hybrid Scoring**: Combines vector similarity (semantic) with BM25 (keyword) for best of both
4. **Cross-Encoder Re-ranking**: Uses Gemini to score query-document relevance (falls back to heuristic)
5. **Smart Chunking**: Respects semantic boundaries (function definitions, paragraphs) with configurable overlap
6. **Content Deduplication**: Hash-based removal of duplicate content across query variants
7. **Full Explainability**: `explain_search()` shows exactly what the system did

### Guidance for Generation 4

The retrieval layer is now intelligent. The next evolution could be:

1. **Retrieval-Augmented Generation (RAG)**: Integrate IRO with AtomRuntime for context-aware responses
2. **Query Understanding**: NLU to decompose complex queries ("find auth code and analyze for vulnerabilities")
3. **Learned Re-ranking**: Train a small model on user feedback for personalized ranking
4. **Multi-Modal Retrieval**: Add image/diagram search to code understanding
5. **Federated Search**: Extend beyond local Chroma to external sources (GitHub, docs sites)

---

## GENERATION 2 EVOLUTION: Workflow Engine

### What Was Built

The **Workflow Engine** (`workflow_engine.py`) is the NEXT LEVEL abstraction above the CapabilityRegistry.

**The Key Insight:** The previous generation (Gen 1) built CapabilityRegistry which provides discovery and tracking, but its composition was simplistic - just sequential steps. Gen 2 adds intelligent DAG-based workflow orchestration.

### What the Workflow Engine Provides

| Feature | CapabilityRegistry (Gen 1) | WorkflowEngine (Gen 2) |
|---------|---------------------------|------------------------|
| Discovery | ✓ | Uses Registry |
| Tracking | ✓ | Uses Registry |
| Composition | Sequential only | **DAG with parallel** |
| Branching | None | **Conditional if/else** |
| Retry | Per-capability | **Smart fallbacks** |
| Context | None | **Shared across steps** |
| Optimization | None | **Learns from history** |
| Auto-compose | None | **From natural language** |

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       Workflow Engine                          │
├────────────────────────────────────────────────────────────────┤
│  • DAG Builder      → Constructs execution graph               │
│  • Parallel Runner  → Executes independent steps concurrently  │
│  • Branch Handler   → Evaluates conditions, routes execution   │
│  • Context Manager  → Shares state across steps                │
│  • Optimizer        → Learns from history, suggests changes    │
│  • Auto-Composer    → Builds workflows from natural language   │
└────────────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
        ┌──────────────┐              ┌──────────────┐
        │  Capability  │              │   Workflow   │
        │   Registry   │              │    Store     │
        └──────────────┘              └──────────────┘
```

### Usage Examples

```python
from cc_atoms.tools.multi_db_agent import WorkflowEngine, Workflow

engine = WorkflowEngine()

# Create workflow with PARALLEL execution
wf = engine.create_workflow("multi-search", "Search multiple sources in parallel")
wf.add_step("search_code", capability="data-agent", params={"query": "{input}", "type": "code"})
wf.add_step("search_docs", capability="data-agent", params={"query": "{input}", "type": "document"})
wf.add_step("combine", capability="atom_runtime", params={"task": "Combine: {search_code.output} + {search_docs.output}"})
wf.add_edge("search_code", "combine")
wf.add_edge("search_docs", "combine")
# search_code and search_docs run IN PARALLEL, then combine runs

# Auto-compose from natural language
wf = engine.compose("search for auth code, analyze for vulnerabilities, generate report")

# Execute
result = engine.execute(wf, input="authentication")

# Get optimization suggestions
suggestions = engine.optimize(wf)
```

### CLI Commands

```bash
workflow-engine list                           # List all workflows
workflow-engine show my-workflow               # Show workflow details
workflow-engine compose "search, analyze"      # Auto-compose from description
workflow-engine run my-workflow --input "foo"  # Execute workflow
workflow-engine optimize my-workflow           # Get optimization suggestions
```

### Files Created

```
src/cc_atoms/tools/multi_db_agent/workflow_engine.py  # Main implementation (900+ lines)
```

### Key Classes

- `WorkflowEngine` - Main orchestrator
- `Workflow` - DAG of steps with edges
- `WorkflowStep` - Individual step with capability, params, retry config
- `WorkflowContext` - Shared state with template resolution ({step.output})
- `WorkflowResult` - Execution result with step-by-step tracking
- `StepStatus` / `NodeType` - Status and node type enums

### What Makes This "Next Level"

1. **Parallel Execution**: Steps without dependencies run concurrently
2. **Template Resolution**: `{input}`, `{step.output}`, `{var.name}` placeholders
3. **Conditional Branching**: Route execution based on step outputs
4. **Smart Retry**: Per-step retry with fallback capabilities
5. **Topological Sorting**: Automatically orders steps for optimal execution
6. **Cycle Detection**: Validates DAGs, prevents infinite loops
7. **History Tracking**: Records execution for optimization analysis
8. **Natural Language Composition**: Builds workflows from task descriptions

---

### Guidance for Generation 3

Use the WorkflowEngine to orchestrate complex multi-step tasks. The next evolution could be:

1. **Self-Healing Workflows**: Auto-modify workflows based on failure patterns
2. **Workflow Templates**: Pre-built workflows for common tasks
3. **Distributed Execution**: Run steps across multiple machines/processes
4. **Visual Workflow Editor**: GUI for building workflows
5. **LLM-Driven Optimization**: Use AI to improve workflow structure

---

---

## What is cc_atoms?

An autonomous orchestration system for Claude Code that:
- Runs iterative AI sessions (up to 25 iterations)
- Accumulates context via `claude -c`
- Provides embeddable `atom_core` library for building tools
- Includes specialized tools for GUI automation, knowledge base sync, multi-db queries
- Home directory indexing with semantic search and conversational AI
- Smart memory context injection - AtomRuntime automatically checks indexed memory and injects relevant context only when pertinent (relevance score > 0.50)
- **NEW:** Autonomous Data Agent - self-managing agent that can re-index, answer questions, and perform automated actions on ~/*

**Key concept:** An "atom" is an autonomous Claude session that can use tools, spawn sub-atoms, and iterate until a task is complete.

---

## Current State: FULLY WORKING + AUTONOMOUS DATA AGENT

Everything is functional and tested:
- **33+ automated tests passing**
- **pip installed globally** (`pip install -e .` done)
- **CLI commands:** `atom`, `atom-gui`, `gui-control`, `elysia-sync`, `multi-db-agent`, `home-indexer`, `conversational-agent`, `data-agent`
- **803 documents indexed** from home directory (581 code, 23 docs, 215 conversations)

---

## Complete Tool Inventory

| Tool | CLI Command | Purpose | Status |
|------|-------------|---------|--------|
| atom | `atom` | Run autonomous sessions | Working |
| atom_gui | `atom-gui` | Tkinter session monitor | Working |
| gui_control | `gui-control` | macOS GUI automation | Working, tested |
| elysia_sync | `elysia-sync` | Knowledge base sync to Weaviate | Working |
| multi_db_agent | `multi-db-agent` | Multi-database query routing | Working, tested |
| home_indexer | `home-indexer` | Index home directory to Chroma | Working |
| conversational_agent | `conversational-agent` | Converse about indexed data | Working |
| autonomous_agent | `data-agent` | Autonomous ~/* automation | Working |
| capability_registry | `cap-registry` | Discover/track capabilities | Working |
| workflow_engine | `workflow-engine` | DAG-based workflow composition | Working (Gen 2) |
| **intelligent_retrieval** | `iro` | **Parallel fan-out search with re-ranking** | **NEW (Gen 3)** |

---

## This Session's Complete History

### 1. News Curation Test - SUCCESSFUL

Ran `gui-control` with complex task: open Chrome, get 30 news articles, summarize, email.

**Command used:**
```bash
gui-control "
Open Google Chrome with the profile associated with tonyacronyjabroni@gmail.com.
The profile directory is 'Profile 5' (verified from Chrome's Local State file).
Use: open -na 'Google Chrome' --args --profile-directory='Profile 5'

Go to Google News (news.google.com).
Open 30 different news articles in tabs.

For each article, create a 2-paragraph summary...
Save all summaries to /tmp/news_summaries.txt...
Then compose an email in Gmail...
" --verbose --max-iterations 25
```

**Results:**
- Duration: ~31 minutes
- Chrome opened with correct profile (Profile 5)
- 22 unique articles summarized (some duplicates filtered)
- Summaries saved to `/tmp/news_summaries.txt` (207 lines)
- **Email sent via macOS Mail** (pivoted when Gmail required re-auth)
- Tab count went: 46 → 68 → 83 → 101 during article opening

**Key insight:** Including "think laterally" and fallback strategies in prompts helps the agent adapt when things fail.

**Documentation:** `tests/test_gui_control_news_curation.md`

### 2. elysia_sync Tool - CREATED FROM SCRATCH

Built a personal knowledge base sync tool using Weaviate + Gemini embeddings.

**Why Gemini:** User wanted to use free tier, avoid OpenAI costs.

**Architecture challenges solved:**
- Weaviate's `text2vec-google` module requires Vertex AI (OAuth), not AI Studio (API key)
- Solution: Use manual embeddings via Gemini API, store with `vector=` parameter
- Embedded Weaviate works without Docker (auto-downloads binary)

**Files created:**
```
src/cc_atoms/tools/elysia_sync/
├── __init__.py
├── elysia_sync.py      # Main sync logic, collectors, Weaviate client
├── context_hook.py     # Atom integration for context injection
└── README.md
```

**Key classes in elysia_sync.py:**
- `ElysiaSyncConfig` - Configuration dataclass
- `ConversationCollector` - Collects from `~/.claude/projects/*.jsonl`
- `CodeCollector` - Collects code files by extension
- `DocumentsCollector` - Collects documents (.md, .txt, .pdf, etc.) - JUST ADDED
- `EmailCollector` - Collects from macOS Mail via AppleScript
- `WeaviateClient` - Handles embedded Weaviate connection
- `get_gemini_embeddings()` - Generates embeddings via Gemini API

**Synced so far:**
- 185 conversations from `~/.claude/projects/`
- 366 code files from `~/claude/`

**CLI commands:**
```bash
elysia-sync sync --sources conversations code --full
elysia-sync query "AtomRuntime"
elysia-sync context "How do I..."
```

### 3. multi_db_agent Tool - CREATED FROM DOWNLOADS

User had downloaded `multi-db-agent-guide.md` - a comprehensive guide for building a multi-database AI agent with semantic routing.

**Built based on that guide:**
```
src/cc_atoms/tools/multi_db_agent/
├── __init__.py
├── router.py           # Query classification (SQL, vector, graph, etc.)
├── orchestrator.py     # Main agent + CLI
└── connectors/
    ├── __init__.py
    ├── sql_connector.py      # SQLAlchemy-based SQL queries
    ├── vector_connector.py   # Chroma/Weaviate vector search
    └── elysia_connector.py   # Integration with elysia_sync
```

**Query types supported:**
- `sql` - "How many orders last week?"
- `vector` - "Find documents about authentication"
- `graph` - "What's the relationship between A and B?"
- `multi_source` - "Combine customer data with support tickets"
- `analytical` - "Analyze sales trends"
- `elysia` - "Search my conversations for API design"

**LLM providers for synthesis:**
- `atom` - Embedded cc_atoms (default, no extra deps)
- `gemini` - Google Gemini free tier
- `anthropic` - Claude
- `ollama` - Local models

**CLI commands:**
```bash
multi-db-agent query "Find code about authentication"
multi-db-agent query "How many users?" --type sql
multi-db-agent interactive
```

---

## Directory Structure

```
~/claude/cc/
├── src/cc_atoms/
│   ├── __init__.py
│   ├── cli.py              # Main atom CLI
│   ├── config.py           # Central configuration
│   ├── atom_core/          # Embeddable orchestration library
│   │   ├── __init__.py
│   │   ├── runtime.py      # AtomRuntime class
│   │   └── ...
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── atom_gui/       # Tkinter session monitor
│   │   ├── atom_create_tool/
│   │   ├── atom_session_analyzer/
│   │   ├── gui_control/    # macOS GUI automation
│   │   │   ├── gui_control.py
│   │   │   ├── mac_gui_control.py  # AppleScript/cliclick integration
│   │   │   └── GUI_CONTROL_PROMPT.md
│   │   ├── elysia_sync/    # Knowledge base sync (NEW)
│   │   │   ├── elysia_sync.py
│   │   │   ├── context_hook.py
│   │   │   └── README.md
│   │   └── multi_db_agent/ # Multi-DB queries (NEW)
│   │       ├── router.py
│   │       ├── orchestrator.py
│   │       └── connectors/
│   └── prompts/
│       └── ATOM.md         # Main atom system prompt
├── tests/
│   ├── run_all_tests.py
│   ├── test_atom.py
│   ├── test_integration.py
│   ├── test_gui_control_live.md
│   └── test_gui_control_news_curation.md  # NEW
├── pyproject.toml          # pip packaging
├── HANDOFF.md              # This file
├── README.md
└── ARCHITECTURE.md
```

---

## Key Code Patterns

### Using AtomRuntime (embedded atom)
```python
from cc_atoms.atom_core import AtomRuntime

runtime = AtomRuntime.create_ephemeral(
    system_prompt="You are a helpful assistant...",
    max_iterations=10,
    verbose=True
)

result = runtime.run("Do something complex")
print(result.get("output", ""))
```

### Using gui-control programmatically
```python
from cc_atoms.tools.gui_control import run_gui_control

result = run_gui_control(
    task="Open Safari and go to google.com",
    max_iterations=10,
    verbose=True
)
```

### Using elysia_sync
```python
from cc_atoms.tools.elysia_sync import sync_to_elysia, query_elysia

# Sync
sync_to_elysia(sources=['conversations', 'code'], incremental=True)

# Query
results = query_elysia("AtomRuntime")
for doc in results:
    print(doc['source'], doc['content'][:100])
```

### Using multi_db_agent
```python
from cc_atoms.tools.multi_db_agent import create_agent

agent = create_agent(llm_provider="gemini")
agent.register_vector({
    "docs": {"store_type": "chroma", "persist_dir": "/tmp/chroma"}
})

result = agent.query("Find documents about authentication")
print(result.answer)
```

### Generating Gemini embeddings
```python
from cc_atoms.tools.elysia_sync.elysia_sync import get_gemini_embeddings
import os

embeddings = get_gemini_embeddings(
    texts=["Hello world", "Another text"],
    api_key=os.getenv("GEMINI_API_KEY"),
    model="text-embedding-004"
)
# Returns list of 768-dim vectors
```

---

## Environment Variables

```bash
# Required for Gemini embeddings (free tier)
export GEMINI_API_KEY=your-key

# Elysia/Weaviate defaults
export WEAVIATE_EMBEDDED=true       # Use embedded Weaviate (no Docker)
export WEAVIATE_IS_LOCAL=true
export ELYSIA_EMBEDDING_PROVIDER=gemini

# Optional
export ANTHROPIC_API_KEY=...        # For Claude in multi_db_agent
export OPENAI_API_KEY=...           # For OpenAI embeddings
```

---

## Data Locations

| Data | Location |
|------|----------|
| Weaviate database | `~/.local/share/weaviate-elysia/` |
| Sync state | `~/.claude/elysia_sync_state.json` |
| Claude conversations | `~/.claude/projects/` |
| Chroma (if used) | Configurable, e.g. `/tmp/chroma_db` |

---

## NEW: Autonomous Data Agent (data-agent) ✓

**Goal:** Self-managing agent for automated interaction with all data in ~/* recursive.

### Capabilities

1. **ask** - Fast semantic search + Gemini response for questions
2. **act** - Complex multi-step tasks via embedded AtomRuntime
3. **search** - Direct search with type filtering (code/document/conversation)
4. **sync** - Incremental re-indexing with change detection
5. **duplicates** - Find duplicate files by content or name
6. **daemon** - Continuous autonomous monitoring mode

### CLI Commands

```bash
# Ask questions about your data
~/claude/cc/bin/data-agent ask "What Python projects do I have?"

# Perform complex actions (uses embedded atom)
~/claude/cc/bin/data-agent act "Find all TODO comments and create a summary"

# Search indexed content
~/claude/cc/bin/data-agent search "authentication" --type code

# Sync index with file changes (incremental)
~/claude/cc/bin/data-agent sync

# Force full re-index
~/claude/cc/bin/data-agent sync --force

# Find duplicate files
~/claude/cc/bin/data-agent duplicates --directory ~/Documents

# Show statistics
~/claude/cc/bin/data-agent stats

# Run autonomous daemon (checks every 30 min)
~/claude/cc/bin/data-agent daemon --interval 30
```

### Python Usage

```python
from cc_atoms.tools.multi_db_agent import AutonomousDataAgent

agent = AutonomousDataAgent(verbose=True)

# Ask questions
response = agent.ask("What have I been working on?")

# Perform complex actions (uses AtomRuntime)
result = agent.act("Analyze my Python code for potential issues")
print(result.output)

# Search with filtering
results = agent.search("GUI automation", doc_type="code")

# Sync index
stats = agent.sync()  # Incremental
stats = agent.sync(force=True)  # Full reindex

# Find duplicates
duplicates = agent.find_duplicates(directory=Path.home() / "Downloads")

# Start autonomous monitoring (background thread)
agent.start_daemon(interval_minutes=30)
```

### Architecture

- Uses `HomeIndexer` for Chroma vector search (Gemini embeddings)
- Uses `AtomRuntime.create_ephemeral()` for complex multi-step actions
- Uses Gemini 2.0 Flash for fast conversational responses
- Change detection via mtime tracking (state persisted to `~/.cache/multi_db_agent/agent_state.json`)

### Files Created

```
src/cc_atoms/tools/multi_db_agent/autonomous_agent.py  # Main implementation
bin/data-agent                                          # Wrapper script for chromadb venv
```

---

## COMPLETED TASK: multi_db_agent with Chroma Indexing ✓

**Goal Achieved:** Built and tested home directory indexing with Chroma and conversational AI.

### What Was Built

1. **HomeIndexer** (`home_indexer.py`) - Indexes home directory to Chroma
   - Collects code files from ~/claude, ~/Projects
   - Collects documents from ~/Documents, ~/Desktop, ~/Downloads
   - Collects Claude conversations from ~/.claude/projects/
   - Uses Gemini embeddings (768 dimensions, text-embedding-004)
   - Persists to `~/.cache/multi_db_agent/home_index/`

2. **ConversationalAgent** (`conversational_agent.py`) - Converse about indexed data
   - Searches the Chroma index using Gemini embeddings
   - Uses Gemini 2.0 Flash for response generation
   - Provides contextual answers about your files, projects, conversations

3. **VectorConnector Updates** - Auto-detects Gemini embeddings
   - Added `embedding_provider` parameter ("auto", "gemini", "default")
   - Auto-detects 768-dim embeddings and switches to Gemini
   - Uses `get_gemini_embedding()` for queries when needed

### Results

```
Indexed:
- 511 code files
- 23 documents
- 205 conversations
- 739 total documents
- Time: ~4.5 minutes
```

### Usage Examples

```python
# Index home directory
from cc_atoms.tools.multi_db_agent import HomeIndexer
indexer = HomeIndexer(verbose=True)
indexer.index_all()

# Query the index
results = indexer.query("GUI automation", top_k=5)

# Use conversational agent
from cc_atoms.tools.multi_db_agent import create_conversational_agent
agent = create_conversational_agent()
response = agent.ask("What Python projects do I have?")
print(response)

# Use multi_db_agent with home index
from cc_atoms.tools.multi_db_agent import MultiDBAgent
agent = MultiDBAgent(llm_provider="gemini", verbose=True)
agent.register_vector({
    "home": {
        "store_type": "chroma",
        "persist_dir": "~/.cache/multi_db_agent/home_index",
        "collection_name": "home_directory",
        "embedding_provider": "gemini",
    }
})
result = agent.query("Find code about authentication")
```

### CLI Commands

```bash
# Index home directory
home-indexer index

# Query indexed content
home-indexer query "Python projects"

# Show stats
home-indexer stats

# Conversational mode
conversational-agent --interactive

# Ask a question
conversational-agent "What have I been working on?"
```

### Python Version Note

**IMPORTANT:** Chromadb requires Python 3.9 (onnxruntime not available for 3.14).

**Solution:** A dedicated venv at `~/.venvs/chromadb-env/` with wrapper scripts:

```bash
# Venv location
~/.venvs/chromadb-env/

# Wrapper scripts (use these from anywhere)
~/claude/cc/bin/home-indexer stats
~/claude/cc/bin/home-indexer index
~/claude/cc/bin/home-indexer query "Python projects"

~/claude/cc/bin/conversational-agent "What projects do I have?"
~/claude/cc/bin/conversational-agent --interactive
```

**To recreate the venv if needed:**
```bash
/usr/bin/python3 -m venv ~/.venvs/chromadb-env
~/.venvs/chromadb-env/bin/pip install --upgrade pip
~/.venvs/chromadb-env/bin/pip install chromadb
~/.venvs/chromadb-env/bin/pip install -e ~/claude/cc
```

**Add to PATH (optional):**
```bash
export PATH="$HOME/claude/cc/bin:$PATH"
```

---

## NEW: AtomRuntime Memory Integration ✓

The `AtomRuntime` now automatically checks the indexed memory before responding. When the user's prompt is related to something in the index, relevant context is injected into the system prompt.

### How It Works

1. When `AtomRuntime.run()` is called with a user prompt
2. The `MemoryProvider` queries the Chroma index using Gemini embeddings
3. If any documents have relevance score > 0.50, they're injected as context
4. The enhanced system prompt is used for the first iteration

### Key Features

- **Smart triggering**: Only activates when relevant (unrelated prompts ignored)
- **Threshold tuning**: 0.50 relevance threshold prevents false positives
- **Minimum length**: Prompts < 10 chars are skipped
- **Auto-detection**: Memory is auto-enabled if the index exists
- **Subprocess isolation**: Uses the chromadb venv automatically

### Test Results (all passing)

```
✓ Empty prompt: NOT triggered (correct)
✓ "What is the capital of France?": NOT triggered (correct)
✓ "How do I bake cookies?": NOT triggered (correct)
✓ "EXIT_LOOP_NOW signal": TRIGGERED (score: 0.713)
✓ "AtomRuntime create ephemeral": TRIGGERED (score: 0.614)
✓ "fix bug in RetryManager class": TRIGGERED (score: 0.656)
✓ "Help me with musicbrainz database": TRIGGERED (score: 0.705)
```

### Usage

```python
from cc_atoms.atom_core import AtomRuntime

# Memory is auto-enabled if index exists
runtime = AtomRuntime(
    system_prompt="You are a helpful assistant.",
    conversation_dir=Path("/tmp/my-task"),
    use_memory=None,  # Auto-detect (default)
    memory_threshold=0.50,  # Relevance threshold
)

# Run - memory context injected if relevant
result = runtime.run("Help me with the musicbrainz database setup")
print(f"Memory used: {result['memory_used']}")
```

### Files Created

- `src/cc_atoms/atom_core/memory.py` - MemoryProvider class
- Updated `src/cc_atoms/atom_core/runtime.py` - Memory integration
- Updated `src/cc_atoms/atom_core/__init__.py` - Exports

---

## Quick Command Reference

```bash
# Run all tests
/opt/homebrew/bin/python3 tests/run_all_tests.py

# Sync knowledge base (elysia)
elysia-sync sync --sources conversations code --full

# Query elysia
elysia-sync query "AtomRuntime"

# Multi-DB query
multi-db-agent query "Find code about authentication"

# Interactive mode
multi-db-agent interactive

# GUI control
gui-control "Open Safari" --verbose

# Check Chrome profiles
cat ~/Library/Application\ Support/Google/Chrome/Local\ State | python3 -c "import json,sys; d=json.load(sys.stdin); profiles=d.get('profile',{}).get('info_cache',{}); [print(f'{k}: {v.get(\"name\")} - {v.get(\"user_name\")}') for k,v in profiles.items()]"
```

---

## Troubleshooting

### Weaviate embedded issues
```bash
# Clear Weaviate data and start fresh
rm -rf ~/.local/share/weaviate-elysia
rm -f ~/.claude/elysia_sync_state.json
```

### Gemini rate limits
- Batch embeddings in groups of 20
- Add `time.sleep(0.5)` between batches
- The code in `add_documents()` already does this

### Import errors
```bash
# Reinstall package
cd ~/claude/cc
/opt/homebrew/bin/python3 -m pip install -e . --break-system-packages
```

### Chrome profile not found
- Profile 5 = tonyacronyjabroni@gmail.com
- Use: `open -na 'Google Chrome' --args --profile-directory='Profile 5'`

---

## User Preferences

- Uses Gemini free tier (avoid OpenAI costs)
- Wants comprehensive indexing of home directory
- Values autonomous, lateral-thinking agents
- Has extensive Claude conversation history in `~/.claude/projects/`
- Prefers thorough documentation and tests

---

## Key Insights from This Session

1. **Embedded Weaviate works well** - No Docker needed, auto-downloads binary
2. **Gemini free tier embeddings** - Work great, 768-dim vectors from text-embedding-004
3. **gui-control lateral thinking** - Including fallback strategies in prompts helps a lot
4. **Mail.app fallback** - When Gmail blocks, macOS Mail works if account is linked
5. **Manual embeddings bypass auth issues** - Weaviate's Google module wants Vertex AI OAuth, but we can generate embeddings ourselves and pass them directly

---

## Important Technical Notes

1. **Use homebrew Python:** `/opt/homebrew/bin/python3` (system python has issues)
2. **Package is editable install:** Changes to `src/` take effect immediately
3. **Weaviate data persists:** Located at `~/.local/share/weaviate-elysia/`
4. **Gemini embedding dimensions:** 768 (text-embedding-004 model)
5. **Chroma is simpler:** No server needed, just `pip install chromadb`

---

## Files Modified This Session

- `src/cc_atoms/tools/elysia_sync/` - Created entirely
- `src/cc_atoms/tools/multi_db_agent/` - Created entirely
- `src/cc_atoms/tools/__init__.py` - Updated tool list
- `pyproject.toml` - Added CLI entries and optional deps
- `tests/test_gui_control_news_curation.md` - Created

---

Read this, understand the architecture and code patterns, and continue with the multi_db_agent + Chroma indexing task.
