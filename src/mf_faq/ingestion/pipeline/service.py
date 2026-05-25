import logging
import json
import time
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timezone

from mf_faq.ingestion.fetcher import Fetcher
from mf_faq.ingestion.extractor import Extractor
from mf_faq.ingestion.cleaner import Cleaner
from mf_faq.ingestion.chunker.service import Chunker
from mf_faq.ingestion.embedder import Embedder
from mf_faq.ingestion.indexer import Indexer

logger = logging.getLogger("mf_faq.pipeline")

class Pipeline:
    def __init__(self):
        self.INDEX_DIR = Path("data/index")
        self.PROCESSED_DIR = Path("data/processed")
        self.LOG_FILE = self.INDEX_DIR / "refresh_log.jsonl"
        
    def _load_old_hashes(self) -> dict:
        old_hashes = {}
        chunks_file = self.INDEX_DIR / "chunks.jsonl"
        if chunks_file.exists():
            with open(chunks_file, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    scheme_id = data["scheme_id"]
                    if scheme_id not in old_hashes:
                        old_hashes[scheme_id] = data["stable_content_hash"]
        return old_hashes

    def refresh(self, force: bool = False, skip_fetch: bool = False) -> str:
        start_time = time.time()
        self.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        # 1. Fetch
        if not skip_fetch:
            fetcher = Fetcher()
            fetch_results = fetcher.fetch_all()
            # If any fetcher failed due to 4xx/429 (not just unchanged), handle it.
            # For simplicity, we assume fetcher handled it and wrote files.
            
        # 2. Extract & Clean to check hashes
        extractor = Extractor()
        cleaner = Cleaner()
        
        raw_dir = Path("data/raw")
        if not raw_dir.exists():
            logger.error("No raw data found.")
            return "failed"
            
        cleaned_docs = {}
        new_hashes = {}
        
        for scheme_dir in raw_dir.iterdir():
            if not scheme_dir.is_dir():
                continue
                
            scheme_id = scheme_dir.name
            html_files = sorted(scheme_dir.glob("*.html"), reverse=True)
            json_files = sorted(scheme_dir.glob("*.json"), reverse=True)
            
            if not html_files or not json_files:
                continue
                
            with open(html_files[0], "r", encoding="utf-8") as f:
                html_content = f.read()
            with open(json_files[0], "r", encoding="utf-8") as f:
                meta = json.load(f)
                
            extracted = extractor.extract(html_content, scheme_id, meta.get("url", ""), meta.get("fetched_at", ""))
            cleaned = cleaner.clean(extracted)
            
            cleaned_docs[scheme_id] = cleaned
            new_hashes[scheme_id] = cleaned.stable_content_hash
            
            # Save cleaned (optional, but good for debug)
            proc_dir = self.PROCESSED_DIR / scheme_id
            proc_dir.mkdir(parents=True, exist_ok=True)
            with open(proc_dir / "cleaned.json", "w", encoding="utf-8") as f:
                json.dump(asdict(cleaned), f, indent=2, ensure_ascii=False)

        # 3. Drift Detection
        old_hashes = self._load_old_hashes()
        drift_count = 0
        for scheme_id, new_hash in new_hashes.items():
            old_hash = old_hashes.get(scheme_id)
            if old_hash and old_hash != new_hash:
                drift_count += 1
                logger.info(f"[{scheme_id}] Hash drifted: {old_hash[:8]} -> {new_hash[:8]}")
                
        if drift_count >= 2 and not force:
            logger.warning(f"Drift count {drift_count} >= 2. Freezing index to prevent massive corruption.")
            self._log_run("frozen", time.time() - start_time, drift_count)
            return "frozen"
            
        # 4. Chunk & Embed
        chunker = Chunker()
        all_chunks = []
        
        for scheme_id, doc in cleaned_docs.items():
            chunks = chunker.chunk(doc)
            all_chunks.extend(chunks)
            # Save chunks
            proc_dir = self.PROCESSED_DIR / scheme_id
            with open(proc_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
                for c in chunks:
                    f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
                    
        try:
            embedder = Embedder()
        except ImportError as e:
            logger.error(f"Embedder failed to load: {e}")
            return "failed"
            
        batch = embedder.embed(all_chunks)
        
        import numpy as np
        np.save(self.INDEX_DIR / "embeddings.npy", batch.embeddings)
        with open(self.INDEX_DIR / "chunks.jsonl", "w", encoding="utf-8") as f:
            for c in batch.chunks:
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
                
        with open(self.INDEX_DIR / "embedder.json", "w", encoding="utf-8") as f:
            json.dump({"model": batch.model_name, "dim": batch.dim, "n_chunks": len(batch.chunks)}, f, indent=2)

        # 5. Index
        Indexer.build()
        
        duration = time.time() - start_time
        self._log_run("ok", duration, drift_count)
        return "ok"
        
    def _log_run(self, outcome: str, duration: float, drift_count: int):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
            "duration_sec": round(duration, 2),
            "drift_count": drift_count
        }
        with open(self.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info(f"Pipeline completed with outcome: {outcome}")
