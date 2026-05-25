import argparse
import logging
import sys

from mf_faq.ingestion.pipeline.service import Pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Refresh Ingestion Pipeline")
    parser.add_argument("--force", action="store_true", help="Force refresh even if drift limit is exceeded")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip the HTTP fetching phase and use existing raw snapshots")
    
    args = parser.parse_args()
    
    pipeline = Pipeline()
    outcome = pipeline.refresh(force=args.force, skip_fetch=args.skip_fetch)
    
    if outcome == "failed":
        sys.exit(1)
    elif outcome == "frozen":
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
