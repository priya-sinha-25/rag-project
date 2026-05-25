import string
import yaml
import re
from typing import Optional

class Resolver:
    def __init__(self, sources_yaml_path: str = "config/sources.yaml"):
        self.schemes = self._load_schemes(sources_yaml_path)
        
    def _load_schemes(self, path: str) -> dict:
        schemes = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                for scheme in data.get("schemes", []):
                    # We store both the ID and the normalized Name as aliases
                    aliases = [
                        scheme["id"].replace("_", " "),
                        scheme["name"].lower()
                    ]
                    # Generate some simple sub-aliases like "mid cap", "equity fund"
                    if "Mid Cap" in scheme["name"]:
                        aliases.append("mid cap")
                    if "Flexi Cap" in scheme["category"]:
                        aliases.append("equity fund")
                        aliases.append("flexi cap")
                    if "Focused" in scheme["name"]:
                        aliases.append("focused")
                    if "ELSS" in scheme["name"]:
                        aliases.append("elss")
                        aliases.append("tax saver")
                    if "Large Cap" in scheme["name"]:
                        aliases.append("large cap")
                        
                    # Clean aliases
                    cleaned_aliases = []
                    for alias in aliases:
                        cleaned = self.normalize(alias)
                        cleaned_aliases.append(cleaned)
                        
                    schemes[scheme["id"]] = sorted(list(set(cleaned_aliases)), key=len, reverse=True)
        except Exception as e:
            pass
        return schemes

    def normalize(self, text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def resolve_scheme(self, query: str) -> Optional[str]:
        """Returns scheme_id if a strong match is found in the query."""
        norm_query = self.normalize(query)
        
        # Simple substring matching. Longest aliases first.
        # This works well for a closed corpus of 5 disparate schemes.
        for scheme_id, aliases in self.schemes.items():
            for alias in aliases:
                # Require word boundaries for short aliases to avoid accidental matches
                if len(alias) <= 5:
                    if re.search(rf'\b{re.escape(alias)}\b', norm_query):
                        return scheme_id
                else:
                    if alias in norm_query:
                        return scheme_id
        return None
