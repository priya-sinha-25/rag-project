import logging
from typing import List, Tuple
import numpy as np

from mf_faq.ingestion.indexer import Indexer, IndexHandle
from mf_faq.ingestion.chunker.service import Chunk
from mf_faq.ingestion.embedder import Embedder

logger = logging.getLogger("mf_faq.hybrid")

class HybridRetriever:
    def __init__(self, index_handle: IndexHandle):
        self.index = index_handle
        
        # Load the embedder exactly as dictated by manifest
        model_name = self.index.manifest.get("model", "BAAI/bge-small-en-v1.5")
        logger.info(f"Hybrid loading embedder: {model_name}")
        self.embedder = Embedder(model_name)

    def _reciprocal_rank_fusion(self, dense_ranks: List[str], sparse_ranks: List[str], k=60) -> List[str]:
        """Combine dense and sparse rankings using RRF."""
        scores = {}
        for rank, chunk_id in enumerate(dense_ranks):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            
        for rank, chunk_id in enumerate(sparse_ranks):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            
        # Sort by score descending
        sorted_chunks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [chunk_id for chunk_id, score in sorted_chunks]

    def search(self, query: str, scheme_id: str = None, top_k: int = 15) -> List[Chunk]:
        """Perform dense and sparse search, filter by scheme, and fuse."""
        
        # 1. Sparse Search (BM25)
        norm_query = Indexer._tokenize(query)
        bm25_scores = self.index.sparse_index.get_scores(norm_query)
        
        # 2. Dense Search (FAISS)
        # If we know the scheme, prepending it to the query helps dense recall slightly, 
        # but often just searching the raw query is fine. We will search raw query.
        q_emb = self.embedder.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
        dense_scores, dense_indices = self.index.vector_index.search(q_emb, self.index.vector_index.ntotal)
        
        # Convert FAISS indices to chunk_ids
        dense_chunk_ids = []
        for idx in dense_indices[0]:
            chunk = self.index.chunks.get(idx)
            if chunk:
                # Apply scheme filter
                if scheme_id and chunk.scheme_id != scheme_id:
                    continue
                dense_chunk_ids.append(chunk.chunk_id)
                
        # Convert BM25 indices to chunk_ids (sorted by score)
        sparse_chunk_ids = []
        sorted_bm25_indices = np.argsort(bm25_scores)[::-1]
        for idx in sorted_bm25_indices:
            if bm25_scores[idx] <= 0:
                continue # Ignore zero scores
            chunk = self.index.chunks.get(idx)
            if chunk:
                # Apply scheme filter
                if scheme_id and chunk.scheme_id != scheme_id:
                    continue
                sparse_chunk_ids.append(chunk.chunk_id)
                
        # 3. Fuse
        fused_ids = self._reciprocal_rank_fusion(dense_chunk_ids, sparse_chunk_ids)
        
        # Map IDs back to Chunks
        id_to_chunk = {c.chunk_id: c for c in self.index.chunks.values()}
        results = [id_to_chunk[cid] for cid in fused_ids[:top_k]]
        
        return results
