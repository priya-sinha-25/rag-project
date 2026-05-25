import logging
from typing import List, Tuple, Optional

from mf_faq.ingestion.indexer import Indexer
from mf_faq.ingestion.chunker.service import Chunk
from mf_faq.retrieval.resolver import Resolver
from mf_faq.retrieval.hybrid import HybridRetriever
from mf_faq.retrieval.reranker import ReRanker

logger = logging.getLogger("mf_faq.retrieval.service")

class RetrieverService:
    def __init__(self):
        logger.info("Initializing RetrieverService...")
        self.resolver = Resolver()
        
        logger.info("Loading IndexHandle...")
        self.index_handle = Indexer.load()
        
        self.hybrid = HybridRetriever(self.index_handle)
        self.reranker = ReRanker()
        logger.info("RetrieverService ready.")

    def search(self, query: str, top_k: int = 3) -> Tuple[List[Tuple[Chunk, float]], Optional[str]]:
        """
        End-to-end retrieval funnel:
        1. Resolve scheme
        2. Hybrid search (filtered)
        3. Cross-encode rerank
        
        Returns: (List of (Chunk, score), resolved_scheme_id)
        """
        logger.info(f"Query: '{query}'")
        
        # 1. Resolve
        scheme_id = self.resolver.resolve_scheme(query)
        if scheme_id:
            logger.info(f"Resolved scheme constraint: {scheme_id}")
        else:
            logger.info("No scheme resolved. Searching full corpus.")
            
        # 2. Hybrid
        # We retrieve a larger candidate pool for the reranker
        hybrid_candidates = self.hybrid.search(query, scheme_id=scheme_id, top_k=15)
        logger.info(f"Hybrid search returned {len(hybrid_candidates)} candidates.")
        
        # If no scheme was detected and we got 0 candidates (rare), fallback isn't needed.
        # But if we had a scheme and got 0 candidates, the user's wording might have missed.
        if not hybrid_candidates and scheme_id:
            logger.warning("Scheme filtered search returned 0 results. Relaxing constraint...")
            hybrid_candidates = self.hybrid.search(query, scheme_id=None, top_k=15)
            logger.info(f"Relaxed hybrid search returned {len(hybrid_candidates)} candidates.")
            
        # 3. Rerank
        final_results = self.reranker.rerank(query, hybrid_candidates, top_k=top_k)
        logger.info(f"Reranking complete. Top score: {final_results[0][1]:.4f}" if final_results else "No results.")
        
        return final_results, scheme_id
