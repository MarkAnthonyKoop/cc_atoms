#!/usr/bin/env python3
"""
Data Search GUI - Visual interface for querying your indexed data

A Tkinter-based GUI that provides:
- Natural language search across all indexed files
- Real-time results with relevance scores
- Detailed view of matched documents
- Quick actions (ask, search, analyze)
- History of recent queries

Usage:
    search-gui                    # Launch the GUI
    python -m cc_atoms.tools.multi_db_agent.search_gui

The GUI connects to:
- HomeIndexer (Chroma + Gemini embeddings)
- AutonomousDataAgent (for ask/act commands)
- MemoryProvider (relevance scoring)
"""
import os
import sys
import json
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


@dataclass
class SearchResult:
    """A single search result"""
    title: str
    path: str
    doc_type: str
    score: float
    content: str
    metadata: Dict[str, Any]


class DataSearchGUI:
    """
    Main GUI application for data search.

    Provides a clean interface to search your indexed files, documents,
    and Claude conversations.
    """

    def __init__(self):
        if not TKINTER_AVAILABLE:
            raise ImportError("tkinter not available")

        # Create main window
        self.root = tk.Tk()
        self.root.title("Data Search - cc_atoms")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('aqua' if sys.platform == 'darwin' else 'clam')

        # State
        self.results: List[SearchResult] = []
        self.selected_result: Optional[SearchResult] = None
        self.query_history: List[str] = []
        self.is_searching = False

        # Queue for thread communication
        self.result_queue = queue.Queue()

        # Build UI
        self._build_ui()

        # Start result checker
        self._check_results()

        # Load agents (in background)
        self._init_agents_async()

    def _build_ui(self):
        """Build the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === TOP: Search bar ===
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=('Helvetica', 14)
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self._do_search())
        self.search_entry.bind('<Up>', self._history_up)
        self.search_entry.bind('<Down>', self._history_down)

        # Search button
        self.search_btn = ttk.Button(
            search_frame,
            text="Search",
            command=self._do_search
        )
        self.search_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Ask button (uses LLM)
        self.ask_btn = ttk.Button(
            search_frame,
            text="Ask AI",
            command=self._do_ask
        )
        self.ask_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Mode selector
        self.mode_var = tk.StringVar(value="all")
        mode_frame = ttk.Frame(search_frame)
        mode_frame.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Radiobutton(mode_frame, text="All", variable=self.mode_var, value="all").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Code", variable=self.mode_var, value="code").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Docs", variable=self.mode_var, value="document").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Convs", variable=self.mode_var, value="conversation").pack(side=tk.LEFT)

        # === MIDDLE: Split pane ===
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left: Results list
        results_frame = ttk.LabelFrame(paned, text="Results", padding="5")
        paned.add(results_frame, weight=1)

        # Results listbox with scrollbar
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.results_listbox = tk.Listbox(
            list_frame,
            font=('Helvetica', 11),
            selectmode=tk.SINGLE,
            activestyle='dotbox'
        )
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.results_listbox.bind('<<ListboxSelect>>', self._on_result_select)
        self.results_listbox.bind('<Double-1>', self._open_file)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.config(yscrollcommand=scrollbar.set)

        # Right: Detail view
        detail_frame = ttk.LabelFrame(paned, text="Details", padding="5")
        paned.add(detail_frame, weight=2)

        # Detail header
        self.detail_header = ttk.Label(
            detail_frame,
            text="Select a result to view details",
            font=('Helvetica', 12, 'bold')
        )
        self.detail_header.pack(fill=tk.X, pady=(0, 5))

        # Metadata
        self.detail_meta = ttk.Label(
            detail_frame,
            text="",
            font=('Helvetica', 10),
            foreground='gray'
        )
        self.detail_meta.pack(fill=tk.X, pady=(0, 5))

        # Content view
        self.detail_content = scrolledtext.ScrolledText(
            detail_frame,
            wrap=tk.WORD,
            font=('Menlo', 11),
            state=tk.DISABLED
        )
        self.detail_content.pack(fill=tk.BOTH, expand=True)

        # === BOTTOM: Status bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Ready. Type a query and press Enter or click Search.")
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=('Helvetica', 10)
        )
        self.status_label.pack(side=tk.LEFT)

        # Index stats
        self.stats_var = tk.StringVar(value="Loading...")
        self.stats_label = ttk.Label(
            status_frame,
            textvariable=self.stats_var,
            font=('Helvetica', 10),
            foreground='gray'
        )
        self.stats_label.pack(side=tk.RIGHT)

        # Focus search entry
        self.search_entry.focus()

    def _init_agents_async(self):
        """Initialize agents in background thread"""
        def init():
            try:
                from cc_atoms.tools.multi_db_agent.autonomous_agent import AutonomousDataAgent
                self.agent = AutonomousDataAgent(verbose=False)
                stats = self.agent.get_stats()
                doc_count = stats.get('index', {}).get('document_count', 'N/A')
                self.root.after(0, lambda: self.stats_var.set(f"Index: {doc_count} documents"))
                self.root.after(0, lambda: self.status_var.set("Ready. Type a query and press Enter."))
            except Exception as e:
                self.agent = None
                self.root.after(0, lambda: self.status_var.set(f"Error loading agent: {e}"))

        threading.Thread(target=init, daemon=True).start()

    def _do_search(self):
        """Execute a search"""
        query = self.search_var.get().strip()
        if not query:
            return

        if self.is_searching:
            return

        # Add to history
        if query not in self.query_history:
            self.query_history.append(query)

        self.is_searching = True
        self.status_var.set(f"Searching: {query}...")
        self.search_btn.config(state=tk.DISABLED)
        self.ask_btn.config(state=tk.DISABLED)

        # Clear results
        self.results_listbox.delete(0, tk.END)
        self.results = []

        # Get filter
        mode = self.mode_var.get()
        doc_type = None if mode == "all" else mode

        # Search in background
        def search():
            try:
                if not self.agent:
                    raise Exception("Agent not initialized")

                results = self.agent.search(query, top_k=20, doc_type=doc_type)

                search_results = []
                for doc in results:
                    sr = SearchResult(
                        title=doc.get('filename', 'Unknown'),
                        path=doc.get('relative_path', doc.get('source', '')),
                        doc_type=doc.get('type', 'unknown'),
                        score=doc.get('score', 0),
                        content=doc.get('content', ''),
                        metadata=doc
                    )
                    search_results.append(sr)

                self.result_queue.put(('search_done', search_results))

            except Exception as e:
                self.result_queue.put(('error', str(e)))

        threading.Thread(target=search, daemon=True).start()

    def _do_ask(self):
        """Ask the AI a question"""
        query = self.search_var.get().strip()
        if not query:
            return

        if self.is_searching:
            return

        # Add to history
        if query not in self.query_history:
            self.query_history.append(query)

        self.is_searching = True
        self.status_var.set(f"Asking AI: {query}...")
        self.search_btn.config(state=tk.DISABLED)
        self.ask_btn.config(state=tk.DISABLED)

        # Ask in background
        def ask():
            try:
                if not self.agent:
                    raise Exception("Agent not initialized")

                response = self.agent.ask(query, top_k=10)
                self.result_queue.put(('ask_done', response))

            except Exception as e:
                self.result_queue.put(('error', str(e)))

        threading.Thread(target=ask, daemon=True).start()

    def _check_results(self):
        """Check for results from background threads"""
        try:
            while True:
                msg_type, data = self.result_queue.get_nowait()

                if msg_type == 'search_done':
                    self.results = data
                    self._display_results()
                    self.status_var.set(f"Found {len(data)} results")

                elif msg_type == 'ask_done':
                    self._display_ai_response(data)
                    self.status_var.set("AI response received")

                elif msg_type == 'error':
                    self.status_var.set(f"Error: {data}")
                    messagebox.showerror("Error", data)

                self.is_searching = False
                self.search_btn.config(state=tk.NORMAL)
                self.ask_btn.config(state=tk.NORMAL)

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self._check_results)

    def _display_results(self):
        """Display search results in the listbox"""
        self.results_listbox.delete(0, tk.END)

        for i, result in enumerate(self.results):
            # Format: [type] score filename
            type_icon = {'code': '📄', 'document': '📝', 'conversation': '💬'}.get(result.doc_type, '❓')
            line = f"{type_icon} {result.score:.2f}  {result.title}"
            self.results_listbox.insert(tk.END, line)

            # Color by score
            if result.score >= 0.7:
                self.results_listbox.itemconfig(i, fg='#006400')  # Dark green
            elif result.score >= 0.5:
                self.results_listbox.itemconfig(i, fg='#228B22')  # Forest green
            else:
                self.results_listbox.itemconfig(i, fg='#666666')  # Gray

    def _display_ai_response(self, response: str):
        """Display AI response in detail view"""
        self.detail_header.config(text="AI Response")
        self.detail_meta.config(text=f"Query: {self.search_var.get()}")

        self.detail_content.config(state=tk.NORMAL)
        self.detail_content.delete(1.0, tk.END)
        self.detail_content.insert(tk.END, response)
        self.detail_content.config(state=tk.DISABLED)

    def _on_result_select(self, event):
        """Handle result selection"""
        selection = self.results_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx >= len(self.results):
            return

        result = self.results[idx]
        self.selected_result = result

        # Update detail view
        self.detail_header.config(text=result.title)
        self.detail_meta.config(
            text=f"Type: {result.doc_type} | Score: {result.score:.3f} | Path: {result.path}"
        )

        self.detail_content.config(state=tk.NORMAL)
        self.detail_content.delete(1.0, tk.END)
        self.detail_content.insert(tk.END, result.content)
        self.detail_content.config(state=tk.DISABLED)

    def _open_file(self, event):
        """Open selected file in default editor"""
        if not self.selected_result:
            return

        path = self.selected_result.metadata.get('source', '')
        if path and Path(path).exists():
            import subprocess
            subprocess.run(['open', path])

    def _history_up(self, event):
        """Navigate up in query history"""
        if self.query_history:
            # Get current position
            current = self.search_var.get()
            try:
                idx = self.query_history.index(current)
                if idx > 0:
                    self.search_var.set(self.query_history[idx - 1])
            except ValueError:
                self.search_var.set(self.query_history[-1])

    def _history_down(self, event):
        """Navigate down in query history"""
        if self.query_history:
            current = self.search_var.get()
            try:
                idx = self.query_history.index(current)
                if idx < len(self.query_history) - 1:
                    self.search_var.set(self.query_history[idx + 1])
                else:
                    self.search_var.set("")
            except ValueError:
                pass

    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def main():
    """Entry point"""
    if not TKINTER_AVAILABLE:
        print("Error: tkinter not available")
        print("On macOS, tkinter is included with Python from python.org")
        print("Or try: brew install python-tk")
        return 1

    # Check if running in chromadb venv
    venv_python = Path.home() / '.venvs' / 'chromadb-env' / 'bin' / 'python'
    current_python = Path(sys.executable)

    if 'chromadb-env' not in str(current_python):
        # Re-launch in chromadb venv
        import subprocess
        result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        return result.returncode

    try:
        app = DataSearchGUI()
        app.run()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
