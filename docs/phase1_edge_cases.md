# Phase 1 Edge Cases: Ingestion & Corpus Build

This document outlines the edge cases related to the offline ingestion pipeline and corpus building of the Mutual Fund FAQ Assistant, as defined in the architecture document.

## Identified Edge Cases

### EC-1.1: `robots.txt` blocking the crawler
- **Description:** The Groww `robots.txt` is updated to disallow crawling of the scheme pages before a scheduled run.
- **Mitigation:** The fetcher respects `robots.txt` and aborts the run, triggering a governance alert instead of proceeding.

### EC-1.2: Server returning 304 Not Modified
- **Description:** The target page hasn't changed since the last fetch.
- **Mitigation:** The fetcher sends `If-None-Match` (ETag) and skips downloading/processing on a 304 response, reusing the previous snapshot.

### EC-1.3: Anti-bot triggering (4xx/429)
- **Description:** Rate limiting or anti-bot measures block the fetcher.
- **Mitigation:** The fetcher stops, alerts, and retries on the next scheduled run. It never attempts to bypass anti-bot mechanisms.

### EC-1.4: Missing "must-have" anchors
- **Description:** The Groww page layout changes, and expected sections (e.g., Expense Ratio, Exit Load) cannot be found.
- **Mitigation:** The extractor marks `extraction_health` as degraded. If too many anchors are missing (Soft-404), the page is failed.

### EC-1.5: JavaScript rendering required
- **Description:** Crucial facts are hidden behind JS-rendered accordions or dynamically loaded tables.
- **Mitigation:** The fetcher falls back to a headless renderer (Playwright) using a desktop viewport and auto-expands `[aria-expanded="false"]` elements.

### EC-1.6: Boilerplate text or volatile fields causing drift
- **Description:** Daily changing fields like NAV or AUM, or new boilerplate, cause unnecessary re-indexing.
- **Mitigation:** The cleaner strips these volatile fields from a separate stable view to compute a `stable_content_hash`.

### EC-1.7: Image-only facts missing text
- **Description:** Facts like Riskometer are only available as SVG/images without `alt` text or `aria-label`.
- **Mitigation:** Read sibling captions. If all are absent, mark as not-extracted (no OCR is performed).

### EC-1.8: Near-duplicate boilerplate across schemes
- **Description:** Similar boilerplate across different schemes causes chunks to cluster too closely in the vector space.
- **Mitigation:** The chunker does not include scheme names in the text, but the embedder transiently prepends `scheme_name` before vectorization.

### EC-1.9: Cross-section bleed
- **Description:** Chunker mistakenly spans a single chunk across multiple distinct sections.
- **Mitigation:** Chunker strictly enforces that one chunk corresponds to exactly one section from the cleaned document.

### EC-1.10: Soft-404 detection
- **Description:** The page returns HTTP 200 but lacks the actual mutual fund product content (e.g., a generic error page).
- **Mitigation:** Handled during refresh; if must-have anchors are missing despite a 200 OK, the URL is failed.

### EC-1.11: Embedder mismatch or index failure
- **Description:** The embedding model version changes, breaking compatibility with the index.
- **Mitigation:** Model and version are saved in `embedder.json`. Phase 2 refuses to load mismatched versions. Index builds use an atomic staging swap.

### EC-1.12: Inconsistent number/currency formats
- **Description:** Values appear as Rs.500, Rs. 500, INR 500, or ₹500.
- **Mitigation:** Cleaner enforces NFKC normalization and maps all variations to a standard format (e.g., ₹).
