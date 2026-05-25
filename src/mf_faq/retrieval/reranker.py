import logging
from typing import List, Tuple
from mf_faq.ingestion.chunker.service import Chunk

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

logger = logging.getLogger("mf_faq.reranker")

class ReRanker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        if CrossEncoder is None:
            raise ImportError("sentence-transformers is not installed.")
        logger.info(f"Loading cross-encoder: {model_name}")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[Chunk], top_k: int = 3) -> List[Tuple[Chunk, float]]:
        """Scores candidate chunks against the query and returns the top_k."""
        if not candidates:
            return []
            
        # Format the pairs for the cross-encoder: (query, text)
        pairs = []
        for c in candidates:
            # We provide the cross encoder with the exact same text that was embedded,
            # which includes the scheme name as context.
            context_text = f"{c.scheme_name}\n\n{c.text}"
            pairs.append([query, context_text])
            
        scores = self.model.predict(pairs)
        
        # Zip chunks with scores and sort descending
        scored_candidates = list(zip(candidates, scores))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return scored_candidates[:top_k]
