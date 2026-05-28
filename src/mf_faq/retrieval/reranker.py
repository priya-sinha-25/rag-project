import logging
from typing import List, Tuple
from mf_faq.ingestion.chunker.service import Chunk

logger = logging.getLogger("mf_faq.reranker")

class ReRanker:
    def __init__(self, model_name: str = "none"):
        logger.info("Reranker disabled to save memory on Streamlit Cloud.")

    def rerank(self, query: str, candidates: List[Chunk], top_k: int = 3) -> List[Tuple[Chunk, float]]:
        """Bypass reranking and just return top_k candidates with dummy scores."""
        if not candidates:
            return []
        
        scored_candidates = []
        for i, c in enumerate(candidates[:top_k]):
            scored_candidates.append((c, 1.0 - (i * 0.01)))
            
        return scored_candidates
