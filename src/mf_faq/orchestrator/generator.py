import re
from mf_faq.ingestion.chunker.service import Chunk

class ExtractiveGenerator:
    @classmethod
    def generate(cls, chunk: Chunk) -> str:
        """Extracts the first <= 3 sentences from the chunk and strips URLs."""
        text = chunk.text
        
        # 1. Strip URLs embedded in the chunk text to prevent link leakage
        url_pattern = re.compile(r'https?://\S+')
        text = url_pattern.sub('', text).strip()
        
        # 2. Extract <= 3 sentences. 
        # A simple split on period-space. This is a heuristic.
        # Tabular data usually doesn't have periods, so it will just be 1 "sentence".
        sentences = [s.strip() for s in text.split('. ') if s.strip()]
        
        if not sentences:
            return text
            
        selected = sentences[:3]
        
        # Re-join
        body = ". ".join(selected)
        # Ensure it ends with punctuation if it was split
        if not body.endswith('.') and not body.endswith('|'):
            if len(sentences) > 3:
                body += "..."
            else:
                body += "."
                
        return body
