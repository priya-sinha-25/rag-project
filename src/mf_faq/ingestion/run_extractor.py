import os
import json
import logging
from dataclasses import asdict
from pathlib import Path

from mf_faq.ingestion.extractor import Extractor
from mf_faq.ingestion.cleaner import Cleaner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mf_faq.run_extractor")

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

def run():
    extractor = Extractor()
    cleaner = Cleaner()

    if not RAW_DIR.exists():
        logger.error(f"Raw directory {RAW_DIR} does not exist. Run fetcher first.")
        return

    for scheme_dir in RAW_DIR.iterdir():
        if not scheme_dir.is_dir():
            continue

        scheme_id = scheme_dir.name
        
        # Find the latest HTML file
        html_files = sorted(scheme_dir.glob("*.html"), reverse=True)
        json_files = sorted(scheme_dir.glob("*.json"), reverse=True)
        
        if not html_files or not json_files:
            logger.warning(f"No valid snapshot found in {scheme_dir}")
            continue

        latest_html = html_files[0]
        latest_json = json_files[0]

        logger.info(f"[{scheme_id}] Processing {latest_html.name}")

        with open(latest_html, "r", encoding="utf-8") as f:
            html_content = f.read()

        with open(latest_json, "r", encoding="utf-8") as f:
            meta = json.load(f)

        url = meta.get("url", "")
        fetched_at = meta.get("fetched_at", "")

        # 1. Extract
        extracted_doc = extractor.extract(html_content, scheme_id, url, fetched_at)
        
        # Ensure processed dir exists
        scheme_proc_dir = PROCESSED_DIR / scheme_id
        scheme_proc_dir.mkdir(parents=True, exist_ok=True)

        with open(scheme_proc_dir / "extracted.json", "w", encoding="utf-8") as f:
            json.dump(asdict(extracted_doc), f, indent=2, ensure_ascii=False)
            
        logger.info(f"[{scheme_id}] Extraction health: {extracted_doc.extraction_health}")

        # 2. Clean
        cleaned_doc = cleaner.clean(extracted_doc)

        with open(scheme_proc_dir / "cleaned.json", "w", encoding="utf-8") as f:
            json.dump(asdict(cleaned_doc), f, indent=2, ensure_ascii=False)
            
        logger.info(f"[{scheme_id}] Cleaned successfully. Stable Hash: {cleaned_doc.stable_content_hash[:8]}...")

if __name__ == "__main__":
    run()
