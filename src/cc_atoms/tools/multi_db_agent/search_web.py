#!/usr/bin/env python3
"""
Data Search Web UI - Browser-based interface for querying indexed data

Supports two search backends:
1. HomeIndexer (Chroma) - Default, local vector store
2. Elysia (Weaviate) - Personal knowledge base with richer data sources

Usage:
    search-web              # Start server on port 8765
    search-web --port 9000  # Custom port
    search-web --elysia     # Use Elysia/Weaviate backend

Then open: http://localhost:8765
"""
import os
import sys
import json
import html
import urllib.parse
import time
import logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, List, Dict, Any

# Configure logging for deep search visibility
LOG_DIR = Path.home() / '.cache' / 'multi_db_agent' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
ELYSIA_LOG_FILE = LOG_DIR / 'elysia_search.jsonl'

# Set up file logger
elysia_logger = logging.getLogger('elysia_search')
elysia_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(ELYSIA_LOG_FILE)
file_handler.setFormatter(logging.Formatter('%(message)s'))  # JSON lines format
elysia_logger.addHandler(file_handler)


def log_elysia_search(event_type: str, data: Dict[str, Any]):
    """Log Elysia search events with deep detail"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event': event_type,
        **data
    }
    elysia_logger.info(json.dumps(log_entry))


def get_html_template():
    """Return HTML template with CSS (no format strings in CSS)"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Data Search - cc_atoms</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; margin-bottom: 20px; }
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            outline: none;
        }
        input[type="text"]:focus { border-color: #007aff; }
        button {
            padding: 12px 24px;
            font-size: 16px;
            background: #007aff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        button:hover { background: #0056b3; }
        button.secondary { background: #6c757d; }
        button.secondary:hover { background: #545b62; }
        button.deep { background: #28a745; }
        button.deep:hover { background: #218838; }
        .spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #007aff; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .filters { margin-bottom: 15px; }
        .filters label { margin-right: 15px; cursor: pointer; }
        .results {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .result {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }
        .result:last-child { border-bottom: none; }
        .result:hover { background: #f8f9fa; }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .result-title { font-weight: 600; color: #007aff; font-size: 15px; }
        .result-score {
            background: #e8f4fd;
            color: #007aff;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .result-meta { color: #666; font-size: 13px; margin-bottom: 8px; }
        .result-content {
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 12px;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 200px;
            overflow-y: auto;
        }
        .type-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            margin-right: 8px;
        }
        .type-code { background: #d4edda; color: #155724; }
        .type-document { background: #cce5ff; color: #004085; }
        .type-conversation { background: #fff3cd; color: #856404; }
        .ai-response {
            background: #f0f7ff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .loading { text-align: center; padding: 40px; color: #666; }
        .stats { text-align: right; color: #666; font-size: 13px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>🔍 Data Search</h1>
    <p style="color: #666; margin-top: -10px;">__STATS__ | <a href="/history">📊 View History</a> | <a href="/elysia-logs">📜 Elysia Logs</a></p>

    <div class="search-box">
        <input type="text" id="query" placeholder="Search your files, code, and conversations..."
               value="__QUERY__" autofocus>
        <button onclick="doSearch()">Search</button>
        <button class="deep" onclick="doAsk()" title="Deep analysis using iterating agent (~1-2 min)">Ask AI (Deep)</button>
    </div>

    <div class="filters">
        <label><input type="radio" name="type" value="all" __CHECKED_ALL__> All</label>
        <label><input type="radio" name="type" value="code" __CHECKED_CODE__> Code</label>
        <label><input type="radio" name="type" value="document" __CHECKED_DOC__> Documents</label>
        <label><input type="radio" name="type" value="conversation" __CHECKED_CONV__> Conversations</label>
    </div>

    <div class="filters" style="margin-top: 5px;">
        <strong style="margin-right: 10px;">Backend:</strong>
        <label><input type="radio" name="backend" value="chroma" __CHECKED_CHROMA__> HomeIndexer (Chroma)</label>
        <label><input type="radio" name="backend" value="elysia" __CHECKED_ELYSIA__> Elysia (Weaviate)</label>
    </div>

    <div class="stats">__STATS__</div>

    __CONTENT__

    <script>
        document.getElementById('query').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') doSearch();
        });

        function getType() {
            return document.querySelector('input[name="type"]:checked').value;
        }

        function getBackend() {
            return document.querySelector('input[name="backend"]:checked').value;
        }

        function doSearch() {
            var q = document.getElementById('query').value;
            if (!q) return;
            window.location.href = '/search?q=' + encodeURIComponent(q) + '&type=' + getType() + '&backend=' + getBackend();
        }

        function doAsk() {
            var q = document.getElementById('query').value;
            if (!q) return;
            window.location.href = '/ask?q=' + encodeURIComponent(q) + '&backend=' + getBackend();
        }
    </script>
</body>
</html>'''


class SearchHandler(BaseHTTPRequestHandler):
    agent = None  # HomeIndexer-based agent
    elysia_client = None  # Elysia/Weaviate client
    default_backend = 'chroma'  # Can be 'chroma' or 'elysia'

    def log_message(self, format, *args):
        pass  # Suppress logs

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        query = params.get('q', [''])[0]
        doc_type = params.get('type', ['all'])[0]
        backend = params.get('backend', [self.default_backend])[0]

        if parsed.path == '/search' and query:
            content = self.do_search(query, doc_type, backend)
        elif parsed.path == '/ask' and query:
            content = self.do_ask(query, backend)
        elif parsed.path == '/history':
            return self.serve_history()
        elif parsed.path == '/elysia-logs':
            return self.serve_elysia_logs()
        else:
            content = '<div class="loading">Enter a query above to search your indexed data.</div>'

        # Build response using simple string replacement
        html_content = get_html_template()
        html_content = html_content.replace('__QUERY__', html.escape(query))
        html_content = html_content.replace('__CONTENT__', content)
        html_content = html_content.replace('__STATS__', f"Index: {self.get_doc_count(backend)} documents")
        html_content = html_content.replace('__CHECKED_ALL__', 'checked' if doc_type == 'all' else '')
        html_content = html_content.replace('__CHECKED_CODE__', 'checked' if doc_type == 'code' else '')
        html_content = html_content.replace('__CHECKED_DOC__', 'checked' if doc_type == 'document' else '')
        html_content = html_content.replace('__CHECKED_CONV__', 'checked' if doc_type == 'conversation' else '')
        html_content = html_content.replace('__CHECKED_CHROMA__', 'checked' if backend == 'chroma' else '')
        html_content = html_content.replace('__CHECKED_ELYSIA__', 'checked' if backend == 'elysia' else '')

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def get_doc_count(self, backend: str = 'chroma'):
        try:
            if backend == 'elysia':
                # For Elysia, we'd need to query each collection
                return 'Elysia'
            elif self.agent:
                stats = self.agent.get_stats()
                return stats.get('index', {}).get('document_count', 'N/A')
        except:
            pass
        return 'N/A'

    def do_search(self, query: str, doc_type: str, backend: str = 'chroma') -> str:
        start_time = time.time()

        # Log search start
        log_elysia_search('search_start', {
            'query': query,
            'doc_type': doc_type,
            'backend': backend
        })

        try:
            if backend == 'elysia':
                return self.do_elysia_search(query, doc_type, start_time)
            else:
                return self.do_chroma_search(query, doc_type, start_time)
        except Exception as e:
            duration = time.time() - start_time
            log_elysia_search('search_error', {
                'query': query,
                'backend': backend,
                'error': str(e),
                'duration_seconds': duration
            })
            return f'<div class="loading">Error: {html.escape(str(e))}</div>'

    def do_chroma_search(self, query: str, doc_type: str, start_time: float) -> str:
        """Search using HomeIndexer/Chroma backend"""
        if not self.agent:
            return '<div class="loading">Agent not initialized</div>'

        dtype = None if doc_type == 'all' else doc_type
        results = self.agent.search(query, top_k=20, doc_type=dtype)

        duration = time.time() - start_time
        log_elysia_search('chroma_search_complete', {
            'query': query,
            'doc_type': doc_type,
            'num_results': len(results),
            'duration_seconds': duration
        })

        if not results:
            return '<div class="loading">No results found</div>'

        return self._format_search_results(results, 'chroma')

    def do_elysia_search(self, query: str, doc_type: str, start_time: float) -> str:
        """Search using Elysia/Weaviate backend"""
        try:
            from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia, ElysiaSyncConfig

            config = ElysiaSyncConfig()

            # Map doc_type to Elysia collections
            if doc_type == 'all':
                collections = None  # Search all
            elif doc_type == 'code':
                collections = [config.code_collection]
            elif doc_type == 'document':
                collections = [config.documents_collection]
            elif doc_type == 'conversation':
                collections = [config.conversations_collection]
            else:
                collections = None

            log_elysia_search('elysia_query_start', {
                'query': query,
                'collections': collections or ['all'],
                'config': {
                    'weaviate_url': config.weaviate_url,
                    'is_local': config.is_local,
                    'embedding_provider': config.embedding_provider
                }
            })

            # Execute query
            results = query_elysia(query, collections=collections, config=config, limit=20)

            duration = time.time() - start_time

            # Deep logging of results
            log_elysia_search('elysia_search_complete', {
                'query': query,
                'doc_type': doc_type,
                'collections_searched': collections or ['all'],
                'num_results': len(results),
                'duration_seconds': duration,
                'result_sources': [r.get('source', 'unknown')[:100] for r in results[:10]],
                'result_types': [r.get('type', 'unknown') for r in results]
            })

            if not results:
                log_elysia_search('elysia_no_results', {
                    'query': query,
                    'note': 'No results returned from Elysia. Index may be empty or connection failed.'
                })
                return '<div class="loading">No results found in Elysia. Try syncing data first: <code>elysia-sync sync</code></div>'

            # Convert Elysia results to standard format
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'filename': Path(r.get('source', 'unknown')).name if r.get('source') else 'Unknown',
                    'type': r.get('type', 'unknown'),
                    'relative_path': r.get('source', ''),
                    'content': r.get('content', ''),
                    'score': 0.0,  # Elysia doesn't return scores in basic query
                    'metadata': r.get('metadata', {})
                })

            return self._format_search_results(formatted_results, 'elysia')

        except ImportError as e:
            log_elysia_search('elysia_import_error', {'error': str(e)})
            return f'<div class="loading">Elysia not available: {html.escape(str(e))}</div>'
        except Exception as e:
            log_elysia_search('elysia_error', {'error': str(e), 'type': type(e).__name__})
            import traceback
            log_elysia_search('elysia_traceback', {'traceback': traceback.format_exc()})
            return f'<div class="loading">Elysia error: {html.escape(str(e))}</div>'

    def _format_search_results(self, results: List[Dict[str, Any]], backend: str) -> str:
        """Format search results as HTML"""
        html_parts = [f'<div class="results"><div class="stats" style="text-align:left;padding:10px;background:#e8f4fd;border-radius:8px 8px 0 0;">Backend: <strong>{backend.upper()}</strong> | Results: {len(results)}</div>']

        for r in results:
            type_class = f"type-{r.get('type', 'unknown')}"
            content_preview = html.escape(r.get('content', '')[:500])
            score = r.get('score', 0)
            score_display = f"{score:.3f}" if score > 0 else "N/A"

            html_parts.append(f'''
            <div class="result">
                <div class="result-header">
                    <span class="result-title">{html.escape(r.get('filename', 'Unknown'))}</span>
                    <span class="result-score">{score_display}</span>
                </div>
                <div class="result-meta">
                    <span class="type-badge {type_class}">{r.get('type', 'unknown')}</span>
                    {html.escape(r.get('relative_path', ''))}
                </div>
                <div class="result-content">{content_preview}</div>
            </div>
            ''')

        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def do_ask(self, query: str, backend: str = 'chroma') -> str:
        start_time = time.time()

        log_elysia_search('ask_start', {
            'query': query,
            'backend': backend
        })

        try:
            if backend == 'elysia':
                return self.do_elysia_ask(query, start_time)
            else:
                return self.do_chroma_ask(query, start_time)
        except Exception as e:
            duration = time.time() - start_time
            log_elysia_search('ask_error', {
                'query': query,
                'backend': backend,
                'error': str(e),
                'duration_seconds': duration
            })
            return f'<div class="loading">Error: {html.escape(str(e))}</div>'

    def do_chroma_ask(self, query: str, start_time: float) -> str:
        """Deep analysis using Chroma/HomeIndexer backend"""
        if not self.agent:
            return '<div class="loading">Agent not initialized</div>'

        # Use the iterating agent (act) for deep analysis instead of simple ask
        # Prepend context to make it clear this is the user's own data
        enhanced_query = f"I am the owner of this data and am asking about my own files. {query}"

        result = self.agent.act(enhanced_query, max_iterations=5)

        duration = time.time() - start_time
        log_elysia_search('chroma_ask_complete', {
            'query': query,
            'success': result.success,
            'duration_seconds': duration
        })

        if result.success:
            # Format the output nicely
            output = result.output
            # Convert markdown-style formatting to HTML
            output = output.replace('**', '<strong>').replace('**', '</strong>')
            output = output.replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
            output = output.replace('EXIT_LOOP_NOW', '')  # Remove termination signal
            return f'<div class="ai-response"><strong>Backend: CHROMA</strong><hr>{html.escape(output)}</div>'
        else:
            return f'<div class="ai-response">Analysis incomplete. {html.escape(result.output)}</div>'

    def do_elysia_ask(self, query: str, start_time: float) -> str:
        """Deep analysis using Elysia/Weaviate backend with context extraction"""
        try:
            from cc_atoms.tools.elysia_sync.elysia_sync import get_relevant_context, ElysiaSyncConfig

            log_elysia_search('elysia_ask_start', {
                'query': query,
                'note': 'Using get_relevant_context for intelligent synthesis'
            })

            config = ElysiaSyncConfig()

            # Use the intelligent context extraction which uses an atom internally
            result = get_relevant_context(query, config=config, max_iterations=5, verbose=False)

            duration = time.time() - start_time

            log_elysia_search('elysia_ask_complete', {
                'query': query,
                'found': result.get('found', False),
                'num_sources': len(result.get('sources', [])),
                'num_raw_results': len(result.get('raw_results', [])),
                'duration_seconds': duration
            })

            if result.get('found'):
                context = result.get('context', 'No context extracted')
                sources = result.get('sources', [])

                sources_html = ''
                if sources:
                    sources_html = '<hr><strong>Sources:</strong><ul>'
                    for src in sources:
                        sources_html += f'<li>{html.escape(src)}</li>'
                    sources_html += '</ul>'

                return f'''<div class="ai-response">
                    <strong>Backend: ELYSIA</strong> | Duration: {duration:.1f}s
                    <hr>
                    {html.escape(context)}
                    {sources_html}
                </div>'''
            else:
                # Show raw results if no synthesized context
                raw_results = result.get('raw_results', [])
                if raw_results:
                    return f'''<div class="ai-response">
                        <strong>Backend: ELYSIA</strong> | No synthesized context, showing raw results
                        <hr>
                        Found {len(raw_results)} related documents but could not synthesize context.
                        Try a more specific query.
                    </div>'''
                else:
                    return '<div class="loading">No results found in Elysia. Try syncing data first: <code>elysia-sync sync</code></div>'

        except ImportError as e:
            log_elysia_search('elysia_ask_import_error', {'error': str(e)})
            return f'<div class="loading">Elysia not available: {html.escape(str(e))}</div>'
        except Exception as e:
            log_elysia_search('elysia_ask_error', {'error': str(e), 'type': type(e).__name__})
            import traceback
            log_elysia_search('elysia_ask_traceback', {'traceback': traceback.format_exc()})
            return f'<div class="loading">Elysia error: {html.escape(str(e))}</div>'

    def serve_elysia_logs(self):
        """Serve the Elysia search logs page"""
        try:
            html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Elysia Search Logs - cc_atoms</title>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .log-entry { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #28a745; }
        .log-entry.error { border-left-color: #dc3545; }
        .log-entry.search { border-left-color: #007aff; }
        .log-entry.elysia { border-left-color: #6f42c1; }
        .log-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .log-type { font-weight: bold; }
        .timestamp { color: #666; font-size: 14px; }
        .log-content { font-family: monospace; font-size: 13px; background: #f8f9fa; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; max-height: 300px; overflow-y: auto; }
        a { color: #007aff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .refresh { float: right; }
    </style>
</head>
<body>
    <h1>Elysia Search Logs <a class="refresh" href="/elysia-logs">🔄 Refresh</a></h1>
    <p><a href="/">← Back to Search</a></p>
'''

            # Read Elysia log file
            logs = []
            if ELYSIA_LOG_FILE.exists():
                with open(ELYSIA_LOG_FILE) as f:
                    for line in f:
                        if line.strip():
                            try:
                                logs.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            # Show most recent first
            logs = list(reversed(logs[-100:]))

            if not logs:
                html_content += '<p>No Elysia logs yet. Try searching with the Elysia backend.</p>'
            else:
                html_content += f'<p>Showing {len(logs)} most recent log entries</p>'

                for log in logs:
                    event = log.get('event', 'unknown')
                    timestamp = log.get('timestamp', '')[:19]

                    # Determine CSS class
                    css_class = 'log-entry'
                    if 'error' in event.lower():
                        css_class += ' error'
                    elif 'elysia' in event.lower():
                        css_class += ' elysia'
                    elif 'search' in event.lower():
                        css_class += ' search'

                    # Format log content (excluding timestamp and event)
                    content = {k: v for k, v in log.items() if k not in ['timestamp', 'event']}
                    content_str = json.dumps(content, indent=2)

                    html_content += f'''
<div class="{css_class}">
    <div class="log-header">
        <span class="log-type">{html.escape(event.upper())}</span>
        <span class="timestamp">{html.escape(timestamp)}</span>
    </div>
    <div class="log-content">{html.escape(content_str)}</div>
</div>'''

            html_content += '''
</body>
</html>'''

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))

        except Exception as e:
            error_html = f'<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>'
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(error_html.encode('utf-8'))

    def serve_history(self):
        """Serve the query/indexing history page"""
        try:
            query_log = Path.home() / '.cache' / 'multi_db_agent' / 'logs' / 'queries.jsonl'
            index_log = Path.home() / '.cache' / 'multi_db_agent' / 'logs' / 'indexing.jsonl'

            html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Query History - cc_atoms</title>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .log-entry { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #007aff; }
        .log-entry.indexing { border-left-color: #28a745; }
        .log-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .log-type { font-weight: bold; color: #007aff; }
        .log-type.indexing { color: #28a745; }
        .timestamp { color: #666; font-size: 14px; }
        .query { font-size: 16px; margin: 5px 0; }
        .meta { color: #666; font-size: 14px; }
        .results { margin-top: 10px; }
        .result-item { padding: 5px; margin: 5px 0; background: #f8f9fa; border-radius: 4px; font-size: 13px; }
        .score { color: #28a745; font-weight: bold; }
        a { color: #007aff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Query & Indexing History</h1>
    <p><a href="/">← Back to Search</a></p>
'''

            # Read query logs (most recent first)
            queries = []
            if query_log.exists():
                with open(query_log) as f:
                    queries = [json.loads(line) for line in f if line.strip()]
                queries = list(reversed(queries[-50:]))  # Last 50, newest first

            # Read indexing logs
            indexes = []
            if index_log.exists():
                with open(index_log) as f:
                    indexes = [json.loads(line) for line in f if line.strip()]
                indexes = list(reversed(indexes[-10:]))  # Last 10, newest first

            # Combine and sort by timestamp
            all_logs = [{'type': 'query', 'data': q} for q in queries]
            all_logs += [{'type': 'indexing', 'data': i} for i in indexes]
            all_logs.sort(key=lambda x: x['data']['timestamp'], reverse=True)

            for log in all_logs[:100]:  # Show last 100 events
                if log['type'] == 'query':
                    q = log['data']
                    html_content += f'''
<div class="log-entry">
    <div class="log-header">
        <span class="log-type">{q['type'].upper()}</span>
        <span class="timestamp">{q['timestamp'][:19]}</span>
    </div>
    <div class="query">"{html.escape(q['query'])}"</div>
    <div class="meta">Duration: {q.get('duration_seconds', 0):.2f}s'''

                    if q.get('iterations'):
                        html_content += f" | Iterations: {q['iterations']}"

                    if q.get('num_results'):
                        html_content += f" | Results: {q['num_results']}"

                    html_content += '</div>'

                    # Show top 3 results
                    if q.get('search_results'):
                        html_content += '<div class="results">Top results:'
                        for r in q['search_results'][:3]:
                            file_short = r['file'].split('/')[-1]
                            html_content += f'''
                <div class="result-item">
                    <span class="score">{r['score']:.3f}</span> -
                    <strong>{html.escape(file_short)}</strong> ({r['type']})
                </div>'''
                        html_content += '</div>'

                    html_content += '</div>'

                elif log['type'] == 'indexing':
                    idx = log['data']
                    stats = idx['stats']
                    html_content += f'''
<div class="log-entry indexing">
    <div class="log-header">
        <span class="log-type indexing">INDEXING ({idx['mode']})</span>
        <span class="timestamp">{idx['timestamp'][:19]}</span>
    </div>
    <div class="meta">
        Duration: {idx['duration_seconds']:.1f}s |
        Files: {idx['files_indexed']} indexed, {idx['files_skipped']} skipped |
        Code: {stats['code_files']}, Docs: {stats['documents']}, Conversations: {stats['conversations']}
    </div>
</div>'''

            html_content += '''
</body>
</html>'''

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))

        except Exception as e:
            error_html = f'<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>'
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(error_html.encode('utf-8'))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Data Search Web UI")
    parser.add_argument('--port', '-p', type=int, default=8765, help='Port (default: 8765)')
    parser.add_argument('--elysia', '-e', action='store_true', help='Use Elysia/Weaviate as default backend')
    args = parser.parse_args()

    print(f"Starting Data Search Web UI...")

    # Set default backend based on flag
    if args.elysia:
        SearchHandler.default_backend = 'elysia'
        print(f"Default backend: Elysia (Weaviate)")
    else:
        SearchHandler.default_backend = 'chroma'
        print(f"Default backend: Chroma (HomeIndexer)")

    # Always try to load HomeIndexer/Chroma agent
    print(f"Loading Chroma agent...")
    try:
        from cc_atoms.tools.multi_db_agent.autonomous_agent import AutonomousDataAgent
        SearchHandler.agent = AutonomousDataAgent(verbose=False)
        print(f"  Chroma agent loaded successfully")
    except Exception as e:
        print(f"  Warning: Could not load Chroma agent: {e}")

    # Test Elysia availability
    print(f"Checking Elysia availability...")
    try:
        from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia, ElysiaSyncConfig
        config = ElysiaSyncConfig()
        print(f"  Elysia module available")
        print(f"  Weaviate URL: {config.weaviate_url}")
        print(f"  Embedding provider: {config.embedding_provider}")
        print(f"  Is local: {config.is_local}")

        # Log startup
        log_elysia_search('server_start', {
            'port': args.port,
            'default_backend': SearchHandler.default_backend,
            'weaviate_url': config.weaviate_url,
            'embedding_provider': config.embedding_provider,
            'is_local': config.is_local
        })
    except ImportError as e:
        print(f"  Warning: Elysia not available: {e}")
        log_elysia_search('elysia_unavailable', {'error': str(e)})
    except Exception as e:
        print(f"  Warning: Elysia config error: {e}")
        log_elysia_search('elysia_config_error', {'error': str(e)})

    server = HTTPServer(('localhost', args.port), SearchHandler)
    print(f"\n✓ Server running at: http://localhost:{args.port}")
    print(f"  Open this URL in your browser")
    print(f"  Backend toggle available in the UI")
    print(f"  Elysia logs: http://localhost:{args.port}/elysia-logs")
    print(f"  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        log_elysia_search('server_shutdown', {'reason': 'keyboard_interrupt'})
        server.shutdown()


if __name__ == "__main__":
    main()
