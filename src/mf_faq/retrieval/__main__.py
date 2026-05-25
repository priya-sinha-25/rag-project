import argparse
import sys
import logging
from mf_faq.retrieval.service import RetrieverService

logging.basicConfig(level=logging.WARNING)
# Enable info specifically for our retrieval logger
logging.getLogger("mf_faq.retrieval").setLevel(logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="Test the Hybrid Retriever")
    parser.add_argument("query", type=str, help="The question to ask")
    args = parser.parse_args()

    print("\n--- Initializing Retriever (loading models...) ---")
    service = RetrieverService()
    
    print("\n--- Searching ---")
    results, scheme = service.search(args.query, top_k=3)
    
    print(f"\n[Resolved Scheme]: {scheme}")
    print("--- Top Results ---")
    for i, (chunk, score) in enumerate(results):
        print(f"\nResult {i+1} (Score: {score:.4f})")
        print(f"Scheme: {chunk.scheme_name}")
        print(f"Section: {chunk.section}")
        print(f"Text: {chunk.text}")
        print("-" * 40)

if __name__ == "__main__":
    main()
