# Phase 2 Edge Cases: Retrieval Layer

This document outlines the edge cases related to the hybrid retrieval and reranking layer of the Mutual Fund FAQ Assistant.

## Identified Edge Cases

### EC-2.1: Numeric vs Semantic query mismatch
- **Description:** Queries containing exact numbers (e.g., "₹500", "0.45%") might score poorly on dense semantic retrieval but high on sparse BM25, and vice versa for phrased questions.
- **Mitigation:** Weighted Reciprocal Rank Fusion (RRF) is used. The system bumps sparse weight versus dense for numeric-heavy queries to ensure exact facts are retrieved.

### EC-2.2: Scheme alias or acronym mismatch
- **Description:** The user searches for "HDFC Midcap" instead of "HDFC Mid Cap Fund - Direct Growth".
- **Mitigation:** Scheme Resolver uses NER-lite (longest substring match on scheme name + aliases from `sources.yaml`) to correctly filter and scope the retrieval.

### EC-2.3: Low confidence reranking
- **Description:** The cross-encoder reranker returns a top result, but the margin between the top chunk and the second chunk is tiny, indicating uncertainty.
- **Mitigation:** A confidence gate (`τ`) is applied. If confidence is too low, the system falls back to the "I don't know" refusal path rather than guessing.

### EC-2.4: Empty retrieval results for a scheme
- **Description:** The query wording completely misses the vocabulary of the target scheme's chunks.
- **Mitigation:** If the initial scheme-filtered candidate list is empty, the system relaxes the scheme filter once to search the full whitelisted corpus.

### EC-2.5: Wrong-section retrieval
- **Description:** Keywords in the query accidentally pull chunks from irrelevant sections (e.g., querying "load" pulls a chunk mentioning a "load" of assets instead of Exit Load).
- **Mitigation:** An optional section hint applies a light score boost when query keywords match a chunk's explicit `section` metadata (e.g., "exit load" boosts the *Exit Load and Tax* section).
