# Phase 0 Edge Cases: Foundation & Governance

This document outlines the edge cases related to the foundation and governance phase of the Mutual Fund FAQ Assistant.

## Identified Edge Cases

### EC-0.1: Unrecognized AMC or missing scheme details
- **Description:** A query or system initialization attempts to load an AMC or scheme not explicitly defined in the whitelisted `sources.yaml`.
- **Mitigation:** The system strictly adheres to the 5 locked schemes. Any unrecognized scheme triggers an immediate out-of-scope refusal or initialization error.

### EC-0.2: Malformed or non-matching URLs
- **Description:** The URLs provided in the configuration do not exactly match the string-equal expected Groww URLs.
- **Mitigation:** Strict validation against `sources.yaml` ensuring 1:1 match. The CI pipeline fails if URLs are incorrect.

### EC-0.3: Ambiguous refusal intents
- **Description:** A user query sits on the boundary between factual and advisory (e.g., "Is this a good expense ratio?").
- **Mitigation:** The `refusal_intents.yaml` defines strict boundary conditions. When in doubt, the system defaults to refusal and provides the educational link.

### EC-0.4: Policy Updates
- **Description:** Need to handle changes in the required disclaimer or PII definitions.
- **Mitigation:** Maintain `disclaimer.txt` and PII regex sets as easily updateable configurations that block deployment if malformed.
