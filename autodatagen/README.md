# Home Oracle

## Overview

**Home Oracle** is an autonomous retrieval-augmented agent that uses your entire home directory as its knowledge base. It combines semantic search with iterative reasoning to provide accurate, contextual answers to any question about your files, code, documents, and past Claude conversations.

## Status
COMPLETE

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Home Oracle                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  User Prompt ──────────▶  Oracle Agent (AtomRuntime)             │
│                           │                                      │
│                           ├── 1. Intent Analysis                 │
│                           │   "What is the user really asking?"  │
│                           │                                      │
│                           ├── 2. Query Planning                  │
│                           │   "What do I need to find?"          │
│                           │                                      │
│                           ├── 3. Iterative Retrieval            │
│                           │   ┌─────────────────────────────┐   │
│                           │   │  Loop until satisfied:       │   │
│                           │   │  • Search home index         │   │
│                           │   │  • Evaluate relevance        │   │
│                           │   │  • Decide: more search or    │   │
│                           │   │    enough context?           │   │
│                           │   └─────────────────────────────┘   │
│                           │                                      │
│                           ├── 4. Synthesis                       │
│                           │   "Generate answer from context"     │
│                           │                                      │
│                           └── 5. Source Attribution              │
│                               "Cite files and conversations"     │
│                                                                   │
│                    ▼                                             │
│             Rich Answer                                          │
│             • Answer text                                        │
│             • Source citations                                   │
│             • Confidence level                                   │
│             • Follow-up suggestions                              │
└──────────────────────────────────────────────────────────────────┘
```

## Key Innovation

Unlike simple RAG systems that do one search and generate, Home Oracle uses an **iterative retrieval loop**:

1. **First pass**: Broad search based on user query
2. **Analysis**: What's missing? What related topics should I explore?
3. **Second pass**: Targeted searches for gaps
4. **Repeat**: Until confidence threshold met or max iterations
5. **Synthesize**: Generate comprehensive answer from all gathered context

This mirrors how a human expert would research a question - not just one search, but a conversation with the knowledge base.

## Components

### 1. HomeIndexer (Existing)
- Indexes all files in ~/ to Chroma vector store
- Uses Gemini embeddings (text-embedding-004)
- Indexes: code, documents, Claude conversations
- Location: `~/.cache/multi_db_agent/home_index`

### 2. SmartSearchEngine (Existing)
- Intent classification
- Query expansion
- Parallel fan-out search
- Re-ranking for precision

### 3. OracleAgent (New)
- Wraps AtomRuntime for iterative reasoning
- Manages the retrieval loop
- Decides when enough context is gathered
- Generates final synthesis

### 4. CLI (New)
- Simple interface: `home_oracle "your question"`
- Options for verbosity, max queries, output format

## Usage

```bash
# Ask a question (iterative retrieval)
home_oracle "What is the architecture of cc_atoms?"

# Quick single-search mode
home_oracle --quick "Where is AtomRuntime defined?"

# Verbose mode (show all searches)
home_oracle -v "How do I create a new atom tool?"

# JSON output for piping
home_oracle --json "What Python projects do I have?"
```

## Progress
- [x] Research cc_atoms codebase and existing components
- [x] Design architecture (this README)
- [x] Implement OracleAgent class
- [x] Create CLI interface
- [x] Add iterative retrieval loop
- [x] Test with various queries
- [x] Document usage

## Current State
Implementation complete with:
- `home_oracle.py` - Main implementation with OracleAgent, OracleSearch, and CLI
- Leverages existing HomeIndexer and SmartSearchEngine from cc_atoms
- Uses Gemini API for both embeddings and generation

## Quick Start

```bash
# Ensure GEMINI_API_KEY is set
export GEMINI_API_KEY="your-key-here"

# Ensure the home index exists (run from cc_atoms)
home-indexer index

# Run Home Oracle
python home_oracle.py "What is AtomRuntime?"

# Quick mode (single search, faster)
python home_oracle.py --quick "Where is AtomRuntime defined?"

# Verbose mode (see search process)
python home_oracle.py -v "How do I create a new atom tool?"

# JSON output
python home_oracle.py --json "What Python projects do I have?"
```

## Decisions
- **Embedding model**: Gemini text-embedding-004 (consistent with existing home index)
- **Vector store**: Chroma (reuses existing home_directory collection)
- **Generation model**: Gemini 2.0 Flash for synthesis (fast, high quality)
- **Search backend**: SmartSearchEngine (Gen 3 retrieval with query expansion, parallel fan-out, re-ranking)
- **Fallback chain**: SmartSearchEngine → HomeIndexer → Direct Chroma

## Tested Queries

1. **Concept query**: "What is AtomRuntime?" - 83% confidence, 1 iteration, accurate response
2. **How-to query**: "How do I create a new atom tool?" - 70% confidence, 1 iteration, comprehensive steps
3. **Exploratory query**: "What files and conversations exist related to multi_db_agent?" - 70% confidence, comprehensive overview with source citations

## File Structure

```
autodatagen/
├── README.md           # This file
├── home_oracle.py      # Main implementation
└── tests/
    ├── test_home_oracle.py  # Pytest tests
    └── run_tests.py         # Simple test runner (no pytest needed)
```

## How It Works

1. **OracleSearch** - Backend that connects to the existing home index:
   - Tries SmartSearchEngine first (best - has query expansion, parallel search, re-ranking)
   - Falls back to HomeIndexer if needed
   - Final fallback to direct Chroma queries

2. **OracleAgent** - The brain that manages iterative retrieval:
   - Analyzes the question and executes initial search
   - Uses Gemini to evaluate confidence and plan follow-up queries
   - Iterates until confident or max iterations reached
   - Synthesizes final answer from all gathered context

3. **CLI** - Simple command-line interface:
   - `--quick` for fast single-search mode
   - `--verbose` to see the search process
   - `--json` for programmatic usage

## Integration with cc_atoms

Home Oracle builds on top of the existing cc_atoms infrastructure:
- Uses the same Chroma index created by `home-indexer`
- Uses the same Gemini embedding model (text-embedding-004)
- Leverages SmartSearchEngine's query expansion and re-ranking
- Can be extended to use AtomRuntime for more complex reasoning

## Installation

The tool is installed in the cc_atoms ecosystem:

```
~/cc_atoms/tools/home_oracle/
├── home_oracle.py      # Main implementation
└── README.md           # Documentation

~/cc_atoms/bin/home_oracle  # Launcher script
```

If `~/cc_atoms/bin` is in your PATH, you can run it directly:

```bash
home_oracle "What Python projects do I have?"
```
