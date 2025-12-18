"""
Vector Database Connector

Supports Chroma (local, free), Weaviate, and integrates with elysia_sync.
"""
import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VectorResult:
    """Result from vector search."""
    answer: str
    sources: List[str]
    documents: List[Dict]
    source: str = "vector"


def get_gemini_embedding(text: str, api_key: str, model: str = "text-embedding-004") -> List[float]:
    """Generate a single embedding using Gemini API."""
    import urllib.request
    import urllib.error

    text = text[:8000] if len(text) > 8000 else text

    if not text.strip():
        return [0.0] * 768

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"

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
            return result.get("embedding", {}).get("values", [0.0] * 768)
    except Exception as e:
        print(f"Embedding error: {e}")
        return [0.0] * 768


class VectorConnector:
    """
    Connect to vector databases for semantic search.

    Supports:
    - Chroma (local, free, persistent)
    - Weaviate (embedded or cloud)
    - LlamaIndex VectorStoreIndex
    """

    def __init__(
        self,
        store_type: str = "chroma",
        persist_dir: Optional[str] = None,
        collection_name: str = "documents",
        embedding_provider: str = "auto",  # "auto", "gemini", "default"
        **kwargs
    ):
        """
        Initialize vector connector.

        Args:
            store_type: "chroma", "weaviate", or "llamaindex"
            persist_dir: Directory for persistent storage (Chroma)
            collection_name: Name of the collection/index
            embedding_provider: "auto" (detect from collection), "gemini", or "default"
            **kwargs: Additional store-specific options
        """
        self.store_type = store_type
        self.persist_dir = persist_dir or str(Path.home() / ".cache" / "multi_db_agent" / collection_name)
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.kwargs = kwargs

        self._store = None
        self._index = None
        self._gemini_api_key = os.getenv("GEMINI_API_KEY")

        self._init_store()

    def _init_store(self):
        """Initialize the vector store."""
        if self.store_type == "chroma":
            self._init_chroma()
        elif self.store_type == "weaviate":
            self._init_weaviate()
        elif self.store_type == "llamaindex":
            self._init_llamaindex()
        else:
            raise ValueError(f"Unknown store type: {self.store_type}")

    def _init_chroma(self):
        """Initialize Chroma (local, persistent, free)."""
        try:
            import chromadb

            # Create persistent client
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )

            # Auto-detect embedding dimension if collection has data
            if self.embedding_provider == "auto":
                try:
                    # Try to peek at an existing embedding
                    peek = self._collection.peek(limit=1)
                    if peek and peek.get('embeddings') and len(peek['embeddings']) > 0:
                        dim = len(peek['embeddings'][0])
                        if dim == 768:  # Gemini dimension
                            self.embedding_provider = "gemini"
                        else:
                            self.embedding_provider = "default"
                except:
                    self.embedding_provider = "default"
        except ImportError:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")

    def _init_weaviate(self):
        """Initialize Weaviate connection."""
        try:
            import weaviate
            from weaviate.embedded import EmbeddedOptions

            # Use embedded Weaviate (no Docker needed)
            self._client = weaviate.WeaviateClient(
                embedded_options=EmbeddedOptions(
                    persistence_data_path=self.persist_dir,
                )
            )
            self._client.connect()
        except ImportError:
            raise ImportError("weaviate-client not installed. Install with: pip install weaviate-client")

    def _init_llamaindex(self):
        """Initialize LlamaIndex vector store."""
        try:
            from llama_index.core import VectorStoreIndex, StorageContext
            from llama_index.vector_stores.chroma import ChromaVectorStore
            import chromadb

            # Use Chroma as backend for LlamaIndex
            chroma_client = chromadb.PersistentClient(path=self.persist_dir)
            chroma_collection = chroma_client.get_or_create_collection(self.collection_name)
            self._store = ChromaVectorStore(chroma_collection=chroma_collection)
            self._storage_context = StorageContext.from_defaults(vector_store=self._store)
        except ImportError:
            raise ImportError("LlamaIndex with Chroma not installed")

    def add_documents(self, documents: List[Dict[str, Any]], embeddings: Optional[List[List[float]]] = None):
        """
        Add documents to the vector store.

        Args:
            documents: List of {"id": str, "content": str, "metadata": dict}
            embeddings: Optional pre-computed embeddings
        """
        if self.store_type == "chroma":
            ids = [doc.get("id", str(i)) for i, doc in enumerate(documents)]
            contents = [doc.get("content", "") for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]

            if embeddings:
                self._collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                # Chroma will generate embeddings
                self._collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas
                )

    def query(self, query: str, top_k: int = 5, **kwargs) -> VectorResult:
        """
        Semantic search query.

        Args:
            query: Natural language query
            top_k: Number of results to return

        Returns:
            VectorResult with answer and source documents
        """
        if self.store_type == "chroma":
            return self._query_chroma(query, top_k)
        elif self.store_type == "weaviate":
            return self._query_weaviate(query, top_k)
        else:
            return self._query_llamaindex(query, top_k)

    def _query_chroma(self, query: str, top_k: int) -> VectorResult:
        """Query Chroma collection."""
        # Use Gemini embeddings if configured
        if self.embedding_provider == "gemini" and self._gemini_api_key:
            query_embedding = get_gemini_embedding(query, self._gemini_api_key)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
        else:
            # Use Chroma's default embeddings
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

        documents = []
        sources = []

        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else None

                documents.append({
                    "content": doc,
                    "metadata": metadata,
                    "score": 1 - (distance or 0)  # Convert distance to similarity
                })
                sources.append(metadata.get("source", f"doc_{i}"))

        # Generate answer from top results
        if documents:
            answer = f"Found {len(documents)} relevant documents:\n"
            for i, doc in enumerate(documents[:3], 1):
                preview = doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"]
                answer += f"\n{i}. {preview}"
        else:
            answer = "No relevant documents found."

        return VectorResult(answer=answer, sources=sources, documents=documents)

    def _query_weaviate(self, query: str, top_k: int) -> VectorResult:
        """Query Weaviate collection."""
        collection = self._client.collections.get(self.collection_name)

        response = collection.query.near_text(
            query=query,
            limit=top_k
        )

        documents = []
        sources = []

        for obj in response.objects:
            documents.append({
                "content": obj.properties.get("content", ""),
                "metadata": obj.properties,
            })
            sources.append(obj.properties.get("source", ""))

        answer = f"Found {len(documents)} relevant documents"
        return VectorResult(answer=answer, sources=sources, documents=documents)

    def _query_llamaindex(self, query: str, top_k: int) -> VectorResult:
        """Query via LlamaIndex."""
        if self._index is None:
            from llama_index.core import VectorStoreIndex
            self._index = VectorStoreIndex.from_vector_store(
                self._store,
                storage_context=self._storage_context
            )

        retriever = self._index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)

        documents = []
        sources = []

        for node in nodes:
            documents.append({
                "content": node.node.text,
                "metadata": node.node.metadata,
                "score": node.score
            })
            sources.append(node.node.metadata.get("source", ""))

        answer = f"Found {len(documents)} relevant documents"
        return VectorResult(answer=answer, sources=sources, documents=documents)

    def close(self):
        """Close connections."""
        if self.store_type == "weaviate" and self._client:
            self._client.close()


class MultiVectorConnector:
    """Manage multiple vector store connections."""

    def __init__(self, configs: Dict[str, Dict]):
        """
        Initialize multiple vector stores.

        Args:
            configs: {
                "docs": {"store_type": "chroma", "collection_name": "documents"},
                "support": {"store_type": "chroma", "collection_name": "tickets"},
            }
        """
        self.connectors = {
            name: VectorConnector(**config)
            for name, config in configs.items()
        }

    def query(self, query: str, collection: Optional[str] = None, top_k: int = 5) -> Dict[str, VectorResult]:
        """Query one or all collections."""
        if collection:
            return {collection: self.connectors[collection].query(query, top_k)}

        results = {}
        for name, connector in self.connectors.items():
            try:
                results[name] = connector.query(query, top_k)
            except Exception as e:
                results[name] = VectorResult(
                    answer=f"Error: {e}",
                    sources=[],
                    documents=[]
                )

        return results

    def close(self):
        """Close all connections."""
        for connector in self.connectors.values():
            connector.close()
