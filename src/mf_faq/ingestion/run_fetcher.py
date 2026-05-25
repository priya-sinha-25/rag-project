import logging
from mf_faq.ingestion.fetcher import Fetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    print("Starting Mutual Fund FAQ Phase 1.1 Fetcher...")
    fetcher = Fetcher()
    
    results = fetcher.fetch_all()
    
    print("\n--- Fetch Summary ---")
    all_ok = True
    for res in results:
        status = res.health.upper()
        print(f"[{res.scheme_id}] Health: {status} | HTTP: {res.http_status} | Fetcher: {res.fetcher_kind}")
        if status not in ["OK", "SKIPPED"]:
            all_ok = False
            
    if all_ok:
        print("\nAll whitelisted URLs processed successfully (OK or SKIPPED).")
    else:
        print("\nSome fetches failed or were blocked. Check logs for details.")

if __name__ == "__main__":
    main()
