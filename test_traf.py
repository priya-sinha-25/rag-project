import trafilatura
from bs4 import BeautifulSoup
import sys

with open(r"data\raw\hdfc_equity\20260518T084759Z.html", "r", encoding="utf-8") as f:
    html = f.read()
    
text = trafilatura.extract(html, include_links=True, include_formatting=True)
with open("traf_out.txt", "w", encoding="utf-8") as f:
    f.write(text if text else "None")

# Also let's check BS4 for 'Expense ratio'
soup = BeautifulSoup(html, "html.parser")
elems = soup.find_all(string=lambda t: t and "expense ratio" in t.lower())
with open("bs4_out.txt", "w", encoding="utf-8") as f:
    for el in elems:
        f.write(f"{el.parent.name} : {repr(el.strip())} -> {repr(el.parent.parent.text[:100])}\n")
