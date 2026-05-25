import os
import glob
import json
import yaml
import time
import httpx
import hashlib
import logging
from urllib import robotparser
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mf_faq.fetcher")

@dataclass
class FetchResult:
    scheme_id: str
    url: str
    http_status: Optional[int]
    health: str  # 'ok', 'skipped', 'failed', 'blocked'
    fetcher_kind: Optional[str]
    saved_html_path: Optional[str]
    saved_meta_path: Optional[str]

class Fetcher:
    def __init__(self, config_path: str = "config/sources.yaml", data_dir: str = "data/raw"):
        self.config_path = config_path
        self.data_dir = data_dir
        self.user_agent = "MutualFundFaqAssistant/1.0"
        self._load_config()

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.schemes = data.get("schemes", [])

    def _check_robots_txt(self) -> bool:
        """Checks https://groww.in/robots.txt to see if we are allowed to fetch."""
        rp = robotparser.RobotFileParser()
        rp.set_url("https://groww.in/robots.txt")
        try:
            rp.read()
            # Test one of the URLs
            if self.schemes and self.schemes[0].get("sources"):
                test_url = self.schemes[0]["sources"][0]["url"]
                allowed = rp.can_fetch(self.user_agent, test_url)
                if not allowed:
                    logger.error(f"robots.txt explicitly blocks crawling for {test_url}")
                    return False
            return True
        except Exception as e:
            logger.warning(f"Failed to read robots.txt, assuming allowed: {e}")
            return True

    def _get_last_etag(self, scheme_id: str) -> Optional[str]:
        """Gets the ETag from the most recent meta.json for the scheme."""
        scheme_dir = os.path.join(self.data_dir, scheme_id)
        if not os.path.exists(scheme_dir):
            return None
        
        meta_files = sorted(glob.glob(os.path.join(scheme_dir, "*.meta.json")))
        if not meta_files:
            return None
            
        last_meta_file = meta_files[-1]
        try:
            with open(last_meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                return meta.get("etag")
        except Exception:
            return None

    def _needs_playwright_fallback(self, html_content: str) -> bool:
        """Determines if the raw HTML needs JS rendering."""
        # Check if basic mutual fund anchors are missing from raw HTML.
        # Groww might render everything in a <div id="__next"> empty div.
        keywords = ["Expense Ratio", "Exit Load", "AUM"]
        found = sum(1 for kw in keywords if kw.lower() in html_content.lower())
        
        # If we found less than 2 of these keywords or HTML is unusually small, fallback.
        if len(html_content) < 50000 or found < 2:
            return True
        return False

    def _fetch_playwright(self, url: str) -> str:
        """Uses playwright to render JS-heavy pages."""
        from playwright.sync_api import sync_playwright
        logger.info(f"Using playwright fallback for {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()
            # Wait for network to be idle to ensure JS data is loaded
            page.goto(url, wait_until="networkidle")
            
            # Optionally, we can auto-expand accordions here if needed
            # page.evaluate("""() => { document.querySelectorAll('[aria-expanded="false"]').forEach(el => el.click()); }""")
            
            content = page.content()
            browser.close()
            return content

    def _save_snapshot(self, scheme_id: str, html: str, meta: dict) -> tuple[str, str]:
        """Saves the HTML and metadata."""
        scheme_dir = os.path.join(self.data_dir, scheme_id)
        os.makedirs(scheme_dir, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        html_path = os.path.join(scheme_dir, f"{timestamp}.html")
        meta_path = os.path.join(scheme_dir, f"{timestamp}.meta.json")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
        return html_path, meta_path

    def fetch_all(self) -> List[FetchResult]:
        results = []
        
        # 1. Check robots.txt
        if not self._check_robots_txt():
            logger.error("Aborting fetch_all due to robots.txt restrictions.")
            for scheme in self.schemes:
                results.append(FetchResult(scheme["id"], "", None, "blocked", None, None, None))
            return results

        client = httpx.Client(headers={"User-Agent": self.user_agent}, follow_redirects=False)
        
        for scheme in self.schemes:
            scheme_id = scheme["id"]
            url = scheme["sources"][0]["url"]
            last_etag = self._get_last_etag(scheme_id)
            
            headers = {}
            if last_etag:
                headers["If-None-Match"] = last_etag
                
            logger.info(f"Fetching {scheme_id} at {url}")
            try:
                response = client.get(url, headers=headers, timeout=15.0)
                
                # Handle 304 Not Modified
                if response.status_code == 304:
                    logger.info(f"[{scheme_id}] 304 Not Modified. Skipping.")
                    results.append(FetchResult(scheme_id, url, 304, "skipped", None, None, None))
                    continue
                    
                # Handle Redirects (Governance Alert)
                if response.status_code in (301, 302, 307, 308):
                    logger.error(f"[{scheme_id}] Governance Alert: Whitelisted URL redirected ({response.status_code}) to {response.headers.get('location')}. Auto-follow disabled.")
                    results.append(FetchResult(scheme_id, url, response.status_code, "failed", None, None, None))
                    continue
                    
                # Handle Client/Server Errors
                if response.status_code >= 400:
                    logger.error(f"[{scheme_id}] HTTP {response.status_code} Error.")
                    results.append(FetchResult(scheme_id, url, response.status_code, "failed", None, None, None))
                    continue
                
                # Check for Playwright Fallback
                html_content = response.text
                fetcher_kind = "httpx"
                
                if self._needs_playwright_fallback(html_content):
                    html_content = self._fetch_playwright(url)
                    fetcher_kind = "playwright"
                    
                # Calculate hash
                content_hash = "sha256:" + hashlib.sha256(html_content.encode("utf-8")).hexdigest()
                
                # Construct Meta
                meta = {
                    "url": url,
                    "fetched_at": datetime.utcnow().isoformat() + "Z",
                    "http_status": response.status_code,
                    "etag": response.headers.get("etag"),
                    "content_hash_raw": content_hash,
                    "fetcher_kind": fetcher_kind
                }
                
                # Save
                html_path, meta_path = self._save_snapshot(scheme_id, html_content, meta)
                logger.info(f"[{scheme_id}] Successfully saved snapshot ({fetcher_kind}).")
                
                results.append(FetchResult(scheme_id, url, response.status_code, "ok", fetcher_kind, html_path, meta_path))
                
            except Exception as e:
                logger.error(f"[{scheme_id}] Failed to fetch: {e}")
                results.append(FetchResult(scheme_id, url, None, "failed", None, None, None))
                
            # Be nice to the server
            time.sleep(1)

        client.close()
        return results

if __name__ == "__main__":
    fetcher = Fetcher()
    fetcher.fetch_all()
