from bs4 import BeautifulSoup
import glob
import re

html_files = glob.glob("data/raw/hdfc_equity/*.html")
if not html_files:
    print("No html files found")
else:
    with open(html_files[-1], "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        
        # Search for NAV or AUM text
        for elem in soup.find_all(string=re.compile(r'NAV|AUM', re.I)):
            parent = elem.parent
            # Only print if it's not a script or style
            if parent.name not in ['script', 'style']:
                print(f"FOUND: {elem.strip()} -> Parent: {parent.name}, Class: {parent.get('class')}")
                print(f"Parent Text: {parent.get_text(strip=True)[:100]}")
                print("-" * 40)
