import json
import logging
from dataclasses import dataclass
from typing import List
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

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
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is not installed.")
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        # Determine embedding dimension
        self.dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Dimension: {self.dim}")

    def embed(self, chunks: List[Chunk]) -> EmbeddingBatch:
        if not chunks:
            return EmbeddingBatch(embeddings=np.array([]), chunks=[], model_name=self.model_name, dim=self.dim)

        texts_to_embed = []
        for chunk in chunks:
            # Format: scheme_name \n\n text
            formatted_text = f"{chunk.scheme_name}\n\n{chunk.text}"
            texts_to_embed.append(formatted_text)

        logger.info(f"Encoding {len(texts_to_embed)} chunks...")
        embeddings = self.model.encode(
            texts_to_embed, 
            batch_size=32, 
            show_progress_bar=False, 
            convert_to_numpy=True,
            normalize_embeddings=True # Recommended for bge models
        )
        
        # Ensure it's float32
        embeddings = embeddings.astype(np.float32)
        
        return EmbeddingBatch(
            embeddings=embeddings,
            chunks=chunks,
            model_name=self.model_name,
            dim=self.dim
        )
