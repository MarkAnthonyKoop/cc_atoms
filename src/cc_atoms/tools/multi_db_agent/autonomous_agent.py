#!/usr/bin/env python3
"""
Autonomous Data Agent - Self-managing agent for home directory automation

This agent can:
1. Periodically re-index changed files
2. Answer questions about your entire home directory
3. Perform automated actions (file search, analysis, organization, reports)
4. Run continuous monitoring and automation tasks

Architecture:
- Uses HomeIndexer for semantic search over ~/
- Uses AtomRuntime for complex multi-step tasks
- Uses Gemini for fast queries
- Tracks file changes via mtime comparison

Usage:
    from cc_atoms.tools.multi_db_agent.autonomous_agent import AutonomousDataAgent

    agent = AutonomousDataAgent()

    # Answer questions
    response = agent.ask("What Python projects do I have?")

    # Perform actions
    result = agent.act("Find all TODO comments in my code and create a summary report")

    # Start autonomous mode
    agent.run_autonomous(
        tasks=["Monitor ~/Downloads for new files and organize them"],
        interval_minutes=30
    )

CLI:
    data-agent ask "What have I been working on?"
    data-agent act "Find duplicate files in ~/Documents"
    data-agent sync                    # Re-index changed files
    data-agent daemon --interval 30    # Run autonomous monitoring
"""
import os
import sys
import json
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum


class ActionType(Enum):
    """Types of actions the agent can perform"""
    SEARCH = "search"           # Search files/content
    ANALYZE = "analyze"         # Analyze code/documents
    ORGANIZE = "organize"       # Organize/move files
    REPORT = "report"           # Generate reports
    SUMMARIZE = "summarize"     # Summarize content
    FIND_DUPLICATES = "find_duplicates"
    CLEAN = "clean"             # Clean up (with confirmation)
    MONITOR = "monitor"         # Watch for changes
    CUSTOM = "custom"           # Custom atom task


@dataclass
class ActionResult:
    """Result of an agent action"""
    success: bool
    action_type: ActionType
    output: str
    files_affected: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeDetectionState:
    """State for tracking file changes"""
    file_mtimes: Dict[str, float] = field(default_factory=dict)
    last_scan: Optional[datetime] = None
    files_added: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)


AUTONOMOUS_SYSTEM_PROMPT = """# Autonomous Data Agent

You are an autonomous agent with full access to the user's home directory.
You can search, analyze, organize, and report on files and data.

## CRITICAL: Read USER_PROMPT.md First!

Your task is specified in USER_PROMPT.md in the current directory.
READ IT IMMEDIATELY and execute the task described there.

## Your Capabilities

1. **Search**: Find files by content, name, type, or semantic meaning
2. **Analyze**: Examine code quality, document structure, patterns
3. **Organize**: Suggest or perform file organization (with user confirmation for moves/deletes)
4. **Report**: Generate summaries, statistics, and reports
5. **Monitor**: Watch for changes and take automated actions

## Guidelines

1. IMMEDIATELY read USER_PROMPT.md and start working on the task
2. Be proactive but safe - suggest destructive actions, don't perform them without confirmation
3. Reference specific file paths in your responses
4. For complex multi-step tasks, break them down and explain your approach
5. Provide actionable insights, not just data

## Output Format

When completing a task, structure your output as:
1. **Summary**: Brief overview of what was done
2. **Details**: Specific findings, files, or actions
3. **Recommendations**: Next steps or suggestions (if applicable)

When done with a task, output: EXIT_LOOP_NOW
"""


class AutonomousDataAgent:
    """
    Self-managing agent for home directory automation.

    Combines:
    - HomeIndexer for semantic search
    - AtomRuntime for complex multi-step tasks
    - Gemini for fast conversational queries
    - File change detection for incremental updates
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "home_directory",
        verbose: bool = True,
        gemini_api_key: Optional[str] = None,
    ):
        """
        Initialize the autonomous agent.

        Args:
            persist_dir: Path to Chroma index
            collection_name: Collection name
            verbose: Print progress info
            gemini_api_key: Gemini API key (or from GEMINI_API_KEY env)
        """
        self.persist_dir = persist_dir or str(Path.home() / '.cache' / 'multi_db_agent' / 'home_index')
        self.collection_name = collection_name
        self.verbose = verbose
        self._gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

        # Change detection state
        self._change_state = ChangeDetectionState()
        self._state_file = Path.home() / '.cache' / 'multi_db_agent' / 'agent_state.json'

        # Daemon state
        self._daemon_running = False
        self._daemon_thread: Optional[threading.Thread] = None

        # Query logging
        self._query_log_file = Path.home() / '.cache' / 'multi_db_agent' / 'logs' / 'queries.jsonl'
        self._query_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Load saved state
        self._load_state()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[DataAgent] {msg}")

    def _log_query(self, query_type: str, query: str, search_results: List[Dict] = None,
                   output: str = None, duration: float = None, iterations: int = None):
        """Log query details to queries.jsonl for transparency"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': query_type,  # 'ask', 'search', 'act'
            'query': query,
            'duration_seconds': duration,
        }

        if search_results:
            log_entry['search_results'] = [
                {
                    'file': r.get('source', r.get('relative_path', 'unknown')),
                    'score': r.get('score', 0),
                    'type': r.get('type', 'unknown'),
                    'preview': r.get('content', '')[:200] if r.get('content') else ''
                }
                for r in search_results[:10]  # Log top 10
            ]
            log_entry['num_results'] = len(search_results)

        if iterations:
            log_entry['iterations'] = iterations

        if output:
            log_entry['output_length'] = len(output)
            log_entry['output_preview'] = output[:500]

        try:
            with open(self._query_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self._log(f"Failed to write query log: {e}")

    def _load_state(self):
        """Load agent state from disk."""
        if self._state_file.exists():
            try:
                with open(self._state_file, 'r') as f:
                    data = json.load(f)
                    self._change_state.file_mtimes = data.get('file_mtimes', {})
                    if data.get('last_scan'):
                        self._change_state.last_scan = datetime.fromisoformat(data['last_scan'])
            except Exception as e:
                self._log(f"Could not load state: {e}")

    def _save_state(self):
        """Save agent state to disk."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, 'w') as f:
                json.dump({
                    'file_mtimes': self._change_state.file_mtimes,
                    'last_scan': self._change_state.last_scan.isoformat() if self._change_state.last_scan else None,
                }, f)
        except Exception as e:
            self._log(f"Could not save state: {e}")

    def _get_indexer(self):
        """Get or create HomeIndexer instance."""
        # Import here to avoid chromadb import issues
        from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexer, HomeIndexerConfig

        config = HomeIndexerConfig(
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )
        return HomeIndexer(config=config, verbose=self.verbose)

    def _call_gemini(self, prompt: str, system_prompt: str = "") -> str:
        """Call Gemini for fast responses."""
        import urllib.request

        if not self._gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")

        model = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._gemini_api_key}"

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        payload = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}]}]
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
            return f"Error: {e}"

    # =========================================================================
    # QUERY CAPABILITIES
    # =========================================================================

    def ask(self, question: str, top_k: int = 10) -> str:
        """
        Ask a question about your indexed data.

        Uses semantic search + Gemini for fast responses.
        For complex multi-step tasks, use act() instead.

        Args:
            question: Your question
            top_k: Number of documents to retrieve

        Returns:
            AI-generated response
        """
        self._log(f"Searching: {question}")

        # Search the index
        indexer = self._get_indexer()
        results = indexer.query(question, top_k=top_k)

        if not results:
            return "No relevant documents found. Try running `data-agent sync` to update the index."

        self._log(f"Found {len(results)} relevant documents")

        # Format context
        context_parts = []
        for i, doc in enumerate(results[:5], 1):
            rel_path = doc.get('relative_path', doc.get('source', 'unknown'))
            content = doc.get('content', '')[:1500]
            score = doc.get('score', 0)
            doc_type = doc.get('type', 'unknown')

            context_parts.append(f"""
--- {doc_type} ({score:.2f}): {rel_path} ---
{content}
""")

        context = "\n".join(context_parts)

        # Generate response
        prompt = f"""Question: {question}

Context from knowledge base:
{context}

Answer the question based on the context. Reference specific files when relevant.
If the context doesn't fully answer the question, say what you found and what might be missing."""

        start_time = time.time()
        response = self._call_gemini(prompt, AUTONOMOUS_SYSTEM_PROMPT)
        duration = time.time() - start_time

        # Log the query
        self._log_query('ask', question, search_results=results, output=response, duration=duration)

        return response

    def search(self, query: str, top_k: int = 20, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search indexed content with optional filtering.

        Args:
            query: Search query
            top_k: Number of results
            doc_type: Filter by type ('code', 'document', 'conversation')

        Returns:
            List of matching documents
        """
        start_time = time.time()
        indexer = self._get_indexer()
        results = indexer.query(query, top_k=top_k)

        if doc_type:
            results = [r for r in results if r.get('type') == doc_type]

        duration = time.time() - start_time

        # Log the search
        self._log_query('search', query, search_results=results, duration=duration)

        return results

    # =========================================================================
    # ACTION CAPABILITIES
    # =========================================================================

    def act(self, task: str, max_iterations: int = 10) -> ActionResult:
        """
        Perform a complex action using AtomRuntime.

        Use this for multi-step tasks like:
        - "Find all TODO comments and create a report"
        - "Analyze my Python code for potential issues"
        - "Summarize my recent conversations"

        Args:
            task: Task description
            max_iterations: Max atom iterations

        Returns:
            ActionResult with output and metadata
        """
        start_time = time.time()
        self._log(f"Starting action: {task}")

        # Determine action type
        action_type = self._classify_action(task)

        # Get relevant context
        search_results = self.search(task, top_k=10)
        context = self._format_context_for_action(search_results)

        # Build enhanced task prompt - task FIRST, very clear
        enhanced_task = f"""## YOUR TASK - DO THIS NOW:

{task}

---

## Relevant Context (from indexed knowledge base):

{context}

---

## Instructions:
1. IMMEDIATELY start working on the task above
2. Use the context to inform your work
3. Be specific with file paths and code references
4. For destructive file operations, describe what you would do but ASK for confirmation
5. When complete, provide a clear summary
6. Output EXIT_LOOP_NOW when done

DO NOT ask what to do. The task is clearly stated above. Begin working on it now.
"""

        # Run via AtomRuntime
        # Disable memory injection - we're providing our own curated context
        from cc_atoms.atom_core import AtomRuntime

        runtime = AtomRuntime.create_ephemeral(
            system_prompt=AUTONOMOUS_SYSTEM_PROMPT,
            max_iterations=max_iterations,
            verbose=self.verbose,
            use_memory=False  # We already injected relevant context above
        )

        result = runtime.run(enhanced_task)
        duration = time.time() - start_time

        action_result = ActionResult(
            success=result.get('success', False),
            action_type=action_type,
            output=result.get('output', ''),
            duration_seconds=duration,
            metadata={
                'iterations': result.get('iterations', 0),
                'search_results_used': len(search_results),
            }
        )

        # Log the action
        self._log_query(
            'act',
            task,
            search_results=search_results,
            output=action_result.output,
            duration=duration,
            iterations=result.get('iterations', 0)
        )

        return action_result

    def _classify_action(self, task: str) -> ActionType:
        """Classify the action type from task description."""
        task_lower = task.lower()

        if any(w in task_lower for w in ['find', 'search', 'locate', 'where']):
            return ActionType.SEARCH
        elif any(w in task_lower for w in ['analyze', 'review', 'check', 'audit']):
            return ActionType.ANALYZE
        elif any(w in task_lower for w in ['organize', 'move', 'rename', 'sort']):
            return ActionType.ORGANIZE
        elif any(w in task_lower for w in ['report', 'list', 'inventory']):
            return ActionType.REPORT
        elif any(w in task_lower for w in ['summarize', 'summary', 'overview']):
            return ActionType.SUMMARIZE
        elif any(w in task_lower for w in ['duplicate', 'duplicates', 'copy', 'copies']):
            return ActionType.FIND_DUPLICATES
        elif any(w in task_lower for w in ['clean', 'delete', 'remove']):
            return ActionType.CLEAN
        elif any(w in task_lower for w in ['monitor', 'watch', 'track']):
            return ActionType.MONITOR
        else:
            return ActionType.CUSTOM

    def _format_context_for_action(self, results: List[Dict[str, Any]]) -> str:
        """Format search results as context for actions."""
        if not results:
            return "No relevant indexed content found."

        parts = []
        for doc in results[:10]:
            rel_path = doc.get('relative_path', 'unknown')
            doc_type = doc.get('type', 'unknown')
            content = doc.get('content', '')[:800]

            parts.append(f"[{doc_type}] {rel_path}:\n{content[:500]}...")

        return "\n\n".join(parts)

    # =========================================================================
    # SYNC / REINDEX
    # =========================================================================

    def detect_changes(self, directories: Optional[List[Path]] = None) -> ChangeDetectionState:
        """
        Detect changed files since last scan.

        Args:
            directories: Directories to scan (default: standard index paths)

        Returns:
            ChangeDetectionState with added/modified/deleted lists
        """
        from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexerConfig

        config = HomeIndexerConfig()
        dirs = directories or config.index_paths

        self._log("Scanning for changes...")

        current_mtimes = {}
        extensions = set(config.code_extensions + config.document_extensions)

        for base_dir in dirs:
            if not base_dir.exists():
                continue

            for ext in extensions:
                for file_path in base_dir.rglob(f'*{ext}'):
                    # Skip common excludes
                    if any(skip in str(file_path) for skip in ['node_modules', '__pycache__', '.git', 'venv']):
                        continue

                    try:
                        mtime = file_path.stat().st_mtime
                        current_mtimes[str(file_path)] = mtime
                    except (OSError, PermissionError):
                        pass

        # Also scan conversations
        conv_dir = Path.home() / '.claude' / 'projects'
        if conv_dir.exists():
            for jsonl in conv_dir.rglob('*.jsonl'):
                try:
                    current_mtimes[str(jsonl)] = jsonl.stat().st_mtime
                except (OSError, PermissionError):
                    pass

        # Compare with previous state
        old_files = set(self._change_state.file_mtimes.keys())
        new_files = set(current_mtimes.keys())

        added = list(new_files - old_files)
        deleted = list(old_files - new_files)

        modified = []
        for f in old_files & new_files:
            if current_mtimes[f] > self._change_state.file_mtimes.get(f, 0):
                modified.append(f)

        # Update state
        self._change_state.file_mtimes = current_mtimes
        self._change_state.last_scan = datetime.now()
        self._change_state.files_added = added
        self._change_state.files_modified = modified
        self._change_state.files_deleted = deleted

        self._save_state()

        self._log(f"Changes: {len(added)} added, {len(modified)} modified, {len(deleted)} deleted")

        return self._change_state

    def sync(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync the index with file changes.

        Args:
            force: Force full reindex instead of incremental

        Returns:
            Sync statistics
        """
        self._log("Starting sync...")

        if force:
            self._log("Force mode: performing full reindex")
            indexer = self._get_indexer()
            stats = indexer.index_all(fresh=True)
            return {
                'mode': 'full',
                'indexed': stats.get('total_indexed', 0),
                'duration': stats.get('elapsed_seconds', 0),
            }

        # Detect changes first
        changes = self.detect_changes()

        total_changes = len(changes.files_added) + len(changes.files_modified)

        if total_changes == 0:
            self._log("No changes detected")
            return {
                'mode': 'incremental',
                'indexed': 0,
                'message': 'No changes detected',
            }

        self._log(f"Found {total_changes} files to index")

        # Run incremental index
        indexer = self._get_indexer()
        stats = indexer.index_all(incremental=True)

        return {
            'mode': 'incremental',
            'files_added': len(changes.files_added),
            'files_modified': len(changes.files_modified),
            'files_deleted': len(changes.files_deleted),
            'indexed': stats.get('total_indexed', 0),
            'duration': stats.get('elapsed_seconds', 0),
        }

    # =========================================================================
    # AUTONOMOUS MODE
    # =========================================================================

    def run_autonomous(
        self,
        tasks: Optional[List[str]] = None,
        interval_minutes: int = 30,
        on_change: Optional[Callable[[ChangeDetectionState], None]] = None,
        max_runtime_hours: Optional[float] = None,
    ):
        """
        Run in autonomous daemon mode.

        Periodically:
        1. Syncs the index with file changes
        2. Executes configured tasks
        3. Calls on_change callback when changes detected

        Args:
            tasks: List of tasks to run on each interval
            interval_minutes: Minutes between checks
            on_change: Callback when changes are detected
            max_runtime_hours: Stop after this many hours (None = run forever)
        """
        self._log(f"Starting autonomous mode (interval: {interval_minutes}m)")
        self._daemon_running = True
        start_time = time.time()

        default_tasks = tasks or [
            "Check for new files in ~/Downloads and summarize any new documents",
        ]

        try:
            while self._daemon_running:
                # Check runtime limit
                if max_runtime_hours:
                    elapsed_hours = (time.time() - start_time) / 3600
                    if elapsed_hours >= max_runtime_hours:
                        self._log(f"Max runtime reached ({max_runtime_hours}h)")
                        break

                self._log(f"\n{'='*50}")
                self._log(f"Autonomous cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # 1. Sync index
                sync_result = self.sync()

                # 2. Check for changes
                changes = self._change_state
                if changes.files_added or changes.files_modified:
                    self._log(f"Changes detected: +{len(changes.files_added)}, ~{len(changes.files_modified)}")

                    if on_change:
                        on_change(changes)

                    # 3. Run tasks
                    for task in default_tasks:
                        self._log(f"Running task: {task[:50]}...")
                        try:
                            result = self.act(task, max_iterations=5)
                            if result.success:
                                self._log(f"Task completed in {result.duration_seconds:.1f}s")
                            else:
                                self._log(f"Task incomplete: {result.output[:100]}")
                        except Exception as e:
                            self._log(f"Task error: {e}")

                # Wait for next interval
                self._log(f"Sleeping for {interval_minutes} minutes...")
                for _ in range(interval_minutes * 60):
                    if not self._daemon_running:
                        break
                    time.sleep(1)

        except KeyboardInterrupt:
            self._log("Interrupted by user")
        finally:
            self._daemon_running = False
            self._log("Autonomous mode stopped")

    def stop_autonomous(self):
        """Stop the autonomous daemon."""
        self._daemon_running = False

    def start_daemon(self, **kwargs):
        """Start autonomous mode in a background thread."""
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._log("Daemon already running")
            return

        self._daemon_thread = threading.Thread(
            target=self.run_autonomous,
            kwargs=kwargs,
            daemon=True
        )
        self._daemon_thread.start()
        self._log("Daemon started in background")

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    def find_duplicates(self, directory: Optional[Path] = None, by_content: bool = True) -> List[Dict]:
        """
        Find duplicate files.

        Args:
            directory: Directory to scan (default: ~/Documents)
            by_content: If True, compare by content hash; else by name

        Returns:
            List of duplicate groups
        """
        target = directory or (Path.home() / 'Documents')
        self._log(f"Scanning for duplicates in {target}...")

        # Group by hash or name
        groups: Dict[str, List[Path]] = {}

        for file_path in target.rglob('*'):
            if not file_path.is_file():
                continue
            if file_path.name.startswith('.'):
                continue

            try:
                if by_content:
                    # Hash first 1MB
                    hasher = hashlib.md5()
                    with open(file_path, 'rb') as f:
                        hasher.update(f.read(1024 * 1024))
                    key = hasher.hexdigest()
                else:
                    key = file_path.name

                if key not in groups:
                    groups[key] = []
                groups[key].append(file_path)

            except (OSError, PermissionError):
                pass

        # Find duplicates
        duplicates = []
        for key, files in groups.items():
            if len(files) > 1:
                duplicates.append({
                    'key': key,
                    'files': [str(f) for f in files],
                    'count': len(files),
                    'size': files[0].stat().st_size if files else 0,
                })

        duplicates.sort(key=lambda x: x['size'], reverse=True)
        self._log(f"Found {len(duplicates)} duplicate groups")

        return duplicates

    def get_stats(self) -> Dict[str, Any]:
        """Get agent and index statistics."""
        indexer = self._get_indexer()
        index_stats = indexer.get_stats()

        return {
            'index': index_stats,
            'last_scan': self._change_state.last_scan.isoformat() if self._change_state.last_scan else None,
            'tracked_files': len(self._change_state.file_mtimes),
            'daemon_running': self._daemon_running,
        }


def main():
    """CLI entry point for autonomous data agent."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous Data Agent - Self-managing home directory automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  data-agent ask "What Python projects do I have?"
  data-agent act "Find all TODO comments and create a summary"
  data-agent sync                      # Sync index with changes
  data-agent sync --force              # Force full reindex
  data-agent search "authentication"   # Search indexed content
  data-agent duplicates                # Find duplicate files
  data-agent stats                     # Show statistics
  data-agent daemon --interval 30      # Run autonomous monitoring
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question about your data')
    ask_parser.add_argument('question', help='Your question')
    ask_parser.add_argument('--top-k', '-k', type=int, default=10, help='Number of docs to retrieve')

    # Act command
    act_parser = subparsers.add_parser('act', help='Perform a complex action')
    act_parser.add_argument('task', help='Task description')
    act_parser.add_argument('--max-iterations', '-n', type=int, default=10, help='Max iterations')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search indexed content')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--top-k', '-k', type=int, default=20, help='Number of results')
    search_parser.add_argument('--type', '-t', choices=['code', 'document', 'conversation'], help='Filter by type')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync index with file changes')
    sync_parser.add_argument('--force', '-f', action='store_true', help='Force full reindex')

    # Duplicates command
    dup_parser = subparsers.add_parser('duplicates', help='Find duplicate files')
    dup_parser.add_argument('--directory', '-d', help='Directory to scan')
    dup_parser.add_argument('--by-name', action='store_true', help='Compare by name instead of content')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')

    # Daemon command
    daemon_parser = subparsers.add_parser('daemon', help='Run in autonomous mode')
    daemon_parser.add_argument('--interval', '-i', type=int, default=30, help='Minutes between checks')
    daemon_parser.add_argument('--max-hours', type=float, help='Maximum runtime in hours')

    # Global args
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    agent = AutonomousDataAgent(verbose=not args.quiet)

    if args.command == 'ask':
        response = agent.ask(args.question, top_k=args.top_k)
        print(response)
        return 0

    elif args.command == 'act':
        result = agent.act(args.task, max_iterations=args.max_iterations)
        print(f"\n{'='*60}")
        print(f"Success: {result.success}")
        print(f"Type: {result.action_type.value}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"{'='*60}")
        print(result.output)
        return 0 if result.success else 1

    elif args.command == 'search':
        results = agent.search(args.query, top_k=args.top_k, doc_type=args.type)
        print(f"\nFound {len(results)} results:\n")
        for i, doc in enumerate(results, 1):
            print(f"--- {i}. {doc.get('relative_path', 'unknown')} ({doc.get('score', 0):.3f}) ---")
            print(f"Type: {doc.get('type', 'unknown')}")
            print(f"Preview: {doc.get('content', '')[:200]}...")
            print()
        return 0

    elif args.command == 'sync':
        result = agent.sync(force=args.force)
        print(f"\nSync complete:")
        print(f"  Mode: {result.get('mode', 'unknown')}")
        print(f"  Indexed: {result.get('indexed', 0)} documents")
        if result.get('duration'):
            print(f"  Duration: {result['duration']:.1f}s")
        return 0

    elif args.command == 'duplicates':
        directory = Path(args.directory) if args.directory else None
        duplicates = agent.find_duplicates(directory=directory, by_content=not args.by_name)

        if not duplicates:
            print("No duplicates found.")
            return 0

        print(f"\nFound {len(duplicates)} duplicate groups:\n")
        for i, dup in enumerate(duplicates[:20], 1):
            size_kb = dup['size'] / 1024
            print(f"{i}. {dup['count']} copies ({size_kb:.1f} KB each):")
            for f in dup['files'][:5]:
                print(f"   - {f}")
            if len(dup['files']) > 5:
                print(f"   ... and {len(dup['files']) - 5} more")
            print()
        return 0

    elif args.command == 'stats':
        stats = agent.get_stats()
        print(f"\nAutonomous Data Agent Statistics")
        print(f"{'='*40}")
        print(f"Index collection: {stats['index'].get('collection_name', 'N/A')}")
        print(f"Indexed documents: {stats['index'].get('document_count', 'N/A')}")
        print(f"Tracked files: {stats.get('tracked_files', 0)}")
        print(f"Last scan: {stats.get('last_scan', 'Never')}")
        print(f"Daemon running: {stats.get('daemon_running', False)}")
        return 0

    elif args.command == 'daemon':
        print(f"Starting autonomous daemon (interval: {args.interval}m)")
        print("Press Ctrl+C to stop\n")
        agent.run_autonomous(
            interval_minutes=args.interval,
            max_runtime_hours=args.max_hours,
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
