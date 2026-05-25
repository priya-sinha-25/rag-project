import logging
from mf_faq.ingestion.indexer import Indexer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mf_faq.run_indexer")

def run():
    logger.info("Starting Indexer build...")
    try:
        Indexer.build()
    except Exception as e:
        logger.error(f"Failed to build index: {e}")
        return
        
    logger.info("Verifying IndexHandle loads correctly...")
    try:
        handle = Indexer.load()
        logger.info(f"Successfully loaded IndexHandle.")
        logger.info(f"Vector Index Total: {handle.vector_index.ntotal}")
        logger.info(f"BM25 Corpus Size: {handle.sparse_index.corpus_size}")
        logger.info(f"Chunks Loaded: {len(handle.chunks)}")
        logger.info(f"Manifest: {handle.manifest}")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")

if __name__ == "__main__":
    run()
