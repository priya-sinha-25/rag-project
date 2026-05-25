# Phase 3 Edge Cases: Reasoning & Guardrails

This document outlines the edge cases related to the orchestrator, guardrails, and generation layer of the Mutual Fund FAQ Assistant.

## Identified Edge Cases

### EC-3.1: PII detected in query
- **Description:** The user accidentally pastes their PAN, Aadhaar, email, or account number into the query.
- **Mitigation:** A hard PII guard rejects the input *before* retrieval. No URLs are returned, and a locked `pii_block` template is used. The query is not logged.

### EC-3.2: Advisory, Comparison, or Prediction queries
- **Description:** The user asks non-factual questions like "Should I invest in this?" or "Which is better, Equity or Mid Cap?"
- **Mitigation:** Intent classifier routes to the Refusal Composer. The system returns a polite refusal with *at most one* URL (the matching Groww scheme URL, or a default).

### EC-3.3: Empty or failed LLM generation
- **Description:** The optional Groq LLM API fails, times out, or returns an empty body.
- **Mitigation:** The system safely falls back to the extractive generator, building the answer directly from the top reranked chunk.

### EC-3.4: Overly verbose generation
- **Description:** The LLM generator produces a response exceeding the strict length cap.
- **Mitigation:** Post-processor enforces a hard cap of ≤ 3 sentences for the factual body before appending the citation footer.

### EC-3.5: Non-whitelisted or excessive URLs
- **Description:** The generator hallucinates a SEBI/AMFI URL, or includes multiple URLs in the text.
- **Mitigation:** Post-processor strips embedded URLs and verifies that *exactly one* URL is present, and it strictly matches `sources.yaml`. If violated, it falls back to a safe template.

### EC-3.6: Generation of banned advisory tokens
- **Description:** Even on a factual query, the LLM hallucinates words like "recommend", "should invest", or "will outperform".
- **Mitigation:** The post-processor runs a strict token scanner over the draft output. If banned tokens are found, it blocks the response and uses the safe fallback template.
