import unicodedata
import hashlib
import re
import copy
from dataclasses import dataclass, asdict
from typing import List, Dict

from mf_faq.ingestion.extractor import ExtractedDoc, Section

@dataclass
class CleanedDoc:
    scheme_id: str
    source_url: str
    fetched_at: str
    sections: List[Section]
    must_have_anchors: Dict[str, bool]
    extraction_health: str
    stable_content_hash: str

class Cleaner:
    def __init__(self):
        # Boilerplate phrases to remove
        self.boilerplate_patterns = [
            r"Mutual fund investments are subject to market risks.*",
            r"You may also like.*",
            r"Please read all scheme related documents carefully.*"
        ]

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
            
        # NFKC Normalization
        text = unicodedata.normalize("NFKC", text)
        
        # Normalize currency
        text = re.sub(r"(Rs\.|INR)\s*", "₹", text, flags=re.IGNORECASE)
        
        # Strip boilerplate
        for pattern in self.boilerplate_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
            
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        return text

    def clean(self, doc: ExtractedDoc) -> CleanedDoc:
        cleaned_sections = []
        
        for section in doc.sections:
            sec_name = section.name.strip()
            
            # Drop FAQ section completely as per architecture
            if "faq" in sec_name.lower() or "frequently asked questions" in sec_name.lower():
                continue
                
            sec_text = self._normalize_text(section.text)
            
            # Aggressive trimming for Fund House
            if "fund house" in sec_name.lower() or "amc" in sec_name.lower():
                # Strip phone, email, address (they were added in Extractor, but let's strip them here to simulate generic cleaning)
                sec_text = re.sub(r"Address:.*?(?=Email:|Phone:|$)", "", sec_text, flags=re.IGNORECASE | re.DOTALL)
                sec_text = re.sub(r"Email:.*?(?=Phone:|$)", "", sec_text, flags=re.IGNORECASE | re.DOTALL)
                sec_text = re.sub(r"Phone:.*", "", sec_text, flags=re.IGNORECASE | re.DOTALL)
                sec_text = self._normalize_text(sec_text)
                
            # Aggressive trimming for Fund Manager
            if "fund manager" in sec_name.lower() or "manager" in sec_name.lower():
                # Keep only name and tenure (Extractor already mostly did this, but ensure experience/bio is stripped)
                sec_text = re.sub(r"Experience:.*", "", sec_text, flags=re.IGNORECASE | re.DOTALL)
                sec_text = self._normalize_text(sec_text)

            # Drop overview if it's too massive and overlaps (we just keep it for now but clean it)
            if sec_text:
                cleaned_sections.append(Section(name=sec_name, text=sec_text))
                
        # Generate Stable Hash
        # Strip volatile fields: NAV, AUM, As On dates
        stable_text_parts = []
        for sec in cleaned_sections:
            if "aum" in sec.name.lower():
                continue # Skip AUM completely for hash
            stable_text = re.sub(r"as on \d{1,2} [A-Za-z]+ \d{4}", "", sec.text, flags=re.IGNORECASE)
            stable_text = re.sub(r"NAV: ₹\d+(\.\d+)?", "", stable_text, flags=re.IGNORECASE)
            stable_text_parts.append(stable_text)
            
        combined_stable_text = " | ".join(stable_text_parts)
        stable_hash = "sha256:" + hashlib.sha256(combined_stable_text.encode("utf-8")).hexdigest()

        return CleanedDoc(
            scheme_id=doc.scheme_id,
            source_url=doc.source_url,
            fetched_at=doc.fetched_at,
            sections=cleaned_sections,
            must_have_anchors=doc.must_have_anchors,
            extraction_health=doc.extraction_health,
            stable_content_hash=stable_hash
        )
