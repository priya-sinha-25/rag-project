import re
import yaml

class PostProcessor:
    def __init__(self, sources_path: str = "config/sources.yaml"):
        self.whitelist = set()
        try:
            with open(sources_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                for scheme in data.get("schemes", []):
                    self.whitelist.add(scheme["sources"][0]["url"])
        except Exception:
            pass

        # Simple list of banned tokens
        self.banned_tokens = [
            "recommend", "should invest", "better than", 
            "will outperform", "guaranteed", "advice"
        ]

    def _count_urls(self, text: str) -> int:
        return len(re.findall(r'https?://\S+', text))

    def _contains_banned_tokens(self, text: str) -> bool:
        t_lower = text.lower()
        for token in self.banned_tokens:
            if token in t_lower:
                return True
        return False

    def process(self, draft: str, state: str, source_url: str = None, last_updated: str = None) -> str:
        """
        Enforces the Non-Negotiable URL Policy and final formatting.
        state can be: 'pii', 'dont_know', 'refusal', 'factual'
        """
        
        # 1. PII and Don't Know must have 0 URLs
        if state in ['pii', 'dont_know']:
            if self._count_urls(draft) > 0:
                return "Security Error: URL leaked in protected state."
            return draft
            
        # 2. Refusal must have exactly 1 URL
        if state == 'refusal':
            if self._count_urls(draft) != 1:
                return "I cannot provide an answer. Please refer to official Groww sources."
            # No footer needed for refusals
            return draft
            
        # 3. Factual must pass strict checks
        if state == 'factual':
            # Check banned tokens
            if self._contains_banned_tokens(draft):
                return "I cannot provide an answer. Please refer to official Groww sources."
                
            # Draft currently has 0 URLs because ExtractiveGenerator stripped them.
            # We append the footer.
            footer = f"\n\nSource: {source_url}\nLast updated from sources: {last_updated}"
            final_text = draft + footer
            
            # Re-verify URL count = 1
            if self._count_urls(final_text) != 1:
                return "System Error: URL policy violation detected."
                
            # Verify URL is in whitelist
            if source_url not in self.whitelist:
                return "System Error: Citation URL not in whitelist."
                
            return final_text
            
        return "Unknown state error."
