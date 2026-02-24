"""
metadata.py
Holt Metadaten (Titel, Beschreibung, Bild) von URLs via OpenGraph.
"""
import requests
from bs4 import BeautifulSoup

def fetch_metadata(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=3)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        data = {}

        # 1. Titel
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
            # Bereinigung für YouTube/Netflix Suffixe
            title = title.replace(" - YouTube", "").replace(" | Netflix", "")
            data["title"] = title
        else:
            data["title"] = soup.title.string if soup.title else "Unbekannter Titel"

        # 2. Beschreibung
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            data["description"] = og_desc.get("content")

        # 3. Thumbnail
        og_image = soup.find("meta", property="og:image")
        if og_image:
            data["thumbnail_url"] = og_image.get("content")

        return data

    except Exception as e:
        print(f"[Metadata] Fehler bei {url}: {e}")
        return None