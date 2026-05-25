import uuid
import yaml
import tiktoken
import logging
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path

from mf_faq.ingestion.cleaner import CleanedDoc

logger = logging.getLogger("mf_faq.chunker")

@dataclass
class Chunk:
    chunk_id: str
    scheme_id: str
    scheme_name: str
    doc_type: str
    source_url: str
    section: str
    section_source: str
    last_updated: str
    content_hash: str
    stable_content_hash: str
    text: str

class Chunker:
    def __init__(self, sources_yaml_path: str = "config/sources.yaml"):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.scheme_meta = self._load_sources(sources_yaml_path)
        self.SOFT_CAP = 300
        
    def _load_sources(self, path: str) -> Dict[str, dict]:
        meta = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                for scheme in data.get("schemes", []):
                    # We assume 1 source per scheme as per phase 0
                    source_info = scheme["sources"][0]
                    meta[scheme["id"]] = {
                        "scheme_name": scheme["name"],
                        "doc_type": source_info["doc_type"]
                    }
        except Exception as e:
            logger.error(f"Failed to load sources.yaml: {e}")
        return meta

    def chunk(self, doc: CleanedDoc) -> List[Chunk]:
        chunks = []
        meta = self.scheme_meta.get(doc.scheme_id, {"scheme_name": doc.scheme_id, "doc_type": "Product_Page"})
        
        for section in doc.sections:
            tokens = self.encoder.encode(section.text)
            
            if len(tokens) < 5:
                continue
                
            if section.name != "Overview":
                # Emit as a single chunk
                chunks.append(self._create_chunk(doc, section.name, section.text, meta))
            else:
                # Tabular / Pipe-aware chunking for Overview
                cells = section.text.split("|")
                current_cells = []
                current_tokens = 0
                
                for i, cell in enumerate(cells):
                    # Add | back unless it's the very last element and was empty
                    cell_text = cell + "|" if i < len(cells) - 1 else cell
                    if not cell_text.strip():
                        continue
                        
                    cell_toks = len(self.encoder.encode(cell_text))
                    current_cells.append(cell_text)
                    current_tokens += cell_toks
                    
                    if current_tokens >= self.SOFT_CAP:
                        chunk_text = "".join(current_cells).strip()
                        chunks.append(self._create_chunk(doc, section.name, chunk_text, meta))
                        
                        # Overlap: keep last ~8 cells (roughly 2-3 logical rows of dense data)
                        overlap_cells = current_cells[-8:] if len(current_cells) > 8 else current_cells[-2:]
                        current_cells = overlap_cells
                        current_tokens = sum(len(self.encoder.encode(c)) for c in current_cells)
                        
                # Flush remaining
                if current_cells:
                    chunk_text = "".join(current_cells).strip()
                    # Only emit if it's meaningful (not just overlap leftovers)
                    if len(self.encoder.encode(chunk_text)) >= 10:
                        chunks.append(self._create_chunk(doc, section.name, chunk_text, meta))
                        
        return chunks
        
    def _create_chunk(self, doc: CleanedDoc, section_name: str, text: str, meta: dict) -> Chunk:
        # Generate stable chunk hash
        import hashlib
        c_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            scheme_id=doc.scheme_id,
            scheme_name=meta["scheme_name"],
            doc_type=meta["doc_type"],
            source_url=doc.source_url,
            section=section_name,
            section_source="html_section",
            last_updated=doc.fetched_at[:10], # YYYY-MM-DD
            content_hash=f"sha256:{c_hash}",
            stable_content_hash=doc.stable_content_hash,
            text=text
        )
