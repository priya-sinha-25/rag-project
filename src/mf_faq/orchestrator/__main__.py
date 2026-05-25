import argparse
import sys
import logging
from mf_faq.orchestrator.service import OrchestratorService

logging.basicConfig(level=logging.WARNING)

def main():
    parser = argparse.ArgumentParser(description="Test the Phase 3 Orchestrator")
    parser.add_argument("query", type=str, help="The question to ask")
    args = parser.parse_args()

    print("\n--- Initializing Assistant (loading models...) ---")
    service = OrchestratorService()
    
    print("\n--- Processing ---")
    answer = service.ask(args.query)
    
    print("\n=== Final Response ===")
    print(answer)
    print("======================\n")

if __name__ == "__main__":
    main()
