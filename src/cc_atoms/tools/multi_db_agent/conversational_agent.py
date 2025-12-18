#!/usr/bin/env python3
"""
Conversational Agent - An embedded atom that converses about your indexed data

This agent uses the home directory index to answer questions about your:
- Code projects
- Documents
- Claude conversations
- Downloads

Usage:
    from cc_atoms.tools.multi_db_agent.conversational_agent import create_conversational_agent

    agent = create_conversational_agent()
    response = agent.ask("What Python projects do I have?")
    print(response)

CLI:
    python -m cc_atoms.tools.multi_db_agent.conversational_agent "What are my recent projects?"
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure we can import from cc_atoms
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


CONVERSATIONAL_SYSTEM_PROMPT = """# Personal Knowledge Assistant

You are a helpful AI assistant with access to the user's personal knowledge base.
You can search through their:
- Code files from ~/claude and ~/Projects
- Documents from ~/Documents, ~/Desktop, ~/Downloads
- Claude Code conversation history

## Your Role

Answer questions about the user's files, projects, conversations, and documents.
Be specific - reference actual file paths and content when relevant.

## Guidelines

1. When asked about projects or code, search and summarize what you find
2. Reference specific files by their relative paths (e.g., "claude/cc/src/...")
3. For conversations, summarize the topics and key points
4. If you can't find relevant information, say so clearly
5. Provide concise but complete answers

## Available Context

You will receive search results from the knowledge base. Use them to answer questions.
If the context doesn't contain enough information, say what you found and suggest the user ask more specifically.
"""


class ConversationalAgent:
    """
    An agent that converses about indexed home directory data.

    Uses:
    - HomeIndexer for searching the Chroma vector store
    - Gemini for generating conversational responses
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "home_directory",
        verbose: bool = False,
    ):
        from cc_atoms.tools.multi_db_agent.home_indexer import HomeIndexer, HomeIndexerConfig

        self.verbose = verbose

        # Connect to existing index
        config = HomeIndexerConfig(
            persist_dir=persist_dir or str(Path.home() / '.cache' / 'multi_db_agent' / 'home_index'),
            collection_name=collection_name,
        )

        self.indexer = HomeIndexer(config=config, verbose=False)
        self._gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not self._gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

    def _log(self, msg: str):
        if self.verbose:
            print(f"[ConversationalAgent] {msg}")

    def _search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search the indexed content."""
        try:
            results = self.indexer.query(query, top_k=top_k)
            return results
        except Exception as e:
            self._log(f"Search error: {e}")
            return []

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format search results as context for the LLM."""
        if not results:
            return "No relevant documents found in the knowledge base."

        context_parts = []
        for i, doc in enumerate(results, 1):
            doc_type = doc.get('type', 'unknown')
            rel_path = doc.get('relative_path', doc.get('source', 'unknown'))
            content = doc.get('content', '')[:2000]  # Limit content length
            score = doc.get('score', 0)

            context_parts.append(f"""
--- Document {i} (type: {doc_type}, score: {score:.3f}) ---
Path: {rel_path}
Content:
{content}
""")

        return "\n".join(context_parts)

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for response generation."""
        import urllib.request
        import json

        model = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._gemini_api_key}"

        full_prompt = f"{CONVERSATIONAL_SYSTEM_PROMPT}\n\n{prompt}"

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
            return f"Error generating response: {e}"

    def ask(self, question: str, top_k: int = 10) -> str:
        """
        Ask a question about your indexed data.

        Args:
            question: Your question
            top_k: Number of documents to retrieve for context

        Returns:
            AI-generated response based on your data
        """
        self._log(f"Searching for: {question}")

        # Search the index
        results = self._search(question, top_k=top_k)
        self._log(f"Found {len(results)} relevant documents")

        # Format context
        context = self._format_context(results)

        # Build prompt
        prompt = f"""## User Question
{question}

## Retrieved Context from Knowledge Base
{context}

## Instructions
Based on the context above, answer the user's question.
Be specific and reference actual files/paths when relevant.
If the context doesn't fully answer the question, say what you found and what's missing.
"""

        # Generate response
        self._log("Generating response...")
        response = self._call_gemini(prompt)

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed data."""
        return self.indexer.get_stats()


def create_conversational_agent(
    persist_dir: Optional[str] = None,
    collection_name: str = "home_directory",
    verbose: bool = False,
) -> ConversationalAgent:
    """
    Create a conversational agent connected to your indexed data.

    Args:
        persist_dir: Path to Chroma database (default: ~/.cache/multi_db_agent/home_index)
        collection_name: Name of the collection
        verbose: Print debug info

    Returns:
        ConversationalAgent instance
    """
    return ConversationalAgent(
        persist_dir=persist_dir,
        collection_name=collection_name,
        verbose=verbose,
    )


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Conversational Agent - Ask questions about your indexed data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  conversational-agent "What Python projects do I have?"
  conversational-agent "What have I been working on recently?"
  conversational-agent "Find code related to authentication"
  conversational-agent --interactive
        """
    )

    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")

    args = parser.parse_args()

    try:
        agent = create_conversational_agent(verbose=args.verbose)
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you've indexed your home directory first:")
        print("  home-indexer index")
        return 1

    if args.stats:
        stats = agent.get_stats()
        print(f"Collection: {stats.get('collection_name', 'N/A')}")
        print(f"Documents: {stats.get('document_count', 'N/A')}")
        print(f"Location: {stats.get('persist_dir', 'N/A')}")
        return 0

    if args.interactive:
        print("Conversational Agent (type 'quit' to exit)")
        print("=" * 50)
        print(f"Indexed documents: {agent.get_stats().get('document_count', 'unknown')}")
        print()

        while True:
            try:
                question = input("\nYou: ").strip()
                if question.lower() in ("quit", "exit", "q"):
                    break
                if not question:
                    continue

                response = agent.ask(question)
                print(f"\nAssistant: {response}")

            except KeyboardInterrupt:
                break
            except EOFError:
                break

        print("\nGoodbye!")
        return 0

    elif args.question:
        response = agent.ask(args.question)
        print(response)
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
