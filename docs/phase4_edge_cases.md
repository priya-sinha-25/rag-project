# Phase 4 Edge Cases: User Interface

This document outlines the edge cases related to the minimal web application UI for the Mutual Fund FAQ Assistant.

## Identified Edge Cases

### EC-4.1: Concurrent or rapid-fire submissions
- **Description:** The user clicks the submit button multiple times before the first query returns.
- **Mitigation:** The UI disables the submit button and input field while a query is in-flight.

### EC-4.2: Extremely long queries
- **Description:** The user pastes a massive block of text into the input field.
- **Mitigation:** The UI enforces a reasonable maximum character limit on the input field, and the FastAPI backend rejects oversized payloads.

### EC-4.3: Missing disclaimer visibility
- **Description:** On small mobile screens, the required financial disclaimer gets pushed out of the viewport.
- **Mitigation:** CSS layout ensures the disclaimer ("Facts-only. No investment advice.") is always visible, potentially fixed to the layout or highly prominent.

### EC-4.4: Clickjacking or uncontrolled link sharing
- **Description:** Malicious actors attempt to iframe the UI or share misleading pre-filled queries.
- **Mitigation:** Links are rendered with `rel="noopener nofollow"`. "Share" functionality is deliberately omitted to discourage misuse. Strict framing headers (X-Frame-Options) are applied by FastAPI.
