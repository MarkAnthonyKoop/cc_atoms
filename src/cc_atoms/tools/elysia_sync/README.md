# Elysia Sync Tool

Personal knowledge base synchronization via Weaviate/Elysia.

## Overview

The `elysia_sync` tool creates a comprehensive personal knowledge base by syncing:
- **Claude Code conversations** from `~/.claude/projects/`
- **Code files** from configured directories
- **Emails** from macOS Mail app
- **Documents** from configured paths

This data is stored in Weaviate and can be queried via Elysia's agentic RAG system, enabling intelligent context injection into atom conversations.

## Installation

### Prerequisites

1. **Weaviate** - Either local or Weaviate Cloud:
   ```bash
   # Local (via Docker)
   docker run -d -p 8080:8080 -p 50051:50051 \
     -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
     -v weaviate_data:/var/lib/weaviate \
     semitechnologies/weaviate:latest

   # Or use Weaviate Cloud: https://console.weaviate.cloud/
   ```

2. **Python dependencies**:
   ```bash
   pip install cc-atoms[elysia]
   # Or manually:
   pip install weaviate-client elysia-ai
   ```

3. **Environment variables**:
   ```bash
   # For local Weaviate
   export WEAVIATE_IS_LOCAL=true

   # For Weaviate Cloud
   export WCD_URL=https://your-cluster.weaviate.cloud
   export WCD_API_KEY=your-api-key

   # For embeddings
   export OPENAI_API_KEY=your-openai-key
   ```

## CLI Usage

### Sync Data

```bash
# Sync all sources (conversations, code, emails)
elysia-sync sync

# Sync specific sources
elysia-sync sync --sources conversations code

# Full sync (not incremental)
elysia-sync sync --full

# Quiet mode
elysia-sync sync --quiet
```

### Query Knowledge Base

```bash
# Search for relevant documents
elysia-sync query "authentication implementation"

# Limit results
elysia-sync query "error handling" --limit 5
```

### Get Context for a Query

```bash
# Use embedded atom to intelligently extract context
elysia-sync context "How do I implement OAuth?"

# Verbose mode to see processing
elysia-sync context "What was the bug fix yesterday?" --verbose
```

## Python API

### Syncing Data

```python
from cc_atoms.tools.elysia_sync import sync_to_elysia, ElysiaSyncConfig

# Sync with default config
result = sync_to_elysia(sources=['conversations', 'code'])

# Custom config
config = ElysiaSyncConfig(
    weaviate_url='http://localhost:8080',
    code_paths=[Path.home() / 'projects'],
)
result = sync_to_elysia(config=config)

print(f"Synced: {result['synced']}")
```

### Querying

```python
from cc_atoms.tools.elysia_sync import query_elysia

# Simple query
results = query_elysia("database migrations")

for doc in results:
    print(f"Source: {doc['source']}")
    print(f"Content: {doc['content'][:200]}...")
```

### Context Injection

The main use case - automatically inject relevant context into atom conversations:

```python
from cc_atoms.tools.elysia_sync import (
    inject_context_into_prompt,
    create_context_aware_runtime
)

# Option 1: Inject context into a prompt
user_prompt = "Help me fix the authentication bug"
enhanced_prompt = inject_context_into_prompt(user_prompt)
# enhanced_prompt now includes relevant background from knowledge base

# Option 2: Create a context-aware runtime
runtime = create_context_aware_runtime(
    system_prompt="You are a helpful coding assistant",
    user_prompt="Implement OAuth for our app"
)
result = runtime.run(user_prompt)
```

### Using the Context Hook

For more control over context injection:

```python
from cc_atoms.tools.elysia_sync import ElysiaContextHook

hook = ElysiaContextHook()

# Check if Elysia is available
if hook.enabled:
    # Get context for a conversation
    context = hook.get_context_for_conversation(
        "The user is asking about API rate limiting"
    )

    # Quick lookup (faster, less intelligent)
    docs = hook.quick_context_lookup("rate limiting")

    # Format documents into context block
    context_block = hook.format_context_block(docs)
```

## Integration with Atom Control Flow

### Automatic Context at Startup

The `get_startup_context()` function can be called at the start of atom sessions:

```python
from cc_atoms.tools.elysia_sync import get_startup_context
from cc_atoms.atom_core import AtomRuntime

# Get context based on conversation directory
context = get_startup_context(conversation_dir=Path("/path/to/project"))

if context:
    system_prompt = f"{base_system_prompt}\n\n{context}"
else:
    system_prompt = base_system_prompt

runtime = AtomRuntime(system_prompt=system_prompt, ...)
```

### Environment Control

Disable context injection via environment variable:

```bash
export ELYSIA_CONTEXT_ENABLED=false
```

## Data Sources

### Conversations

Collected from `~/.claude/projects/`:
- JSONL conversation files
- Extracts last 50 messages per conversation
- Indexes project path, timestamps, message content

### Code

Collected from configured paths (default: `~/claude`):
- Python, JavaScript, TypeScript, Markdown, etc.
- Skips node_modules, __pycache__, .venv, etc.
- Max file size: 10MB

### Emails

Collected via AppleScript from macOS Mail:
- Subject, sender, date, content
- Up to 1000 most recent emails
- Content truncated to 2000 characters

## Collections

Data is stored in Weaviate collections:

| Collection | Description |
|------------|-------------|
| `ClaudeConversations` | Claude Code conversation history |
| `CodeFiles` | Source code files |
| `Emails` | Email messages |
| `Documents` | General documents |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      elysia_sync                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Conversation│  │    Code     │  │   Email     │        │
│  │  Collector  │  │  Collector  │  │  Collector  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          ▼                                  │
│                 ┌─────────────────┐                        │
│                 │ WeaviateClient  │                        │
│                 └────────┬────────┘                        │
│                          │                                  │
├──────────────────────────┼──────────────────────────────────┤
│                          ▼                                  │
│                 ┌─────────────────┐                        │
│                 │    Weaviate     │                        │
│                 │   (Vector DB)   │                        │
│                 └────────┬────────┘                        │
│                          │                                  │
│         ┌────────────────┼────────────────┐                │
│         ▼                ▼                ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   query_    │  │   context   │  │  Elysia     │        │
│  │   elysia    │  │   _hook     │  │  (RAG)      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

All configuration via `ElysiaSyncConfig`:

```python
@dataclass
class ElysiaSyncConfig:
    # Weaviate connection
    weaviate_url: str = 'http://localhost:8080'
    weaviate_api_key: Optional[str] = None
    is_local: bool = True

    # LLM for embeddings
    openai_api_key: Optional[str] = None

    # Data source paths
    claude_projects_dir: Path = ~/.claude/projects
    code_paths: List[Path] = [~/claude]
    documents_paths: List[Path] = [~/Documents]

    # Collection names
    conversations_collection: str = 'ClaudeConversations'
    code_collection: str = 'CodeFiles'
    emails_collection: str = 'Emails'
    documents_collection: str = 'Documents'

    # Sync settings
    max_file_size_mb: int = 10
    file_extensions: List[str] = ['.py', '.js', ...]

    # State file for incremental sync
    state_file: Path = ~/.claude/elysia_sync_state.json
```

## Use Cases

1. **"What did I work on yesterday?"** - Query conversations for recent activity
2. **"How did we implement auth?"** - Search code and conversations
3. **"What emails about the project?"** - Search email history
4. **Context-aware coding** - Automatic context injection based on current task

## Troubleshooting

### Weaviate Connection Failed

```bash
# Check if Weaviate is running
curl http://localhost:8080/v1/.well-known/ready

# Check Docker
docker ps | grep weaviate
```

### No Results from Query

1. Ensure data has been synced: `elysia-sync sync`
2. Check collection exists in Weaviate
3. Verify OpenAI API key for embeddings

### Email Collection Failed

- macOS Mail app must be running
- May need to grant Terminal accessibility permissions

## Sources

- [Elysia by Weaviate](https://github.com/weaviate/elysia)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [Weaviate Python Client](https://weaviate.io/developers/weaviate/client-libraries/python)
