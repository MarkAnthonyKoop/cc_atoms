#!/usr/bin/env python3
"""
Home Directory Indexer for Multi-DB Agent

Indexes files from the user's home directory into a Chroma vector store
using Gemini embeddings. Designed to work with multi_db_agent for querying.

Usage:
    from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexer

    indexer = HomeIndexer()
    indexer.index_all()

    # Then query via multi_db_agent
    from cc_atoms.tools.multi_db_agent import create_agent
    agent = create_agent()
    agent.register_vector({"home": indexer.get_vector_config()})
    result = agent.query("What Python projects do I have?")
"""
import os
import sys
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# Try to import chromadb
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


@dataclass
class HomeIndexerConfig:
    """Configuration for home directory indexing"""

    # Directories to index - FULL HOME DIRECTORY
    index_paths: List[Path] = field(default_factory=lambda: [
        Path.home(),  # Index everything in ~
    ])

    # Claude conversations
    claude_projects_dir: Path = field(default_factory=lambda: Path.home() / '.claude' / 'projects')

    # File extensions for code
    code_extensions: List[str] = field(default_factory=lambda: [
        '.py', '.js', '.ts', '.tsx', '.jsx', '.md', '.txt', '.json', '.yaml', '.yml',
        '.sh', '.bash', '.zsh', '.html', '.css', '.sql', '.go', '.rs', '.swift',
        '.rb', '.php', '.java', '.c', '.cpp', '.h', '.hpp', '.toml', '.ini', '.cfg',
    ])

    # File extensions for documents
    document_extensions: List[str] = field(default_factory=lambda: [
        '.md', '.txt', '.pdf', '.doc', '.docx', '.rtf',
        '.csv', '.json', '.xml', '.html', '.htm',
    ])

    # Skip patterns - skip system/cache dirs but keep user content
    skip_dirs: List[str] = field(default_factory=lambda: [
        # Build/package dirs
        'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build',
        '.git', '.svn', '.hg', 'target', 'vendor', '.tox', 'eggs',
        '*.egg-info', '.mypy_cache', '.pytest_cache',
        # macOS system dirs to skip
        'Library', '.Trash', '.cache', '.venvs', '.local',
        'Applications',  # Usually just app bundles
        # Large media dirs (can enable if needed)
        # 'Movies', 'Music', 'Pictures',
    ])

    # Limits
    max_file_size_mb: int = 10
    max_content_length: int = 50000  # Characters per document
    embedding_batch_size: int = 20

    # Chroma settings
    persist_dir: str = field(default_factory=lambda: str(Path.home() / '.cache' / 'multi_db_agent' / 'home_index'))
    collection_name: str = 'home_directory'

    # Gemini API
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY'))
    gemini_model: str = 'text-embedding-004'

    # State file for incremental indexing
    state_file: Path = field(default_factory=lambda: Path.home() / '.cache' / 'multi_db_agent' / 'index_state.json')


def get_gemini_embeddings(texts: List[str], api_key: str, model: str = "text-embedding-004") -> List[List[float]]:
    """Generate embeddings using Gemini API."""
    import urllib.request
    import urllib.error

    embeddings = []
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"

    for text in texts:
        # Truncate text if too long
        text = text[:8000] if len(text) > 8000 else text

        if not text.strip():
            embeddings.append([0.0] * 768)  # Zero vector for empty text
            continue

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
                embeddings.append(result.get("embedding", {}).get("values", [0.0] * 768))
        except urllib.error.HTTPError as e:
            print(f"Embedding error: {e.code} - {e.reason}")
            embeddings.append([0.0] * 768)
        except Exception as e:
            print(f"Embedding error: {e}")
            embeddings.append([0.0] * 768)

    return embeddings


class HomeIndexer:
    """
    Indexes home directory contents into Chroma vector store.

    Collects:
    - Code files from ~/claude, ~/Projects
    - Documents from ~/Documents, ~/Desktop, ~/Downloads
    - Claude conversations from ~/.claude/projects/
    """

    def __init__(self, config: Optional[HomeIndexerConfig] = None, verbose: bool = True):
        self.config = config or HomeIndexerConfig()
        self.verbose = verbose
        self._client = None
        self._collection = None
        self._stats = {
            'code_files': 0,
            'documents': 0,
            'conversations': 0,
            'total_indexed': 0,
            'errors': 0,
        }

        # Indexing logging
        self._index_log_file = Path.home() / '.cache' / 'multi_db_agent' / 'logs' / 'indexing.jsonl'
        self._index_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._files_indexed = []
        self._files_skipped = []
        self._errors_log = []

    def _log(self, msg: str):
        if self.verbose:
            print(f"[HomeIndexer] {msg}")

    def _log_file(self, action: str, file_path: Path, reason: str = None, error: str = None):
        """Log individual file processing"""
        if action == 'indexed':
            self._files_indexed.append(str(file_path))
        elif action == 'skipped':
            self._files_skipped.append({'file': str(file_path), 'reason': reason})
        elif action == 'error':
            self._errors_log.append({'file': str(file_path), 'error': str(error)})

    def _write_index_log(self, mode: str, duration: float):
        """Write comprehensive indexing log"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'mode': mode,  # 'fresh' or 'incremental'
            'duration_seconds': duration,
            'stats': self._stats.copy(),
            'files_indexed': len(self._files_indexed),
            'files_skipped': len(self._files_skipped),
            'errors': len(self._errors_log),
            'sample_indexed': self._files_indexed[:20],  # First 20 files
            'sample_skipped': self._files_skipped[:20],
            'all_errors': self._errors_log,  # Log all errors
        }

        try:
            with open(self._index_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self._log(f"Failed to write index log: {e}")

    def _init_chroma(self, fresh: bool = False):
        """Initialize Chroma client and collection."""
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb not installed. Run: pip install chromadb")

        os.makedirs(self.config.persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.config.persist_dir)

        # Delete existing collection only if fresh mode
        if fresh:
            try:
                self._client.delete_collection(name=self.config.collection_name)
                self._log("Deleted existing collection for fresh index")
            except:
                pass

        self._collection = self._client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self._log(f"Chroma collection '{self.config.collection_name}' ready at {self.config.persist_dir}")

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        for skip in self.config.skip_dirs:
            if skip.startswith('*'):
                # Glob pattern
                if any(p.endswith(skip[1:]) for p in path.parts):
                    return True
            else:
                if skip in path.parts:
                    return True

        # Skip hidden files/directories
        if any(p.startswith('.') and p not in ['.claude'] for p in path.parts):
            return True

        return False

    def _collect_code_files(self) -> List[Dict[str, Any]]:
        """Collect code files from configured paths."""
        documents = []
        max_size = self.config.max_file_size_mb * 1024 * 1024

        for base_path in self.config.index_paths:
            if not base_path.exists():
                continue

            self._log(f"Scanning code in {base_path}...")

            for ext in self.config.code_extensions:
                for file_path in base_path.rglob(f'*{ext}'):
                    if self._should_skip(file_path):
                        continue

                    try:
                        stat = file_path.stat()
                        if stat.st_size > max_size:
                            continue

                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if not content.strip():
                            continue

                        # Get relative path for display
                        try:
                            rel_path = file_path.relative_to(Path.home())
                        except ValueError:
                            rel_path = file_path

                        documents.append({
                            'id': hashlib.md5(str(file_path).encode()).hexdigest(),
                            'type': 'code',
                            'source': str(file_path),
                            'filename': file_path.name,
                            'extension': file_path.suffix,
                            'relative_path': str(rel_path),
                            'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'content': content[:self.config.max_content_length],
                            'file_size': stat.st_size,
                            'line_count': content.count('\n') + 1,
                        })
                        self._stats['code_files'] += 1

                    except Exception as e:
                        self._stats['errors'] += 1

        return documents

    def _collect_documents(self) -> List[Dict[str, Any]]:
        """Collect document files from Documents, Desktop, Downloads."""
        documents = []
        max_size = self.config.max_file_size_mb * 1024 * 1024

        doc_paths = [
            Path.home() / 'Documents',
            Path.home() / 'Desktop',
            Path.home() / 'Downloads',
        ]

        for base_path in doc_paths:
            if not base_path.exists():
                continue

            self._log(f"Scanning documents in {base_path}...")

            for ext in self.config.document_extensions:
                for file_path in base_path.rglob(f'*{ext}'):
                    if self._should_skip(file_path):
                        continue

                    try:
                        stat = file_path.stat()
                        if stat.st_size > max_size:
                            continue

                        # Read content
                        content = self._read_document(file_path)
                        if not content or not content.strip():
                            continue

                        try:
                            rel_path = file_path.relative_to(Path.home())
                        except ValueError:
                            rel_path = file_path

                        documents.append({
                            'id': hashlib.md5(str(file_path).encode()).hexdigest(),
                            'type': 'document',
                            'source': str(file_path),
                            'filename': file_path.name,
                            'extension': file_path.suffix,
                            'relative_path': str(rel_path),
                            'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'content': content[:self.config.max_content_length],
                            'file_size': stat.st_size,
                        })
                        self._stats['documents'] += 1

                    except Exception as e:
                        self._stats['errors'] += 1

        return documents

    def _read_document(self, file_path: Path) -> Optional[str]:
        """Read document content, handling different file types."""
        ext = file_path.suffix.lower()

        # Text-based files
        if ext in ['.md', '.txt', '.csv', '.json', '.xml', '.html', '.htm', '.rtf']:
            try:
                return file_path.read_text(encoding='utf-8', errors='ignore')
            except:
                return None

        # PDF files
        if ext == '.pdf':
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
            return f"[PDF Document: {file_path.name}]"

        return None

    def _collect_conversations(self) -> List[Dict[str, Any]]:
        """Collect Claude conversations from ~/.claude/projects/"""
        documents = []
        projects_dir = self.config.claude_projects_dir

        if not projects_dir.exists():
            return documents

        self._log(f"Scanning conversations in {projects_dir}...")

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            for conv_file in project_dir.glob('**/*.jsonl'):
                try:
                    messages = []
                    with open(conv_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    messages.append(json.loads(line))
                                except json.JSONDecodeError:
                                    continue

                    if not messages:
                        continue

                    # Extract project path from directory name
                    project_path = project_dir.name.replace('-', '/')
                    if project_path.startswith('/'):
                        project_path = project_path[1:]

                    # Build searchable content from messages
                    content_parts = []
                    for msg in messages[-100:]:  # Last 100 messages
                        # Claude conversations use 'type' not 'role'
                        role = msg.get('type', msg.get('role', 'unknown'))

                        # Content can be in msg directly or nested in msg['message']
                        msg_content = msg.get('message', {}).get('content', msg.get('content', ''))

                        # Content can be a list of {type: 'text', text: '...'} objects
                        if isinstance(msg_content, list):
                            text_parts = []
                            for part in msg_content:
                                if isinstance(part, dict) and part.get('text'):
                                    text_parts.append(part['text'])
                            msg_content = ' '.join(text_parts)

                        if isinstance(msg_content, str) and msg_content.strip():
                            content_parts.append(f"[{role}]: {msg_content[:2000]}")

                    content = '\n'.join(content_parts)
                    if not content.strip():
                        continue

                    stat = conv_file.stat()

                    documents.append({
                        'id': hashlib.md5(str(conv_file).encode()).hexdigest(),
                        'type': 'conversation',
                        'source': str(conv_file),
                        'filename': conv_file.name,
                        'project_path': project_path,
                        'relative_path': f".claude/projects/{project_dir.name}/{conv_file.name}",
                        'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'content': content[:self.config.max_content_length],
                        'message_count': len(messages),
                    })
                    self._stats['conversations'] += 1

                except Exception as e:
                    self._stats['errors'] += 1

        return documents

    def _add_to_chroma(self, documents: List[Dict[str, Any]]):
        """Add documents to Chroma with Gemini embeddings."""
        if not documents:
            return

        if not self.config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        batch_size = self.config.embedding_batch_size
        total_batches = (len(documents) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(documents))
            batch = documents[start_idx:end_idx]

            self._log(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} docs)...")

            # Prepare texts for embedding
            texts = [doc['content'] for doc in batch]

            # Generate embeddings
            embeddings = get_gemini_embeddings(
                texts,
                self.config.gemini_api_key,
                self.config.gemini_model
            )

            # Prepare data for Chroma
            ids = [doc['id'] for doc in batch]
            documents_text = texts
            metadatas = []

            for doc in batch:
                meta = {
                    'type': doc.get('type', 'unknown'),
                    'source': doc.get('source', ''),
                    'filename': doc.get('filename', ''),
                    'relative_path': doc.get('relative_path', ''),
                    'timestamp': doc.get('timestamp', ''),
                }
                # Add optional fields
                if 'extension' in doc:
                    meta['extension'] = doc['extension']
                if 'project_path' in doc:
                    meta['project_path'] = doc['project_path']
                if 'line_count' in doc:
                    meta['line_count'] = doc['line_count']
                if 'message_count' in doc:
                    meta['message_count'] = doc['message_count']
                if 'file_size' in doc:
                    meta['file_size'] = doc['file_size']
                metadatas.append(meta)

            # Filter out documents with failed embeddings (all zeros)
            valid_indices = [i for i, emb in enumerate(embeddings) if any(v != 0 for v in emb)]

            if valid_indices:
                self._collection.add(
                    ids=[ids[i] for i in valid_indices],
                    documents=[documents_text[i] for i in valid_indices],
                    metadatas=[metadatas[i] for i in valid_indices],
                    embeddings=[embeddings[i] for i in valid_indices]
                )
                self._stats['total_indexed'] += len(valid_indices)

                # Log each indexed file
                for i in valid_indices:
                    doc = batch[i]
                    self._log_file('indexed', Path(doc.get('source', 'unknown')))

            # Rate limit delay
            if batch_num < total_batches - 1:
                time.sleep(0.5)

    def _load_state(self) -> Dict[str, Any]:
        """Load previous indexing state."""
        if self.config.state_file.exists():
            try:
                with open(self.config.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _get_indexed_ids(self) -> set:
        """Get IDs of already indexed documents."""
        if not self._collection:
            return set()
        try:
            # Get all IDs from collection
            result = self._collection.get(include=[])
            return set(result.get('ids', []))
        except:
            return set()

    def index_all(self, fresh: bool = False, incremental: bool = True) -> Dict[str, Any]:
        """
        Index all content from home directory.

        Args:
            fresh: If True, delete existing index and start fresh
            incremental: If True (default), only index new/changed files

        Returns:
            Statistics about indexed content
        """
        mode = "fresh" if fresh else ("incremental" if incremental else "full")
        self._log(f"Starting home directory indexing (mode: {mode})...")
        start_time = time.time()

        # Reset stats
        self._stats = {
            'code_files': 0,
            'documents': 0,
            'conversations': 0,
            'total_indexed': 0,
            'skipped': 0,
            'errors': 0,
        }

        # Initialize Chroma
        self._init_chroma(fresh=fresh)

        # For incremental, get already indexed IDs
        existing_ids = set() if fresh else self._get_indexed_ids()
        if existing_ids:
            self._log(f"Found {len(existing_ids)} already indexed documents")

        # Collect all documents
        all_docs = []

        self._log("\n=== Collecting Code Files ===")
        code_docs = self._collect_code_files()
        all_docs.extend(code_docs)
        self._log(f"Found {len(code_docs)} code files")

        self._log("\n=== Collecting Documents ===")
        doc_docs = self._collect_documents()
        all_docs.extend(doc_docs)
        self._log(f"Found {len(doc_docs)} documents")

        self._log("\n=== Collecting Conversations ===")
        conv_docs = self._collect_conversations()
        all_docs.extend(conv_docs)
        self._log(f"Found {len(conv_docs)} conversations")

        # Filter out already-indexed docs for incremental mode
        if existing_ids and incremental:
            new_docs = [doc for doc in all_docs if doc['id'] not in existing_ids]
            self._stats['skipped'] = len(all_docs) - len(new_docs)
            self._log(f"\nIncremental: {len(new_docs)} new, {self._stats['skipped']} already indexed")
            all_docs = new_docs

        self._log(f"\n=== Indexing {len(all_docs)} Documents ===")

        # Add to Chroma with embeddings
        self._add_to_chroma(all_docs)

        elapsed = time.time() - start_time
        self._stats['elapsed_seconds'] = round(elapsed, 2)

        self._log(f"\n=== Indexing Complete ===")
        self._log(f"Code files: {self._stats['code_files']}")
        self._log(f"Documents: {self._stats['documents']}")
        self._log(f"Conversations: {self._stats['conversations']}")
        self._log(f"Total indexed: {self._stats['total_indexed']}")
        self._log(f"Errors: {self._stats['errors']}")
        self._log(f"Time: {elapsed:.1f}s")

        # Write comprehensive log
        self._write_index_log(mode, elapsed)

        # Save state
        self._save_state()

        return self._stats

    def _save_state(self):
        """Save indexing state for future reference."""
        state = {
            'last_index': datetime.now().isoformat(),
            'stats': self._stats,
            'config': {
                'persist_dir': self.config.persist_dir,
                'collection_name': self.config.collection_name,
            }
        }

        self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def get_vector_config(self) -> Dict[str, Any]:
        """Get configuration for registering with MultiDBAgent."""
        return {
            'store_type': 'chroma',
            'persist_dir': self.config.persist_dir,
            'collection_name': self.config.collection_name,
        }

    def query(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Query the indexed content.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of matching documents with metadata
        """
        if not self._collection:
            # Reconnect to existing collection
            if not CHROMADB_AVAILABLE:
                raise ImportError("chromadb not installed")

            self._client = chromadb.PersistentClient(path=self.config.persist_dir)
            try:
                self._collection = self._client.get_collection(name=self.config.collection_name)
            except:
                raise ValueError(f"Collection '{self.config.collection_name}' not found. Run index_all() first.")

        # Generate query embedding
        if not self.config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        query_embedding = get_gemini_embeddings(
            [query],
            self.config.gemini_api_key,
            self.config.gemini_model
        )[0]

        # Query Chroma
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )

        # Format results
        documents = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else None

                documents.append({
                    'content': doc,
                    'metadata': metadata,
                    'score': 1 - (distance or 0),  # Convert distance to similarity
                    'source': metadata.get('source', ''),
                    'type': metadata.get('type', ''),
                    'filename': metadata.get('filename', ''),
                    'relative_path': metadata.get('relative_path', ''),
                })

        return documents

    def get_stats(self) -> Dict[str, Any]:
        """Get current collection statistics."""
        if not self._collection:
            if not CHROMADB_AVAILABLE:
                return {'error': 'chromadb not installed'}

            try:
                self._client = chromadb.PersistentClient(path=self.config.persist_dir)
                self._collection = self._client.get_collection(name=self.config.collection_name)
            except:
                return {'error': 'Collection not found'}

        return {
            'collection_name': self.config.collection_name,
            'document_count': self._collection.count(),
            'persist_dir': self.config.persist_dir,
        }


def main():
    """CLI entry point for home indexer."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Home Directory Indexer - Index your files for AI search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  home-indexer index          # Index home directory
  home-indexer query "Python projects"
  home-indexer stats          # Show collection stats
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Index command
    index_parser = subparsers.add_parser('index', help='Index home directory')
    index_parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    index_parser.add_argument('--fresh', '-f', action='store_true', help='Fresh index (delete existing)')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query indexed content')
    query_parser.add_argument('query', help='Search query')
    query_parser.add_argument('--top-k', '-k', type=int, default=10, help='Number of results')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show collection statistics')

    args = parser.parse_args()

    if args.command == 'index':
        indexer = HomeIndexer(verbose=not args.quiet)
        stats = indexer.index_all(fresh=args.fresh)
        skipped = stats.get('skipped', 0)
        if skipped > 0:
            print(f"\nIndexed {stats['total_indexed']} new documents, skipped {skipped} (already indexed) in {stats.get('elapsed_seconds', 0)}s")
        else:
            print(f"\nIndexed {stats['total_indexed']} documents in {stats.get('elapsed_seconds', 0)}s")
        return 0

    elif args.command == 'query':
        indexer = HomeIndexer(verbose=False)
        results = indexer.query(args.query, top_k=args.top_k)

        print(f"\nFound {len(results)} results:\n")
        for i, doc in enumerate(results, 1):
            print(f"--- Result {i} (score: {doc['score']:.3f}) ---")
            print(f"Type: {doc['type']}")
            print(f"File: {doc['relative_path']}")
            print(f"Preview: {doc['content'][:300]}...")
            print()
        return 0

    elif args.command == 'stats':
        indexer = HomeIndexer(verbose=False)
        stats = indexer.get_stats()
        print(f"Collection: {stats.get('collection_name', 'N/A')}")
        print(f"Documents: {stats.get('document_count', 'N/A')}")
        print(f"Location: {stats.get('persist_dir', 'N/A')}")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
