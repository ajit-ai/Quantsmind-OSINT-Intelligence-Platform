import requests
from bs4 import BeautifulSoup
from collectors.policies import PolicyEnforcer

def collect_scrape(source, policy=None):
    enforcer = PolicyEnforcer(policy)
    if not enforcer.can_fetch(source.url): return []
    enforcer.throttle()
    try:
        resp = requests.get(source.url, timeout=15, headers={"User-Agent": "OSINT-Platform/1.0 (+research)"})
        soup = BeautifulSoup(resp.text, "lxml")
        # generic extraction - quotes.toscrape compatible
        items = []
        for el in soup.select(".quote"):
            text = el.select_one(".text")
            author = el.select_one(".author")
            items.append({"url": source.url, "title": author.get_text(strip=True) if author else "", "content_text": text.get_text(strip=True) if text else "", "published_at": None})
        if not items:
            # fallback: all paragraphs
            for p in soup.find_all("p")[:10]:
                items.append({"url": source.url, "title": soup.title.string if soup.title else "", "content_text": p.get_text(strip=True), "published_at": None})
        return items[:20]
    except Exception as e:
        print(f"scrape failed: {e}")
        return []
