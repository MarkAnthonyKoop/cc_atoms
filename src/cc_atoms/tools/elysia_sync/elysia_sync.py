#!/usr/bin/env python3
"""
Elysia Sync Tool - Personal knowledge base synchronization

Syncs data from OS to Elysia/Weaviate for RAG-based retrieval.
Uses embedded atom for intelligent data extraction and context injection.

Data Sources:
- Claude Code conversations (~/.claude/projects/)
- Code repositories (configured paths)
- Emails (via macOS Mail app or Gmail API)
- Documents (configurable paths)
- System metadata

Usage:
    from cc_atoms.tools.elysia_sync import sync_to_elysia, query_elysia

    # Sync data to Elysia
    sync_to_elysia(sources=['conversations', 'code'])

    # Query for relevant context
    context = query_elysia("What do I know about authentication?")
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from cc_atoms.atom_core import AtomRuntime


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ElysiaSyncConfig:
    """Configuration for Elysia sync operations"""

    # Weaviate connection
    weaviate_url: str = field(default_factory=lambda: os.getenv('WCD_URL', 'http://localhost:8080'))
    weaviate_api_key: Optional[str] = field(default_factory=lambda: os.getenv('WCD_API_KEY'))
    is_local: bool = field(default_factory=lambda: os.getenv('WEAVIATE_IS_LOCAL', 'true').lower() == 'true')

    # Embedding provider: 'openai', 'gemini', or 'none' (for local models)
    embedding_provider: str = field(default_factory=lambda: os.getenv('ELYSIA_EMBEDDING_PROVIDER', 'gemini'))

    # LLM API keys for embeddings
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'))

    # Gemini model for embeddings (free tier supports text-embedding-004)
    gemini_embedding_model: str = field(default_factory=lambda: os.getenv('GEMINI_EMBEDDING_MODEL', 'text-embedding-004'))

    # Data source paths
    claude_projects_dir: Path = field(default_factory=lambda: Path.home() / '.claude' / 'projects')
    code_paths: List[Path] = field(default_factory=lambda: [
        Path.home() / 'claude',
        Path.home() / 'Projects',
    ])
    documents_paths: List[Path] = field(default_factory=lambda: [
        Path.home() / 'Documents',
        Path.home() / 'Desktop',
        Path.home() / 'Downloads',
    ])

    # Document file extensions
    document_extensions: List[str] = field(default_factory=lambda: [
        '.md', '.txt', '.pdf', '.doc', '.docx', '.rtf',
        '.csv', '.json', '.xml', '.html', '.htm',
    ])

    # Collection names in Weaviate
    conversations_collection: str = 'ClaudeConversations'
    code_collection: str = 'CodeFiles'
    emails_collection: str = 'Emails'
    documents_collection: str = 'Documents'

    # Sync settings
    max_file_size_mb: int = 10
    file_extensions: List[str] = field(default_factory=lambda: [
        '.py', '.js', '.ts', '.tsx', '.jsx', '.md', '.txt', '.json', '.yaml', '.yml',
        '.sh', '.bash', '.zsh', '.html', '.css', '.sql', '.go', '.rs', '.swift'
    ])

    # State file for incremental sync
    state_file: Path = field(default_factory=lambda: Path.home() / '.claude' / 'elysia_sync_state.json')


# =============================================================================
# Data Collectors
# =============================================================================

class ConversationCollector:
    """Collects Claude Code conversation data from ~/.claude/projects/"""

    def __init__(self, config: ElysiaSyncConfig):
        self.config = config
        self.projects_dir = config.claude_projects_dir

    def collect(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Collect conversation data, optionally filtering by date"""
        documents = []

        if not self.projects_dir.exists():
            return documents

        # Iterate through project directories
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            # Find .jsonl conversation files
            for conv_file in project_dir.glob('**/*.jsonl'):
                try:
                    doc = self._process_conversation(conv_file, since)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"Warning: Failed to process {conv_file}: {e}")

        return documents

    def _process_conversation(self, conv_file: Path, since: Optional[datetime]) -> Optional[Dict[str, Any]]:
        """Process a single conversation file"""
        stat = conv_file.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)

        # Skip if older than since
        if since and mod_time < since:
            return None

        # Parse JSONL
        messages = []
        try:
            with open(conv_file, 'r') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
        except (json.JSONDecodeError, IOError):
            return None

        if not messages:
            return None

        # Extract project info from path
        # Path format: ~/.claude/projects/-Users-foo-bar-project/conv-id.jsonl
        project_path = conv_file.parent.name.replace('-', '/')
        if project_path.startswith('/'):
            project_path = project_path[1:]

        # Build document
        return {
            'id': hashlib.md5(str(conv_file).encode()).hexdigest(),
            'type': 'conversation',
            'source': str(conv_file),
            'project_path': project_path,
            'timestamp': mod_time.isoformat(),
            'message_count': len(messages),
            'content': self._extract_content(messages),
            'metadata': {
                'file_size': stat.st_size,
                'first_message': messages[0].get('content', '')[:200] if messages else '',
            }
        }

    def _extract_content(self, messages: List[Dict]) -> str:
        """Extract searchable content from messages"""
        parts = []
        for msg in messages[-50:]:  # Last 50 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, str):
                parts.append(f"[{role}]: {content[:1000]}")
        return '\n'.join(parts)


class CodeCollector:
    """Collects code files from configured paths"""

    def __init__(self, config: ElysiaSyncConfig):
        self.config = config

    def collect(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Collect code files"""
        documents = []
        max_size = self.config.max_file_size_mb * 1024 * 1024

        for code_path in self.config.code_paths:
            if not code_path.exists():
                continue

            for ext in self.config.file_extensions:
                for file_path in code_path.rglob(f'*{ext}'):
                    # Skip hidden directories and common ignore patterns
                    if any(p.startswith('.') or p in ['node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']
                           for p in file_path.parts):
                        continue

                    try:
                        doc = self._process_file(file_path, since, max_size)
                        if doc:
                            documents.append(doc)
                    except Exception as e:
                        print(f"Warning: Failed to process {file_path}: {e}")

        return documents

    def _process_file(self, file_path: Path, since: Optional[datetime], max_size: int) -> Optional[Dict[str, Any]]:
        """Process a single code file"""
        stat = file_path.stat()

        # Skip large files
        if stat.st_size > max_size:
            return None

        mod_time = datetime.fromtimestamp(stat.st_mtime)

        # Skip if older than since
        if since and mod_time < since:
            return None

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except IOError:
            return None

        return {
            'id': hashlib.md5(str(file_path).encode()).hexdigest(),
            'type': 'code',
            'source': str(file_path),
            'filename': file_path.name,
            'extension': file_path.suffix,
            'timestamp': mod_time.isoformat(),
            'content': content[:50000],  # Limit content size
            'metadata': {
                'file_size': stat.st_size,
                'line_count': content.count('\n') + 1,
                'relative_path': str(file_path.relative_to(Path.home())) if str(file_path).startswith(str(Path.home())) else str(file_path),
            }
        }


class EmailCollector:
    """Collects emails via macOS Mail app or AppleScript"""

    def __init__(self, config: ElysiaSyncConfig):
        self.config = config

    def collect(self, since: Optional[datetime] = None, max_emails: int = 1000) -> List[Dict[str, Any]]:
        """Collect recent emails using AppleScript"""
        documents = []

        # AppleScript to get emails from Mail.app
        script = '''
        tell application "Mail"
            set output to ""
            set allMessages to messages of inbox
            repeat with i from 1 to (count of allMessages)
                if i > ''' + str(max_emails) + ''' then exit repeat
                set msg to item i of allMessages
                set msgSubject to subject of msg
                set msgSender to sender of msg
                set msgDate to date received of msg
                set msgContent to content of msg
                set output to output & "---EMAIL_START---" & linefeed
                set output to output & "Subject: " & msgSubject & linefeed
                set output to output & "From: " & msgSender & linefeed
                set output to output & "Date: " & (msgDate as string) & linefeed
                set output to output & "Content: " & (text 1 thru 2000 of msgContent) & linefeed
                set output to output & "---EMAIL_END---" & linefeed
            end repeat
            return output
        end tell
        '''

        try:
            import subprocess
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                documents = self._parse_emails(result.stdout, since)
        except Exception as e:
            print(f"Warning: Email collection failed: {e}")

        return documents

    def _parse_emails(self, raw_output: str, since: Optional[datetime]) -> List[Dict[str, Any]]:
        """Parse AppleScript email output"""
        documents = []
        emails = raw_output.split('---EMAIL_START---')

        for email_text in emails:
            if '---EMAIL_END---' not in email_text:
                continue

            email_text = email_text.split('---EMAIL_END---')[0]
            lines = email_text.strip().split('\n')

            email_data = {}
            content_lines = []
            in_content = False

            for line in lines:
                if line.startswith('Subject: '):
                    email_data['subject'] = line[9:]
                elif line.startswith('From: '):
                    email_data['sender'] = line[6:]
                elif line.startswith('Date: '):
                    email_data['date'] = line[6:]
                elif line.startswith('Content: '):
                    in_content = True
                    content_lines.append(line[9:])
                elif in_content:
                    content_lines.append(line)

            if email_data.get('subject'):
                doc_id = hashlib.md5(f"{email_data.get('subject', '')}{email_data.get('date', '')}".encode()).hexdigest()
                documents.append({
                    'id': doc_id,
                    'type': 'email',
                    'source': 'macOS Mail',
                    'subject': email_data.get('subject', ''),
                    'sender': email_data.get('sender', ''),
                    'timestamp': email_data.get('date', ''),
                    'content': '\n'.join(content_lines),
                    'metadata': {}
                })

        return documents


class DocumentsCollector:
    """Collects document files from configured directories"""

    def __init__(self, config: ElysiaSyncConfig):
        self.config = config

    def collect(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Collect documents from configured paths"""
        documents = []
        max_size = self.config.max_file_size_mb * 1024 * 1024

        for docs_path in self.config.documents_paths:
            if not docs_path.exists():
                continue

            for ext in self.config.document_extensions:
                for file_path in docs_path.rglob(f'*{ext}'):
                    # Skip hidden files/directories
                    if any(p.startswith('.') for p in file_path.parts):
                        continue

                    try:
                        doc = self._process_file(file_path, since, max_size)
                        if doc:
                            documents.append(doc)
                    except Exception as e:
                        print(f"Warning: Failed to process {file_path}: {e}")

        return documents

    def _process_file(self, file_path: Path, since: Optional[datetime], max_size: int) -> Optional[Dict[str, Any]]:
        """Process a single document file"""
        stat = file_path.stat()

        # Skip large files
        if stat.st_size > max_size:
            return None

        mod_time = datetime.fromtimestamp(stat.st_mtime)

        # Skip if older than since
        if since and mod_time < since:
            return None

        # Read content based on type
        content = self._read_file_content(file_path)
        if not content:
            return None

        return {
            'id': hashlib.md5(str(file_path).encode()).hexdigest(),
            'type': 'document',
            'source': str(file_path),
            'filename': file_path.name,
            'extension': file_path.suffix,
            'timestamp': mod_time.isoformat(),
            'content': content[:50000],  # Limit content size
            'metadata': {
                'file_size': stat.st_size,
                'relative_path': str(file_path.relative_to(Path.home())) if str(file_path).startswith(str(Path.home())) else str(file_path),
            }
        }

    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content, handling different file types"""
        ext = file_path.suffix.lower()

        # Text-based files
        if ext in ['.md', '.txt', '.csv', '.json', '.xml', '.html', '.htm', '.rtf']:
            try:
                return file_path.read_text(encoding='utf-8', errors='ignore')
            except:
                return None

        # PDF files - try to extract text
        if ext == '.pdf':
            return self._extract_pdf_text(file_path)

        # Skip binary formats we can't read
        return None

    def _extract_pdf_text(self, file_path: Path) -> Optional[str]:
        """Extract text from PDF using available tools"""
        # Try pdftotext (poppler)
        try:
            import subprocess
            result = subprocess.run(
                ['pdftotext', str(file_path), '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except:
            pass

        # Fallback: just use filename as content
        return f"[PDF Document: {file_path.name}]"


# =============================================================================
# Gemini Embeddings Helper
# =============================================================================

def get_gemini_embeddings(texts: List[str], api_key: str, model: str = "text-embedding-004") -> List[List[float]]:
    """
    Generate embeddings using Gemini API.

    Args:
        texts: List of texts to embed
        api_key: Gemini API key
        model: Embedding model (default: text-embedding-004)

    Returns:
        List of embedding vectors
    """
    import urllib.request
    import urllib.error

    embeddings = []
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"

    for text in texts:
        # Truncate text if too long (Gemini has limits)
        text = text[:8000] if len(text) > 8000 else text

        payload = json.dumps({
            "model": f"models/{model}",
            "content": {"parts": [{"text": text}]}
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                embeddings.append(result.get("embedding", {}).get("values", []))
        except urllib.error.HTTPError as e:
            print(f"Embedding error: {e.code} - {e.reason}")
            embeddings.append([])  # Empty embedding for failed items
        except Exception as e:
            print(f"Embedding error: {e}")
            embeddings.append([])

    return embeddings


# =============================================================================
# Weaviate/Elysia Integration
# =============================================================================

class WeaviateClient:
    """Simple Weaviate client for data ingestion and queries"""

    def __init__(self, config: ElysiaSyncConfig):
        self.config = config
        self._client = None

    def connect(self):
        """Connect to Weaviate (supports embedded, local, and cloud)"""
        try:
            import weaviate

            # Build headers for embedding API
            headers = {}
            if self.config.embedding_provider == 'gemini' and self.config.gemini_api_key:
                headers['X-Goog-Studio-Api-Key'] = self.config.gemini_api_key
            elif self.config.embedding_provider == 'openai' and self.config.openai_api_key:
                headers['X-OpenAI-Api-Key'] = self.config.openai_api_key

            # Check for use_embedded flag (no Docker needed)
            use_embedded = os.getenv('WEAVIATE_EMBEDDED', 'true').lower() == 'true'

            if use_embedded and self.config.is_local:
                # Use embedded Weaviate (downloads binary automatically)
                from weaviate.embedded import EmbeddedOptions

                # For Gemini with AI Studio, we'll use manual embeddings (no vectorizer module)
                # This avoids the Vertex AI authentication issues
                if self.config.embedding_provider == 'gemini':
                    modules = "backup-filesystem"
                    default_vectorizer = "none"
                else:
                    modules = "text2vec-openai,backup-filesystem"
                    default_vectorizer = "text2vec-openai"

                # Build env vars for embedded Weaviate
                env_vars = {
                    "ENABLE_MODULES": modules,
                    "BACKUP_FILESYSTEM_PATH": str(Path.home() / ".cache" / "weaviate-backups"),
                    "DEFAULT_VECTORIZER_MODULE": default_vectorizer,
                }

                # Pass API keys as environment variables for embedded mode
                if self.config.embedding_provider == 'openai' and self.config.openai_api_key:
                    env_vars["OPENAI_APIKEY"] = self.config.openai_api_key

                self._client = weaviate.WeaviateClient(
                    embedded_options=EmbeddedOptions(
                        additional_env_vars=env_vars,
                        persistence_data_path=str(Path.home() / ".local" / "share" / "weaviate-elysia"),
                    ),
                    additional_headers=headers if headers else None
                )
                self._client.connect()
                print("Connected to embedded Weaviate (manual embeddings mode)")

            elif self.config.is_local:
                # Connect to local Docker/standalone Weaviate
                self._client = weaviate.connect_to_local(
                    host=self.config.weaviate_url.replace('http://', '').replace('https://', '').split(':')[0],
                    port=int(self.config.weaviate_url.split(':')[-1]) if ':' in self.config.weaviate_url else 8080,
                    headers=headers if headers else None
                )
            else:
                # Connect to Weaviate Cloud
                from weaviate.auth import AuthApiKey
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.config.weaviate_url,
                    auth_credentials=AuthApiKey(self.config.weaviate_api_key),
                    headers=headers if headers else None
                )

            return True
        except ImportError:
            print("Error: weaviate-client not installed. Run: pip install weaviate-client")
            return False
        except Exception as e:
            print(f"Error connecting to Weaviate: {e}")
            import traceback
            traceback.print_exc()
            return False

    def ensure_collection(self, name: str, description: str = ""):
        """Ensure a collection exists"""
        if not self._client:
            return False

        try:
            collections = self._client.collections
            if not collections.exists(name):
                from weaviate.classes.config import Configure, Property, DataType

                # Select vectorizer based on provider
                if self.config.embedding_provider == 'gemini':
                    # For Gemini AI Studio, use no vectorizer - we'll provide embeddings manually
                    vectorizer_config = Configure.Vectorizer.none()
                elif self.config.embedding_provider == 'openai':
                    vectorizer_config = Configure.Vectorizer.text2vec_openai()
                else:
                    # No vectorizer - will need manual embeddings
                    vectorizer_config = Configure.Vectorizer.none()

                collections.create(
                    name=name,
                    description=description,
                    vectorizer_config=vectorizer_config,
                    properties=[
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="source", data_type=DataType.TEXT),
                        Property(name="doc_type", data_type=DataType.TEXT),
                        Property(name="timestamp", data_type=DataType.TEXT),
                        Property(name="metadata", data_type=DataType.TEXT),
                    ]
                )
            return True
        except Exception as e:
            print(f"Error creating collection {name}: {e}")
            return False

    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> int:
        """Add documents to a collection (with manual Gemini embeddings if configured)"""
        if not self._client:
            return 0

        try:
            collection = self._client.collections.get(collection_name)

            # For Gemini provider, generate embeddings manually
            if self.config.embedding_provider == 'gemini' and self.config.gemini_api_key:
                # Process in batches to avoid rate limits
                batch_size = 20
                total_added = 0

                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i + batch_size]

                    # Extract text for embeddings
                    texts = [doc.get('content', '')[:8000] for doc in batch_docs]

                    # Generate embeddings via Gemini API
                    embeddings = get_gemini_embeddings(
                        texts,
                        self.config.gemini_api_key,
                        self.config.gemini_embedding_model
                    )

                    # Add documents with their embeddings
                    with collection.batch.dynamic() as batch:
                        for doc, embedding in zip(batch_docs, embeddings):
                            if embedding:  # Only add if embedding succeeded
                                batch.add_object(
                                    properties={
                                        'content': doc.get('content', ''),
                                        'source': doc.get('source', ''),
                                        'doc_type': doc.get('type', ''),
                                        'timestamp': doc.get('timestamp', ''),
                                        'metadata': json.dumps(doc.get('metadata', {})),
                                    },
                                    vector=embedding
                                )
                                total_added += 1

                    # Small delay to avoid rate limits
                    import time
                    time.sleep(0.5)

                return total_added
            else:
                # Use automatic vectorization (OpenAI or none)
                with collection.batch.dynamic() as batch:
                    for doc in documents:
                        batch.add_object(properties={
                            'content': doc.get('content', ''),
                            'source': doc.get('source', ''),
                            'doc_type': doc.get('type', ''),
                            'timestamp': doc.get('timestamp', ''),
                            'metadata': json.dumps(doc.get('metadata', {})),
                        })

                return len(documents)
        except Exception as e:
            print(f"Error adding documents: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def query(self, collection_name: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Query a collection using vector similarity"""
        if not self._client:
            return []

        try:
            collection = self._client.collections.get(collection_name)

            # For Gemini provider, use near_vector with manual embedding
            if self.config.embedding_provider == 'gemini' and self.config.gemini_api_key:
                # Generate query embedding
                embeddings = get_gemini_embeddings(
                    [query],
                    self.config.gemini_api_key,
                    self.config.gemini_embedding_model
                )

                if not embeddings or not embeddings[0]:
                    print("Failed to generate query embedding")
                    return []

                response = collection.query.near_vector(
                    near_vector=embeddings[0],
                    limit=limit
                )
            else:
                # Use automatic text vectorization
                response = collection.query.near_text(
                    query=query,
                    limit=limit
                )

            results = []
            for obj in response.objects:
                results.append({
                    'content': obj.properties.get('content', ''),
                    'source': obj.properties.get('source', ''),
                    'type': obj.properties.get('doc_type', ''),
                    'timestamp': obj.properties.get('timestamp', ''),
                    'metadata': json.loads(obj.properties.get('metadata', '{}')),
                })

            return results
        except Exception as e:
            print(f"Error querying: {e}")
            return []

    def close(self):
        """Close connection"""
        if self._client:
            self._client.close()


# =============================================================================
# Embedded Atom for Intelligent Context Extraction
# =============================================================================

CONTEXT_EXTRACTION_PROMPT = """# Elysia Context Extractor

You are an intelligent context extraction agent. Your job is to analyze the current conversation
and determine what relevant information from the knowledge base would be helpful.

## Your Task

Given a conversation or query, you will:
1. Identify key topics, entities, and concepts
2. Generate search queries to find relevant context
3. Evaluate retrieved documents for relevance
4. Synthesize the most useful context to inject

## Available Tools

You have access to:
- Bash: Run commands, query databases
- Read: Read files
- Write: Write output files

## Process

1. Analyze the input conversation/query
2. Extract key entities and concepts
3. Generate 2-3 search queries
4. For each query result, score relevance (0-10)
5. Compile the most relevant context

## Output Format

When done, output:

```
CONTEXT_FOUND:
[Synthesized relevant context here - 2-3 paragraphs max]

SOURCES:
- source1
- source2

EXIT_LOOP_NOW
```

If no relevant context found:

```
NO_RELEVANT_CONTEXT

EXIT_LOOP_NOW
```

## Current Query

{query}

Begin analyzing and extracting relevant context.
"""


def get_relevant_context(
    query: str,
    config: Optional[ElysiaSyncConfig] = None,
    max_iterations: int = 5,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Use embedded atom to intelligently extract relevant context from Elysia.

    This is designed to be called at the start of atom conversations to inject
    relevant background knowledge from the user's personal knowledge base.

    Args:
        query: The conversation or query to find context for
        config: Elysia configuration
        max_iterations: Max iterations for context extraction
        verbose: Print progress

    Returns:
        {
            "found": bool,
            "context": str,
            "sources": List[str],
            "raw_results": List[Dict]
        }
    """
    config = config or ElysiaSyncConfig()

    # First, do a direct query to Weaviate
    client = WeaviateClient(config)
    raw_results = []

    if client.connect():
        # Query all collections
        for collection in [config.conversations_collection, config.code_collection,
                          config.emails_collection, config.documents_collection]:
            try:
                results = client.query(collection, query, limit=5)
                raw_results.extend(results)
            except:
                pass
        client.close()

    if not raw_results:
        return {
            "found": False,
            "context": "",
            "sources": [],
            "raw_results": []
        }

    # Use atom to intelligently synthesize
    system_prompt = CONTEXT_EXTRACTION_PROMPT.replace('{query}', query)

    # Add raw results to prompt
    results_text = "\n\n## Retrieved Documents\n\n"
    for i, doc in enumerate(raw_results[:10], 1):
        results_text += f"### Document {i}\n"
        results_text += f"Source: {doc.get('source', 'unknown')}\n"
        results_text += f"Type: {doc.get('type', 'unknown')}\n"
        results_text += f"Content:\n{doc.get('content', '')[:2000]}\n\n"

    system_prompt += results_text

    runtime = AtomRuntime.create_ephemeral(
        system_prompt=system_prompt,
        max_iterations=max_iterations,
        verbose=verbose
    )

    result = runtime.run("Analyze the retrieved documents and extract relevant context.")

    # Parse output
    output = result.get('output', '')

    if 'CONTEXT_FOUND:' in output:
        context_start = output.find('CONTEXT_FOUND:') + len('CONTEXT_FOUND:')
        sources_start = output.find('SOURCES:')

        context = output[context_start:sources_start].strip() if sources_start > 0 else output[context_start:].strip()

        sources = []
        if sources_start > 0:
            sources_text = output[sources_start + len('SOURCES:'):output.find('EXIT_LOOP_NOW')]
            sources = [s.strip().lstrip('- ') for s in sources_text.strip().split('\n') if s.strip()]

        return {
            "found": True,
            "context": context,
            "sources": sources,
            "raw_results": raw_results
        }

    return {
        "found": False,
        "context": "",
        "sources": [],
        "raw_results": raw_results
    }


# =============================================================================
# Main Sync Functions
# =============================================================================

def sync_to_elysia(
    sources: Optional[List[str]] = None,
    config: Optional[ElysiaSyncConfig] = None,
    incremental: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Sync data sources to Elysia/Weaviate.

    Args:
        sources: List of sources to sync: 'conversations', 'code', 'emails', 'documents'
                 Default: all sources
        config: Elysia configuration
        incremental: Only sync changes since last sync
        verbose: Print progress

    Returns:
        {
            "success": bool,
            "synced": {
                "conversations": int,
                "code": int,
                "emails": int,
                "documents": int
            },
            "errors": List[str]
        }
    """
    config = config or ElysiaSyncConfig()
    sources = sources or ['conversations', 'code', 'emails']

    # Load last sync time for incremental
    last_sync = None
    if incremental and config.state_file.exists():
        try:
            with open(config.state_file) as f:
                state = json.load(f)
                last_sync = datetime.fromisoformat(state.get('last_sync', ''))
        except:
            pass

    if verbose:
        print(f"Elysia Sync - Sources: {sources}")
        if last_sync:
            print(f"Incremental sync since: {last_sync}")

    # Connect to Weaviate
    client = WeaviateClient(config)
    if not client.connect():
        return {"success": False, "synced": {}, "errors": ["Failed to connect to Weaviate"]}

    results = {"success": True, "synced": {}, "errors": []}

    try:
        # Sync conversations
        if 'conversations' in sources:
            if verbose:
                print("Collecting conversations...")
            collector = ConversationCollector(config)
            docs = collector.collect(since=last_sync)
            if verbose:
                print(f"  Found {len(docs)} conversations")

            if docs:
                client.ensure_collection(config.conversations_collection, "Claude Code conversations")
                count = client.add_documents(config.conversations_collection, docs)
                results['synced']['conversations'] = count

        # Sync code
        if 'code' in sources:
            if verbose:
                print("Collecting code files...")
            collector = CodeCollector(config)
            docs = collector.collect(since=last_sync)
            if verbose:
                print(f"  Found {len(docs)} code files")

            if docs:
                client.ensure_collection(config.code_collection, "Code files")
                count = client.add_documents(config.code_collection, docs)
                results['synced']['code'] = count

        # Sync emails
        if 'emails' in sources:
            if verbose:
                print("Collecting emails...")
            collector = EmailCollector(config)
            docs = collector.collect(since=last_sync)
            if verbose:
                print(f"  Found {len(docs)} emails")

            if docs:
                client.ensure_collection(config.emails_collection, "Email messages")
                count = client.add_documents(config.emails_collection, docs)
                results['synced']['emails'] = count

        # Save sync state
        config.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config.state_file, 'w') as f:
            json.dump({'last_sync': datetime.now().isoformat()}, f)

    except Exception as e:
        results['success'] = False
        results['errors'].append(str(e))
    finally:
        client.close()

    if verbose:
        print(f"\nSync complete: {results['synced']}")

    return results


def query_elysia(
    query: str,
    collections: Optional[List[str]] = None,
    config: Optional[ElysiaSyncConfig] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Query Elysia/Weaviate for relevant documents.

    Args:
        query: Search query
        collections: Collections to search (default: all)
        config: Elysia configuration
        limit: Max results per collection

    Returns:
        List of matching documents
    """
    config = config or ElysiaSyncConfig()
    collections = collections or [
        config.conversations_collection,
        config.code_collection,
        config.emails_collection,
        config.documents_collection
    ]

    client = WeaviateClient(config)
    if not client.connect():
        return []

    results = []
    try:
        for collection in collections:
            try:
                docs = client.query(collection, query, limit=limit)
                results.extend(docs)
            except:
                pass
    finally:
        client.close()

    return results


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Elysia Sync - Personal knowledge base synchronization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  elysia-sync sync                    # Sync all sources
  elysia-sync sync --sources conversations code
  elysia-sync query "authentication"  # Search knowledge base
  elysia-sync context "How do I..."   # Get relevant context
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync data to Elysia')
    sync_parser.add_argument('--sources', nargs='+', choices=['conversations', 'code', 'emails', 'documents'],
                            help='Sources to sync')
    sync_parser.add_argument('--full', action='store_true', help='Full sync (not incremental)')
    sync_parser.add_argument('--quiet', action='store_true', help='Quiet mode')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query knowledge base')
    query_parser.add_argument('query', help='Search query')
    query_parser.add_argument('--limit', type=int, default=10, help='Max results')

    # Context command
    context_parser = subparsers.add_parser('context', help='Get relevant context for a query')
    context_parser.add_argument('query', help='Query to find context for')
    context_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.command == 'sync':
        result = sync_to_elysia(
            sources=args.sources,
            incremental=not args.full,
            verbose=not args.quiet
        )
        return 0 if result['success'] else 1

    elif args.command == 'query':
        results = query_elysia(args.query, limit=args.limit)
        for i, doc in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Source: {doc.get('source', 'unknown')}")
            print(f"Type: {doc.get('type', 'unknown')}")
            print(f"Content: {doc.get('content', '')[:500]}...")
        return 0

    elif args.command == 'context':
        result = get_relevant_context(args.query, verbose=args.verbose)
        if result['found']:
            print("\n=== Relevant Context ===\n")
            print(result['context'])
            print("\nSources:")
            for src in result['sources']:
                print(f"  - {src}")
        else:
            print("No relevant context found.")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
