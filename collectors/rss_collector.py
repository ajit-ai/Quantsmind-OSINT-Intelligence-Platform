import feedparser
import requests
import datetime
from bs4 import BeautifulSoup
from collectors.policies import PolicyEnforcer

FETCH_TIMEOUT = 15

def _fetch_full_text(url, policy=None):
    enforcer = PolicyEnforcer(policy)
    if not enforcer.can_fetch(url):
        return ""
    enforcer.throttle()
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": "Quantsmind-OSINT/1.0 (+respects robots.txt)"})
        soup = BeautifulSoup(resp.text, "lxml")
        # extract main content
        article = soup.select_one("article") or soup
        texts = [p.get_text(" ", strip=True) for p in article.find_all("p")]
        return " ".join(t for t in texts if len(t) > 40)[:5000]
    except Exception as e:
        print(f"[rss] full fetch failed {url}: {e}")
        return ""

def collect_rss(source, policy=None):
    from collectors.policies import PolicyEnforcer
    enforcer = PolicyEnforcer(policy)
    if not enforcer.can_fetch(source.url):
        print(f"[rss] blocked by policy: {source.url}")
        return []
    enforcer.throttle()
    # use feedparser with custom UA
    feed = feedparser.parse(source.url, agent="Quantsmind-OSINT/1.0")
    if getattr(feed, "bozo", 0) and not feed.entries:
        print(f"[rss] bozo {source.url}: {getattr(feed, 'bozo_exception', '')}")
        return []
    items = []
    fetch_full = bool((source.config or {}).get("fetch_full_text"))
    for entry in feed.entries[:20]:
        url = entry.get("link", "")
        if not url or not enforcer.can_fetch(url):
            continue
        title = entry.get("title", "")[:1000]
        summary = entry.get("summary", "") or entry.get("description", "")
        text = BeautifulSoup(summary, "lxml").get_text(" ", strip=True) if summary else ""
        if fetch_full and url:
            full = _fetch_full_text(url, policy)
            if full:
                text = full
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = None
        if published:
            try:
                published_at = datetime.datetime(*published[:6], tzinfo=datetime.timezone.utc)
            except Exception:
                pass
        items.append({"url": url, "title": title, "content_text": text or summary[:5000] or title, "published_at": published_at})
    return items
