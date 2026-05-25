import sys
from mf_faq.retrieval.service import RetrieverService

retriever = RetrieverService()
candidates, scheme_id = retriever.search("What is the NAV of HDFC Equity?", top_k=5)

print(f"Scheme ID: {scheme_id}")
for chunk, score in candidates:
    print(f"\n--- Score: {score:.3f} ---")
    print(f"Text: {chunk.text}")
