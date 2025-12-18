#!/usr/bin/env python3
"""
Tests for the Memory System (MemoryProvider + AtomRuntime integration)

These are REAL tests - no mocking. They test against the actual Chroma index.
Requires: ~/.cache/multi_db_agent/home_index/ to exist with indexed data.

Run: python3 tests/test_memory.py
"""
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestMemoryAvailability(unittest.TestCase):
    """Test that the memory system is properly set up"""

    def test_chromadb_venv_exists(self):
        """Chromadb venv should exist"""
        venv_python = Path.home() / '.venvs' / 'chromadb-env' / 'bin' / 'python'
        self.assertTrue(venv_python.exists(), f"Chromadb venv not found at {venv_python}")

    def test_index_directory_exists(self):
        """Index directory should exist"""
        index_dir = Path.home() / '.cache' / 'multi_db_agent' / 'home_index'
        self.assertTrue(index_dir.exists(), f"Index not found at {index_dir}")

    def test_check_memory_available(self):
        """check_memory_available() should return True"""
        from cc_atoms.atom_core.memory import check_memory_available
        self.assertTrue(check_memory_available())


class TestMemoryProvider(unittest.TestCase):
    """Test the MemoryProvider class"""

    @classmethod
    def setUpClass(cls):
        """Set up once for all tests"""
        from cc_atoms.atom_core.memory import MemoryProvider, check_memory_available
        if not check_memory_available():
            raise unittest.SkipTest("Memory system not available")
        cls.provider = MemoryProvider(verbose=False)

    def test_empty_prompt_not_triggered(self):
        """Empty prompts should not trigger memory"""
        context, docs = self.provider.get_relevant_context("")
        self.assertIsNone(context)
        self.assertEqual(docs, [])

    def test_short_prompt_not_triggered(self):
        """Very short prompts should not trigger memory"""
        context, docs = self.provider.get_relevant_context("hi")
        self.assertIsNone(context)

    def test_unrelated_prompt_not_triggered(self):
        """Unrelated prompts should not trigger memory (score < threshold)"""
        unrelated_prompts = [
            "What is the capital of France?",
            "How do I bake chocolate chip cookies?",
            "What is the weather like today?",
            "Tell me a joke about elephants",
        ]
        for prompt in unrelated_prompts:
            context, docs = self.provider.get_relevant_context(prompt)
            # Should either be None or have low scores
            if docs:
                best_score = docs[0].get('score', 0)
                self.assertLess(best_score, 0.50,
                    f"Unrelated prompt '{prompt}' triggered with score {best_score}")

    def test_related_prompt_triggered(self):
        """Prompts related to indexed content should trigger memory"""
        related_prompts = [
            ("AtomRuntime create ephemeral", 0.55),
            ("EXIT_LOOP_NOW signal", 0.65),
            ("RetryManager class", 0.55),
            ("gui control automation", 0.50),
        ]
        for prompt, min_score in related_prompts:
            context, docs = self.provider.get_relevant_context(prompt)
            self.assertIsNotNone(context, f"Related prompt '{prompt}' should trigger")
            self.assertGreater(len(docs), 0)
            best_score = docs[0].get('score', 0)
            self.assertGreaterEqual(best_score, min_score,
                f"'{prompt}' score {best_score} < expected {min_score}")

    def test_context_format(self):
        """Context should be properly formatted"""
        context, docs = self.provider.get_relevant_context("AtomRuntime")
        self.assertIsNotNone(context)
        self.assertIn("## Relevant Context from Memory", context)
        self.assertIn("relevance:", context)

    def test_enhance_prompt_adds_context(self):
        """enhance_prompt should prepend context to system prompt"""
        original = "You are a helpful assistant."
        user_prompt = "Help me with AtomRuntime"

        enhanced = self.provider.enhance_prompt(original, user_prompt)

        # Should be longer
        self.assertGreater(len(enhanced), len(original))
        # Should end with original
        self.assertTrue(enhanced.endswith(original))
        # Should have context header
        self.assertIn("## Relevant Context from Memory", enhanced)

    def test_enhance_prompt_unchanged_for_unrelated(self):
        """enhance_prompt should not modify for unrelated prompts"""
        original = "You are a helpful assistant."
        user_prompt = "What is the capital of France?"

        enhanced = self.provider.enhance_prompt(original, user_prompt)

        # Should be unchanged
        self.assertEqual(enhanced, original)


class TestAtomRuntimeMemoryIntegration(unittest.TestCase):
    """Test AtomRuntime memory integration"""

    @classmethod
    def setUpClass(cls):
        """Set up once for all tests"""
        from cc_atoms.atom_core.memory import check_memory_available
        if not check_memory_available():
            raise unittest.SkipTest("Memory system not available")

    def test_auto_enables_memory(self):
        """AtomRuntime should auto-enable memory when available"""
        from cc_atoms.atom_core import AtomRuntime

        runtime = AtomRuntime.create_ephemeral(
            system_prompt="Test",
            max_iterations=1,
            use_memory=None  # Auto-detect
        )

        self.assertIsNotNone(runtime.memory_provider)

    def test_can_disable_memory(self):
        """AtomRuntime should allow disabling memory"""
        from cc_atoms.atom_core import AtomRuntime

        runtime = AtomRuntime.create_ephemeral(
            system_prompt="Test",
            max_iterations=1,
            use_memory=False
        )

        self.assertIsNone(runtime.memory_provider)

    def test_memory_threshold_configurable(self):
        """Memory threshold should be configurable"""
        from cc_atoms.atom_core import AtomRuntime

        runtime = AtomRuntime.create_ephemeral(
            system_prompt="Test",
            max_iterations=1,
            use_memory=True,
            memory_threshold=0.75  # Higher threshold
        )

        self.assertEqual(runtime.memory_provider.relevance_threshold, 0.75)


class TestDataAgentIntegration(unittest.TestCase):
    """Test data-agent CLI integration"""

    @classmethod
    def setUpClass(cls):
        """Check data-agent is available"""
        import subprocess
        result = subprocess.run(
            [str(Path.home() / 'claude' / 'cc' / 'bin' / 'data-agent'), '--help'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise unittest.SkipTest("data-agent not available")

    def test_stats_command(self):
        """data-agent stats should work"""
        import subprocess
        result = subprocess.run(
            [str(Path.home() / 'claude' / 'cc' / 'bin' / 'data-agent'), 'stats'],
            capture_output=True,
            text=True,
            timeout=30
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Indexed documents:", result.stdout)

    def test_search_command(self):
        """data-agent search should return results"""
        import subprocess
        result = subprocess.run(
            [str(Path.home() / 'claude' / 'cc' / 'bin' / 'data-agent'),
             'search', 'AtomRuntime', '--top-k', '3'],
            capture_output=True,
            text=True,
            timeout=60
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("results", result.stdout.lower())

    def test_ask_command(self):
        """data-agent ask should return an answer"""
        import subprocess
        result = subprocess.run(
            [str(Path.home() / 'claude' / 'cc' / 'bin' / 'data-agent'),
             'ask', 'What is AtomRuntime?'],
            capture_output=True,
            text=True,
            timeout=120
        )
        self.assertEqual(result.returncode, 0)
        # Should have some substantive response
        self.assertGreater(len(result.stdout), 100)


def run_tests():
    """Run all tests with verbose output"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryAvailability))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestAtomRuntimeMemoryIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataAgentIntegration))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
