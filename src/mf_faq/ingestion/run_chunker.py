import json
import logging
from dataclasses import asdict
from pathlib import Path

from mf_faq.ingestion.extractor import Section
from mf_faq.ingestion.cleaner import CleanedDoc
from mf_faq.ingestion.chunker.service import Chunker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mf_faq.run_chunker")

PROCESSED_DIR = Path("data/processed")

def run():
    chunker = Chunker()
    
    if not PROCESSED_DIR.exists():
        logger.error(f"Processed directory {PROCESSED_DIR} does not exist. Run extractor first.")
        return

    for scheme_dir in PROCESSED_DIR.iterdir():
        if not scheme_dir.is_dir():
            continue

        cleaned_file = scheme_dir / "cleaned.json"
        if not cleaned_file.exists():
            logger.warning(f"No cleaned.json found in {scheme_dir}")
            continue

        logger.info(f"[{scheme_dir.name}] Chunking...")

        with open(cleaned_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Reconstruct CleanedDoc
        sections = [Section(**s) for s in data["sections"]]
        doc = CleanedDoc(
            scheme_id=data["scheme_id"],
            source_url=data["source_url"],
            fetched_at=data["fetched_at"],
            sections=sections,
            must_have_anchors=data["must_have_anchors"],
            extraction_health=data["extraction_health"],
            stable_content_hash=data["stable_content_hash"]
        )

        chunks = chunker.chunk(doc)
        
        chunks_file = scheme_dir / "chunks.jsonl"
        with open(chunks_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
                
        logger.info(f"[{scheme_dir.name}] Created {len(chunks)} chunks.")

if __name__ == "__main__":
    run()
