import json
import logging
import os
from pathlib import Path
from dataclasses import asdict
import numpy as np

from mf_faq.ingestion.chunker.service import Chunk
from mf_faq.ingestion.embedder import Embedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mf_faq.run_embedder")

PROCESSED_DIR = Path("data/processed")
INDEX_DIR = Path("data/index")

def run():
    if not PROCESSED_DIR.exists():
        logger.error(f"Processed directory {PROCESSED_DIR} does not exist. Run chunker first.")
        return

    all_chunks = []
    for scheme_dir in PROCESSED_DIR.iterdir():
        if not scheme_dir.is_dir():
            continue

        chunks_file = scheme_dir / "chunks.jsonl"
        if not chunks_file.exists():
            continue

        with open(chunks_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                all_chunks.append(Chunk(**data))

    if not all_chunks:
        logger.error("No chunks found to embed.")
        return

    logger.info(f"Loaded {len(all_chunks)} chunks across the corpus.")

    # Initialize Embedder
    try:
        embedder = Embedder()
    except ImportError as e:
        logger.error(f"Failed to initialize Embedder: {e}")
        return

    # Generate Embeddings
    batch = embedder.embed(all_chunks)
    
    # Setup index dir
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Save embeddings.npy
    npy_path = INDEX_DIR / "embeddings.npy"
    np.save(npy_path, batch.embeddings)
    logger.info(f"Saved embeddings to {npy_path} with shape {batch.embeddings.shape}")

    # 2. Save chunks.jsonl
    chunks_path = INDEX_DIR / "chunks.jsonl"
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in batch.chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(batch.chunks)} chunks to {chunks_path}")

    # 3. Save embedder.json
    manifest_path = INDEX_DIR / "embedder.json"
    manifest_data = {
        "model": batch.model_name,
        "dim": batch.dim,
        "n_chunks": len(batch.chunks)
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info(f"Saved embedder manifest to {manifest_path}")

if __name__ == "__main__":
    run()
