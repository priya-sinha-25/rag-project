# Phase 5 Edge Cases: Evaluation, Compliance & Observability

This document outlines the edge cases related to the testing, compliance gating, and operations of the Mutual Fund FAQ Assistant.

## Identified Edge Cases

### EC-5.1: Sudden source drift
- **Description:** A target Groww URL starts 404ing, or its content hash drifts by a massive percentage (e.g., full redesign).
- **Mitigation:** The operational runbook detects this. An alert is triggered if drift > X%, and the pipeline freezes the index rather than ingesting broken data.

### EC-5.2: CI gate URL policy failure
- **Description:** A code change causes the system to start generating outputs with non-whitelisted URLs.
- **Mitigation:** The evaluation harness includes strict compliance gates. The CI build fails immediately if any generated answer cites a URL outside `sources.yaml`.

### EC-5.3: PII leaking into logs
- **Description:** A bug in the PII guard allows sensitive user data to be written to standard out or monitoring systems.
- **Mitigation:** A log-line scanner acts as a secondary defense. Structured logs explicitly hash queries and only store `{request_id, intent, scheme_id, ...}` without raw text.

### EC-5.4: Out-of-corpus query bleeding
- **Description:** A user asks about an obscure non-HDFC scheme, and the retriever accidentally matches generic tokens, returning an incorrect factual answer.
- **Mitigation:** Evaluation harness tests out-of-corpus queries (unknown schemes) to guarantee they always trigger the "I don't have a verified answer" path.

### EC-5.7: Cascading drift across multiple URLs
- **Description:** A site-wide template change at Groww affects ≥ 2 whitelisted URLs simultaneously.
- **Mitigation:** The orchestrator detects multi-URL drift, freezes the index, and raises a single aggregated alert rather than spamming operations.

### EC-5.8: Index build corruption
- **Description:** The weekly re-index job fails midway or produces a corrupted FAISS/BM25 file.
- **Mitigation:** Indexing uses an atomic staging swap (`.staging/`). Readers only see fully-built indexes, preventing downtime or corrupted responses.
