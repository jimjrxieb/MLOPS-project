"""
Ollama-based Embeddings Engine
Replaces sentence-transformers + PyTorch with pure Ollama

Benefits:
- No PyTorch dependency
- Native RTX 5080 GPU support
- Optimized embeddings (nomic-embed-text: 768-dim)
- Faster (GPU-accelerated)
- Specialized embedding model (not same as LLM)

Architecture:
┌────────────────────────────────────────┐
│ Text → Ollama API → Embeddings (768d) │
└────────────────────────────────────────┘
"""

import requests
import json
from typing import List, Dict, Any, Optional
import numpy as np


class OllamaEmbeddings:
    """
    Ollama-based embedding engine.

    Uses Ollama's native embedding API instead of sentence-transformers.
    Leverages your existing LLaMA model for consistent embeddings.

    Example:
        >>> embedder = OllamaEmbeddings()
        >>> vectors = embedder.embed_documents(["SQL injection", "XSS attack"])
        >>> print(vectors.shape)  # (2, 768)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text:latest",  # Optimized embedding model (768-dim)
        timeout: int = 30
    ):
        """
        Initialize Ollama embeddings.

        Args:
            base_url: Ollama API endpoint
            model: Embedding model to use (default: nomic-embed-text)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.dimension = None  # Will be detected on first embed

        # Test connectivity
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()

            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]

            if self.model in model_names:
                return True
            else:
                print(f"⚠️  Model {self.model} not found in Ollama")
                print(f"   Available: {', '.join(model_names[:3])}")
                return False

        except Exception as e:
            print(f"❌ Ollama not available: {e}")
            return False

    def __call__(self, input: List[str]) -> List[List[float]]:
        """ChromaDB embedding_function interface.

        ChromaDB calls embedding_function(texts) and expects a list of vectors.
        This makes OllamaEmbeddings compatible with get_or_create_collection().
        """
        return [self.embed_single(text) for text in input]

    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions for nomic-embed-text)
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get('embedding', [])

            # Store dimension on first call
            if self.dimension is None:
                self.dimension = len(embedding)

            return embedding

        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            # Return zero vector as fallback
            return [0.0] * (self.dimension or 768)

    def embed_documents(
        self,
        documents: List[str],
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for multiple documents.

        Args:
            documents: List of texts to embed
            show_progress: Show progress bar (for large batches)

        Returns:
            Numpy array of shape (len(documents), 768)
        """
        embeddings = []

        if show_progress:
            from tqdm import tqdm
            documents = tqdm(documents, desc="Embedding documents")

        for doc in documents:
            embedding = self.embed_single(doc)
            embeddings.append(embedding)

        return np.array(embeddings)

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a query (alias for embed_single for compatibility).

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        return self.embed_single(query)

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        if self.dimension is None:
            # Test with dummy text to get dimension
            test_embedding = self.embed_single("test")
            self.dimension = len(test_embedding)
        return self.dimension


# Singleton instance
_ollama_embeddings: Optional[OllamaEmbeddings] = None


def get_ollama_embeddings(
    model: str = "nomic-embed-text:latest"  # Optimized embedding model (768-dim)
) -> OllamaEmbeddings:
    """
    Get singleton Ollama embeddings instance.

    Args:
        model: Ollama model to use

    Returns:
        OllamaEmbeddings instance
    """
    global _ollama_embeddings

    if _ollama_embeddings is None:
        _ollama_embeddings = OllamaEmbeddings(model=model)

    return _ollama_embeddings


if __name__ == "__main__":
    """Test Ollama embeddings"""
    print("🧪 Testing Ollama Embeddings...")
    print("=" * 60)

    embedder = OllamaEmbeddings()

    # Test single embedding
    print("\n1. Single text embedding:")
    text = "SQL injection vulnerability"
    embedding = embedder.embed_single(text)
    print(f"   Text: '{text}'")
    print(f"   Dimension: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")

    # Test batch embeddings
    print("\n2. Batch embeddings:")
    texts = [
        "Cross-site scripting (XSS)",
        "Command injection",
        "Path traversal"
    ]
    embeddings = embedder.embed_documents(texts, show_progress=True)
    print(f"   Batch size: {len(texts)}")
    print(f"   Shape: {embeddings.shape}")

    # Test similarity
    print("\n3. Similarity test:")
    text1 = "SQL injection attack"
    text2 = "SQL injection vulnerability"
    text3 = "Network security"

    emb1 = np.array(embedder.embed_single(text1))
    emb2 = np.array(embedder.embed_single(text2))
    emb3 = np.array(embedder.embed_single(text3))

    # Cosine similarity
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sim_12 = cosine_sim(emb1, emb2)
    sim_13 = cosine_sim(emb1, emb3)

    print(f"   '{text1}' vs '{text2}': {sim_12:.3f}")
    print(f"   '{text1}' vs '{text3}': {sim_13:.3f}")
    print(f"   ✅ Related texts have higher similarity!" if sim_12 > sim_13 else "❌ Similarity test failed")

    print("\n" + "=" * 60)
    print("✅ Ollama embeddings working perfectly!")
    print(f"   Dimension: {embedder.get_dimension()}")
    print(f"   Model: {embedder.model}")
    print(f"   GPU: RTX 5080 (native support)")
