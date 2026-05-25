import json
import logging
from typing import List, Dict
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import trafilatura

logger = logging.getLogger("mf_faq.extractor")

@dataclass
class Section:
    name: str
    text: str

@dataclass
class ExtractedDoc:
    scheme_id: str
    source_url: str
    fetched_at: str
    sections: List[Section]
    must_have_anchors: Dict[str, bool]
    extraction_health: str

class Extractor:
    def __init__(self):
        self.must_have_keys = ["Expense Ratio", "Exit Load", "AUM", "NAV", "Scheme Details"]

    def extract(self, html: str, scheme_id: str, url: str, fetched_at: str) -> ExtractedDoc:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Try to extract structured data from Next.js props if available
        next_data = soup.find("script", id="__NEXT_DATA__")
        mf_data = {}
        if next_data and next_data.string:
            try:
                data = json.loads(next_data.string)
                mf_data = data.get("props", {}).get("pageProps", {}).get("mfServerSideData", {})
            except Exception as e:
                logger.warning(f"[{scheme_id}] Failed to parse __NEXT_DATA__: {e}")

        sections = []
        
        # We will build sections based on structured data and fallback to trafilatura text
        
        # --- Scheme Details ---
        scheme_details_text = ""
        if mf_data:
            scheme_details_text += f"Scheme Name: {mf_data.get('scheme_name', '')}\n"
            scheme_details_text += f"Category: {mf_data.get('category', '')} - {mf_data.get('sub_category', '')}\n"
            scheme_details_text += f"Benchmark: {mf_data.get('benchmark_name', '')}\n"
            scheme_details_text += f"Risk: {mf_data.get('nfo_risk', '')}\n"
            scheme_details_text += f"Description: {mf_data.get('description', '')}\n"
        sections.append(Section(name="Scheme Details", text=scheme_details_text.strip()))

        # --- Expense Ratio ---
        expense_text = ""
        if mf_data and mf_data.get("expense_ratio"):
            expense_text = f"Expense Ratio: {mf_data['expense_ratio']}%"
        else:
            # Fallback
            el = soup.find(string=lambda t: t and "expense ratio" in t.lower() and t.parent.name != "script")
            if el and el.parent and el.parent.parent:
                expense_text = el.parent.parent.text.strip()
        sections.append(Section(name="Expense Ratio", text=expense_text))

        # --- Exit Load ---
        exit_load_text = ""
        if mf_data and mf_data.get("exit_load"):
            exit_load_text = str(mf_data["exit_load"]).strip()
        else:
            el = soup.find(string=lambda t: t and "exit load" in t.lower() and t.parent.name != "script")
            if el and el.parent and el.parent.parent:
                exit_load_text = el.parent.parent.text.strip()
        sections.append(Section(name="Exit Load", text=exit_load_text))

        # --- AUM ---
        aum_text = ""
        if mf_data and mf_data.get("aum"):
            aum_text = f"AUM: ₹{mf_data['aum']} Cr"
        else:
            el = soup.find(string=lambda t: t and "Asset Under Management" in t and t.parent.name != "script")
            if el and el.parent:
                aum_text = el.parent.text.strip()
            elif soup.find("div", class_="bodyLarge"):
                aum_text = soup.find("div", class_="bodyLarge").text.strip()
        sections.append(Section(name="AUM", text=aum_text))
        
        # --- NAV ---
        nav_text = ""
        if mf_data and mf_data.get("nav"):
            nav_text = f"NAV: ₹{mf_data['nav']}"
        else:
            el = soup.find(string=lambda t: t and "Latest NAV" in t and t.parent.name != "script")
            if el and el.parent:
                nav_text = el.parent.text.strip()
            elif soup.find("div", class_="bodyLarge"):
                nav_text = soup.find("div", class_="bodyLarge").text.strip()
        sections.append(Section(name="NAV", text=nav_text))
        
        # --- Fund Manager ---
        manager_text = ""
        if mf_data and mf_data.get("fund_manager_details"):
            for mgr in mf_data["fund_manager_details"]:
                manager_text += f"Manager: {mgr.get('person_name', '')}\n"
                manager_text += f"Tenure: Since {mgr.get('date_from', '')[:10]}\n"
                manager_text += f"Experience: {mgr.get('experience', '')}\n\n"
        sections.append(Section(name="Fund Manager", text=manager_text.strip()))

        # --- Fund House ---
        fund_house_text = ""
        if mf_data and mf_data.get("amc_info"):
            info = mf_data["amc_info"]
            fund_house_text += f"AMC: {info.get('name', '')}\n"
            fund_house_text += f"Rank: {info.get('rank', '')}\n"
            fund_house_text += f"Launch Date: {info.get('launch_date', '')[:10]}\n"
            fund_house_text += f"Address: {info.get('address', '')}\n"
            fund_house_text += f"Email: {info.get('email', '')}\n"
            fund_house_text += f"Phone: {info.get('phone', '')}\n"
        sections.append(Section(name="Fund House", text=fund_house_text.strip()))

        # --- Trafilatura Main Text / Overview ---
        traf_text = trafilatura.extract(html, include_links=False, include_formatting=False)
        if traf_text:
            sections.append(Section(name="Overview", text=traf_text))

        # Determine health
        anchors = {}
        for kw in self.must_have_keys:
            found = any(kw.lower() in s.name.lower() and len(s.text) > 2 for s in sections)
            anchors[kw] = found

        health = "ok" if sum(anchors.values()) >= len(self.must_have_keys) - 1 else "degraded"

        return ExtractedDoc(
            scheme_id=scheme_id,
            source_url=url,
            fetched_at=fetched_at,
            sections=sections,
            must_have_anchors=anchors,
            extraction_health=health
        )
