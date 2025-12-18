#!/usr/bin/env python3
"""
Live Integration Tests for Search Backends

NO MOCKING - These tests hit real backends with real queries.
Tests both Chroma (HomeIndexer) and Elysia (Weaviate) search backends.

Usage:
    python3 -m pytest tests/test_search_backends.py -v
    python3 tests/test_search_backends.py  # Direct execution
"""
import os
import sys
import json
import time
import unittest
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


class TestChromaBackend(unittest.TestCase):
    """Live tests for HomeIndexer/Chroma search backend"""

    @classmethod
    def setUpClass(cls):
        """Initialize the Chroma agent once for all tests"""
        print("\n" + "="*60)
        print("CHROMA BACKEND TESTS - LIVE QUERIES")
        print("="*60)

        from cc_atoms.tools.multi_db_agent.autonomous_agent import AutonomousDataAgent
        cls.agent = AutonomousDataAgent(verbose=False)

        # Get stats to verify connection
        stats = cls.agent.get_stats()
        cls.doc_count = stats.get('index', {}).get('document_count', 0)
        print(f"Connected to Chroma index with {cls.doc_count} documents")

    def test_01_index_has_documents(self):
        """Verify the index has documents to search"""
        self.assertGreater(self.doc_count, 0,
            "Chroma index is empty. Run 'data-agent sync' first.")
        print(f"  Index contains {self.doc_count} documents")

    def test_02_search_python_code(self):
        """Search for Python-related content"""
        query = "python function definition"
        results = self.agent.search(query, top_k=10)

        print(f"\n  Query: '{query}'")
        print(f"  Results: {len(results)}")

        self.assertGreater(len(results), 0, "No results for Python search")

        # Check result structure
        first = results[0]
        self.assertIn('content', first)
        self.assertIn('score', first)
        self.assertIn('type', first)

        print(f"  Top result: {first.get('filename', 'unknown')} (score: {first.get('score', 0):.3f})")
        print(f"  Content preview: {first.get('content', '')[:100]}...")

    def test_03_search_conversations(self):
        """Search for conversation content"""
        query = "claude code conversation"
        results = self.agent.search(query, top_k=10, doc_type='conversation')

        print(f"\n  Query: '{query}' (type: conversation)")
        print(f"  Results: {len(results)}")

        # Conversations might not exist in index
        if results:
            first = results[0]
            self.assertEqual(first.get('type'), 'conversation')
            print(f"  Top result: {first.get('filename', 'unknown')}")
        else:
            print("  No conversation results (index may not have conversations)")

    def test_04_search_code_files(self):
        """Search specifically for code files"""
        query = "import json"
        results = self.agent.search(query, top_k=10, doc_type='code')

        print(f"\n  Query: '{query}' (type: code)")
        print(f"  Results: {len(results)}")

        self.assertGreater(len(results), 0, "No code results found")

        for r in results[:3]:
            self.assertEqual(r.get('type'), 'code')
            print(f"    - {r.get('filename', 'unknown')} (score: {r.get('score', 0):.3f})")

    def test_05_search_elysia_related(self):
        """Search for elysia-related content (meta test!)"""
        query = "elysia weaviate vector search"
        results = self.agent.search(query, top_k=10)

        print(f"\n  Query: '{query}'")
        print(f"  Results: {len(results)}")

        self.assertGreater(len(results), 0, "No elysia-related results")

        # Should find elysia_sync.py or related files
        filenames = [r.get('filename', '') for r in results]
        print(f"  Found files: {filenames[:5]}")

    def test_06_search_performance(self):
        """Test search performance with timing"""
        queries = [
            "authentication login user",
            "database query sql",
            "http request api",
            "error handling exception",
            "file read write path"
        ]

        print(f"\n  Performance test with {len(queries)} queries:")

        times = []
        for query in queries:
            start = time.time()
            results = self.agent.search(query, top_k=10)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"    '{query[:30]}': {len(results)} results in {elapsed:.3f}s")

        avg_time = sum(times) / len(times)
        print(f"  Average search time: {avg_time:.3f}s")

        # Search should be reasonably fast
        self.assertLess(avg_time, 5.0, "Average search time too slow (>5s)")

    def test_07_search_empty_query_handling(self):
        """Test handling of edge case queries"""
        # Very short query
        results = self.agent.search("a", top_k=5)
        print(f"\n  Short query 'a': {len(results)} results")

        # Query with special characters
        results = self.agent.search("def __init__(self):", top_k=5)
        print(f"  Special chars query: {len(results)} results")

        # Long query
        long_query = "how do I implement a vector search system with embeddings and semantic similarity"
        results = self.agent.search(long_query, top_k=5)
        print(f"  Long query: {len(results)} results")


class TestElysiaBackend(unittest.TestCase):
    """Live tests for Elysia/Weaviate search backend"""

    @classmethod
    def setUpClass(cls):
        """Initialize Elysia connection"""
        print("\n" + "="*60)
        print("ELYSIA BACKEND TESTS - LIVE QUERIES")
        print("="*60)

        cls.elysia_available = False
        cls.has_data = False

        try:
            from cc_atoms.tools.elysia_sync.elysia_sync import (
                query_elysia, ElysiaSyncConfig, WeaviateClient
            )
            cls.query_elysia = query_elysia
            cls.config = ElysiaSyncConfig()

            print(f"Elysia config:")
            print(f"  Weaviate URL: {cls.config.weaviate_url}")
            print(f"  Embedding provider: {cls.config.embedding_provider}")
            print(f"  Is local: {cls.config.is_local}")

            # Test connection
            client = WeaviateClient(cls.config)
            if client.connect():
                cls.elysia_available = True
                print("  Connection: SUCCESS")

                # Check if there's data
                test_results = query_elysia("test", limit=1)
                cls.has_data = len(test_results) > 0
                print(f"  Has data: {cls.has_data}")

                client.close()
            else:
                print("  Connection: FAILED")

        except ImportError as e:
            print(f"Elysia import failed: {e}")
        except Exception as e:
            print(f"Elysia setup error: {e}")

    def test_01_elysia_available(self):
        """Verify Elysia module can be imported"""
        try:
            from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia
            print("  Elysia module imported successfully")
        except ImportError as e:
            self.fail(f"Cannot import elysia_sync: {e}")

    def test_02_elysia_config_valid(self):
        """Verify Elysia configuration is valid"""
        from cc_atoms.tools.elysia_sync.elysia_sync import ElysiaSyncConfig
        config = ElysiaSyncConfig()

        print(f"\n  Config validation:")
        print(f"    weaviate_url: {config.weaviate_url}")
        print(f"    embedding_provider: {config.embedding_provider}")
        print(f"    gemini_api_key set: {bool(config.gemini_api_key)}")

        self.assertIsNotNone(config.weaviate_url)
        self.assertIn(config.embedding_provider, ['gemini', 'openai', 'none'])

    @unittest.skipUnless(lambda: TestElysiaBackend.elysia_available, "Elysia not available")
    def test_03_elysia_connection(self):
        """Test Elysia/Weaviate connection"""
        if not self.elysia_available:
            self.skipTest("Elysia connection not available")

        from cc_atoms.tools.elysia_sync.elysia_sync import WeaviateClient

        client = WeaviateClient(self.config)
        connected = client.connect()

        print(f"\n  Weaviate connection: {'SUCCESS' if connected else 'FAILED'}")

        if connected:
            client.close()

        self.assertTrue(connected, "Failed to connect to Weaviate")

    def test_04_elysia_search_code(self):
        """Search for code using Elysia"""
        if not self.elysia_available:
            self.skipTest("Elysia not available")

        from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia
        query = "python class definition"
        results = query_elysia(query, limit=10)

        print(f"\n  Query: '{query}'")
        print(f"  Results: {len(results)}")

        if results:
            for r in results[:3]:
                print(f"    - {r.get('source', 'unknown')[:60]}... (type: {r.get('type')})")
        else:
            print("  No results (index may be empty - run 'elysia-sync sync')")

    def test_05_elysia_search_conversations(self):
        """Search conversations using Elysia"""
        if not self.elysia_available:
            self.skipTest("Elysia not available")

        from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia, ElysiaSyncConfig
        config = ElysiaSyncConfig()

        query = "claude conversation"
        results = query_elysia(
            query,
            collections=[config.conversations_collection],
            limit=10
        )

        print(f"\n  Query: '{query}' (conversations only)")
        print(f"  Results: {len(results)}")

        if results:
            for r in results[:3]:
                print(f"    - {r.get('source', 'unknown')[:60]}...")

    def test_06_elysia_search_all_collections(self):
        """Search across all Elysia collections"""
        if not self.elysia_available:
            self.skipTest("Elysia not available")

        from cc_atoms.tools.elysia_sync.elysia_sync import query_elysia
        query = "vector embedding search"
        results = query_elysia(query, limit=20)

        print(f"\n  Query: '{query}' (all collections)")
        print(f"  Results: {len(results)}")

        # Group by type
        by_type = {}
        for r in results:
            t = r.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1

        print(f"  By type: {by_type}")


class TestSearchLogging(unittest.TestCase):
    """Test the search logging functionality"""

    @classmethod
    def setUpClass(cls):
        print("\n" + "="*60)
        print("SEARCH LOGGING TESTS")
        print("="*60)

        cls.log_file = Path.home() / '.cache' / 'multi_db_agent' / 'logs' / 'elysia_search.jsonl'

    def test_01_log_file_exists(self):
        """Check if log file exists after searches"""
        print(f"\n  Log file: {self.log_file}")
        print(f"  Exists: {self.log_file.exists()}")

        if self.log_file.exists():
            size = self.log_file.stat().st_size
            print(f"  Size: {size} bytes")

    def test_02_log_format_valid(self):
        """Verify log entries are valid JSON"""
        if not self.log_file.exists():
            self.skipTest("Log file doesn't exist yet")

        valid_count = 0
        invalid_count = 0

        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        valid_count += 1

                        # Check required fields
                        self.assertIn('timestamp', entry)
                        self.assertIn('event', entry)
                    except json.JSONDecodeError:
                        invalid_count += 1

        print(f"\n  Valid entries: {valid_count}")
        print(f"  Invalid entries: {invalid_count}")

        self.assertEqual(invalid_count, 0, f"{invalid_count} invalid log entries found")

    def test_03_log_events_recorded(self):
        """Check what events have been logged"""
        if not self.log_file.exists():
            self.skipTest("Log file doesn't exist yet")

        events = {}
        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        event = entry.get('event', 'unknown')
                        events[event] = events.get(event, 0) + 1
                    except:
                        pass

        print(f"\n  Event types recorded:")
        for event, count in sorted(events.items()):
            print(f"    {event}: {count}")

    def test_04_recent_logs(self):
        """Show most recent log entries"""
        if not self.log_file.exists():
            self.skipTest("Log file doesn't exist yet")

        entries = []
        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass

        print(f"\n  Last 5 log entries:")
        for entry in entries[-5:]:
            ts = entry.get('timestamp', '')[:19]
            event = entry.get('event', 'unknown')
            query = entry.get('query', '')[:30] if entry.get('query') else ''
            print(f"    [{ts}] {event}: {query}")


class TestSearchWebIntegration(unittest.TestCase):
    """Integration tests for the search_web.py module"""

    @classmethod
    def setUpClass(cls):
        print("\n" + "="*60)
        print("SEARCH WEB INTEGRATION TESTS")
        print("="*60)

    def test_01_import_search_web(self):
        """Verify search_web module imports correctly"""
        from cc_atoms.tools.multi_db_agent.search_web import (
            SearchHandler,
            get_html_template,
            log_elysia_search
        )
        print("  search_web module imported successfully")

    def test_02_html_template_valid(self):
        """Verify HTML template contains expected elements"""
        from cc_atoms.tools.multi_db_agent.search_web import get_html_template

        template = get_html_template()

        # Check for key UI elements
        checks = [
            ('Backend toggle', 'name="backend"'),
            ('Chroma option', 'value="chroma"'),
            ('Elysia option', 'value="elysia"'),
            ('Search button', 'onclick="doSearch()"'),
            ('Ask AI button', 'onclick="doAsk()"'),
            ('Type filters', 'name="type"'),
            ('Elysia logs link', '/elysia-logs'),
        ]

        print("\n  Template validation:")
        for name, pattern in checks:
            found = pattern in template
            status = "OK" if found else "MISSING"
            print(f"    {name}: {status}")
            self.assertIn(pattern, template, f"Template missing: {name}")

    def test_03_log_function_works(self):
        """Test the logging function"""
        from cc_atoms.tools.multi_db_agent.search_web import log_elysia_search

        # Log a test event
        log_elysia_search('test_event', {
            'test_id': 'integration_test',
            'timestamp_check': datetime.now().isoformat()
        })

        print("\n  Test log entry written")

        # Verify it was written
        log_file = Path.home() / '.cache' / 'multi_db_agent' / 'logs' / 'elysia_search.jsonl'

        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
                last_line = lines[-1] if lines else ''

                if 'test_event' in last_line:
                    print("  Test event found in log file")
                else:
                    print("  Test event not found in last line")


class TestInterestingQueries(unittest.TestCase):
    """Test with interesting, realistic queries"""

    @classmethod
    def setUpClass(cls):
        print("\n" + "="*60)
        print("INTERESTING QUERY TESTS")
        print("="*60)

        from cc_atoms.tools.multi_db_agent.autonomous_agent import AutonomousDataAgent
        cls.agent = AutonomousDataAgent(verbose=False)

    def test_01_find_authentication_code(self):
        """Find authentication-related code"""
        results = self.agent.search("authentication login password hash", top_k=5)
        print(f"\n  'authentication login password hash': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_02_find_api_endpoints(self):
        """Find API endpoint definitions"""
        results = self.agent.search("api endpoint route handler request response", top_k=5)
        print(f"\n  'api endpoint route handler': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_03_find_database_operations(self):
        """Find database-related code"""
        results = self.agent.search("database query insert update delete sql", top_k=5)
        print(f"\n  'database query sql': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_04_find_error_handling(self):
        """Find error handling patterns"""
        results = self.agent.search("try except error handling exception raise", top_k=5)
        print(f"\n  'error handling exception': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_05_find_test_files(self):
        """Find test files"""
        results = self.agent.search("unittest pytest test case assert", top_k=5)
        print(f"\n  'unittest pytest test': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_06_find_configuration(self):
        """Find configuration files"""
        results = self.agent.search("config configuration settings environment variable", top_k=5)
        print(f"\n  'config settings environment': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_07_find_atom_related(self):
        """Find atom framework code"""
        results = self.agent.search("atom runtime iteration prompt claude", top_k=5)
        print(f"\n  'atom runtime iteration prompt': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_08_find_embedding_code(self):
        """Find embedding/vector code"""
        results = self.agent.search("embedding vector gemini openai text-embedding", top_k=5)
        print(f"\n  'embedding vector gemini': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_09_semantic_search_concepts(self):
        """Test semantic understanding with conceptual query"""
        results = self.agent.search("how to make code run faster optimization performance", top_k=5)
        print(f"\n  'how to make code run faster': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")

    def test_10_natural_language_query(self):
        """Test natural language question"""
        results = self.agent.search("where is the main entry point for the application", top_k=5)
        print(f"\n  'where is the main entry point': {len(results)} results")
        for r in results[:3]:
            print(f"    - {r.get('filename', 'unknown')}")


def run_tests():
    """Run all tests with verbose output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes in order
    suite.addTests(loader.loadTestsFromTestCase(TestChromaBackend))
    suite.addTests(loader.loadTestsFromTestCase(TestElysiaBackend))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchWebIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestInterestingQueries))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\nFailed tests:")
        for test, trace in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nErrors:")
        for test, trace in result.errors:
            print(f"  - {test}")

    return result


if __name__ == "__main__":
    run_tests()
