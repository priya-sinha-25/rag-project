import os
from groq import Groq
from mf_faq.ingestion.chunker.service import Chunk

class GroqGenerator:
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.api_key)
        self.model_name = model_name
        self.system_prompt = """You are a strict, factual assistant for Groww mutual funds.
Your ONLY job is to take the provided verified FACT and rewrite it into a conversational answer.

RULES:
1. Base your answer EXCLUSIVELY on the provided fact. Do not add outside knowledge.
2. Keep the answer strictly UNDER 3 sentences.
3. DO NOT include any URLs or links in your response.
4. Output raw text only. No markdown, no bolding.
5. If the fact contains tabular data (pipe-separated), summarize it naturally in a sentence.
6. CRITICAL: If the provided fact does NOT contain the information needed to answer the user's query, you MUST output exactly this exact phrase, word for word, and nothing else:
I don't have a verified answer for that. Please ask about scheme details, exit loads, or AUM."""

    def generate(self, query: str, chunk: Chunk) -> str:
        """Calls Groq to generate a conversational answer from the chunk."""
        
        # Prepare the context
        context = f"Verified Fact Context:\n{chunk.scheme_name}\nSection: {chunk.section}\nContent: {chunk.text}"
        
        user_prompt = f"{context}\n\nUser Query: {query}\n\nAnswer:"
        
        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=self.model_name,
            temperature=0.0, # Zero temperature for max determinism
            max_tokens=150
        )
        
        return chat_completion.choices[0].message.content.strip()
