import re
import yaml
from typing import Optional, Tuple

class PIIGuard:
    # Basic Indian context PII regexes
    PAN_REGEX = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', re.IGNORECASE)
    AADHAAR_REGEX = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')
    EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    PHONE_REGEX = re.compile(r'\b(?:\+?91|0)?[6-9]\d{9}\b')

    @classmethod
    def check(cls, text: str) -> bool:
        """Returns True if PII is detected, False otherwise."""
        if cls.PAN_REGEX.search(text): return True
        if cls.AADHAAR_REGEX.search(text): return True
        if cls.EMAIL_REGEX.search(text): return True
        if cls.PHONE_REGEX.search(text): return True
        return False

class IntentClassifier:
    def __init__(self, intents_path: str = "config/refusal_intents.yaml"):
        self.intents = []
        try:
            with open(intents_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.intents = data.get("refusal_intents", [])
        except Exception:
            pass

    def classify(self, query: str) -> Optional[dict]:
        """Returns the intent dict if a refusal pattern matches, None if factual."""
        q_lower = query.lower()
        for intent in self.intents:
            for pattern in intent.get("patterns", []):
                if pattern in q_lower:
                    return intent
        return None

class RefusalComposer:
    def __init__(self, sources_path: str = "config/sources.yaml"):
        self.scheme_urls = {}
        self.default_url = ""
        try:
            with open(sources_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                for i, scheme in enumerate(data.get("schemes", [])):
                    url = scheme["sources"][0]["url"]
                    self.scheme_urls[scheme["id"]] = url
                    if i == 0:
                        self.default_url = url
        except Exception:
            pass

    def compose(self, intent_dict: dict, scheme_id: Optional[str]) -> str:
        """Composes the refusal string with exactly one educational URL."""
        canned = intent_dict.get("canned_copy", "I cannot answer this. See: {educational_link}")
        link = self.scheme_urls.get(scheme_id, self.default_url)
        return canned.replace("{educational_link}", link)
