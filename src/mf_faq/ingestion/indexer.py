import json
import logging
import pickle
import string
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

from mf_faq.ingestion.chunker.service import Chunk

logger = logging.getLogger("mf_faq.indexer")

@dataclass
class IndexHandle:
    vector_index: Any  # faiss.Index
    sparse_index: Any  # BM25Okapi
    chunks: Dict[int, Chunk]
    manifest: Dict[str, Any]

class Indexer:
    INDEX_DIR = Path("data/index")
    
    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        # Simple lowercase and punctuation strip tokenization for BM25
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        return text.split()

    @classmethod
    def build(cls) -> None:
        if faiss is None or BM25Okapi is None:
            raise ImportError("faiss-cpu and rank_bm25 are required.")
            
        cls.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        embeddings_path = cls.INDEX_DIR / "embeddings.npy"
        chunks_path = cls.INDEX_DIR / "chunks.jsonl"
        manifest_path = cls.INDEX_DIR / "embedder.json"
        
        if not (embeddings_path.exists() and chunks_path.exists() and manifest_path.exists()):
            raise FileNotFoundError("Run embedder first. Missing required index files.")
            
        logger.info("Loading inputs...")
        embeddings = np.load(embeddings_path)
        
        chunks = []
        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                chunks.append(Chunk(**json.loads(line)))
                
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Chunk count {len(chunks)} does not match embeddings shape {embeddings.shape[0]}")
            
        # 1. Build Dense Index (FAISS)
        logger.info(f"Building FAISS IndexFlatIP (dim={embeddings.shape[1]})...")
        # IndexFlatIP uses Inner Product, which is equivalent to Cosine Similarity when vectors are normalized
        vector_index = faiss.IndexFlatIP(embeddings.shape[1])
        vector_index.add(embeddings)
        
        faiss_path = cls.INDEX_DIR / "vector.faiss"
        faiss.write_index(vector_index, str(faiss_path))
        logger.info(f"Saved FAISS index to {faiss_path}")
        
        # 2. Build Sparse Index (BM25)
        logger.info("Building BM25 Sparse Index...")
        tokenized_corpus = [cls._tokenize(chunk.text) for chunk in chunks]
        bm25_index = BM25Okapi(tokenized_corpus)
        
        bm25_path = cls.INDEX_DIR / "bm25.pkl"
        with open(bm25_path, "wb") as f:
            pickle.dump(bm25_index, f)
        logger.info(f"Saved BM25 index to {bm25_path}")
        
        # 3. Update Manifest
        from datetime import datetime, timezone
        
        # Compute per-scheme chunk counts
        per_scheme_counts = {}
        for chunk in chunks:
            per_scheme_counts[chunk.scheme_id] = per_scheme_counts.get(chunk.scheme_id, 0) + 1
            
        manifest.update({
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_chunks": len(chunks),
            "per_scheme_counts": per_scheme_counts
        })
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info("Updated manifest.json (embedder.json)")
        logger.info("Index build complete!")

    @classmethod
    def load(cls) -> IndexHandle:
        if faiss is None or BM25Okapi is None:
            raise ImportError("faiss-cpu and rank_bm25 are required.")
            
        faiss_path = cls.INDEX_DIR / "vector.faiss"
        bm25_path = cls.INDEX_DIR / "bm25.pkl"
        chunks_path = cls.INDEX_DIR / "chunks.jsonl"
        manifest_path = cls.INDEX_DIR / "embedder.json"
        
        logger.info("Loading FAISS index...")
        vector_index = faiss.read_index(str(faiss_path))
        
        logger.info("Loading BM25 index...")
        with open(bm25_path, "rb") as f:
            sparse_index = pickle.load(f)
            
        logger.info("Loading chunks...")
        chunks_dict = {}
        with open(chunks_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                chunks_dict[i] = Chunk(**json.loads(line))
                
        logger.info("Loading manifest...")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        return IndexHandle(
            vector_index=vector_index,
            sparse_index=sparse_index,
            chunks=chunks_dict,
            manifest=manifest
        )
