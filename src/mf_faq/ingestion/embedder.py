import json
import logging
from dataclasses import dataclass
from typing import List
import numpy as np

try:
    from fastembed import TextEmbedding
except ImportError:
    TextEmbedding = None

from mf_faq.ingestion.chunker.service import Chunk

logger = logging.getLogger("mf_faq.embedder")

@dataclass
class EmbeddingBatch:
    embeddings: np.ndarray
    chunks: List[Chunk]
    model_name: str
    dim: int

class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        if TextEmbedding is None:
            raise ImportError("fastembed is not installed.")
        
        logger.info(f"Loading fastembed model: {self.model_name}")
        self.model = TextEmbedding(model_name=self.model_name, cache_dir="/tmp/fastembed")
        self.dim = 384
        logger.info(f"Model loaded. Dimension: {self.dim}")

    def embed(self, chunks: List[Chunk]) -> EmbeddingBatch:
        if not chunks:
            return EmbeddingBatch(embeddings=np.array([]), chunks=[], model_name=self.model_name, dim=self.dim)

        texts_to_embed = []
        for chunk in chunks:
            formatted_text = f"{chunk.scheme_name}\n\n{chunk.text}"
            texts_to_embed.append(formatted_text)

        logger.info(f"Encoding {len(texts_to_embed)} chunks with fastembed...")
        embeddings_generator = self.model.embed(texts_to_embed)
        embeddings = np.vstack(list(embeddings_generator))
        
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        embeddings = embeddings / norms
        embeddings = embeddings.astype(np.float32)
        
        return EmbeddingBatch(
            embeddings=embeddings,
            chunks=chunks,
            model_name=self.model_name,
            dim=self.dim
        )

    def embed_query(self, query: str) -> np.ndarray:
        """Embeds a single query string for dense retrieval."""
        embeddings_generator = self.model.embed([query])
        embeddings = np.vstack(list(embeddings_generator))
        
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        embeddings = embeddings / norms
        return embeddings.astype(np.float32)
