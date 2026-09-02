import feedparser, requests, hashlib, datetime
from bs4 import BeautifulSoup

def collect_rss(source, policy=None):
    from collectors.policies import PolicyEnforcer
    enforcer = PolicyEnforcer(policy)
    if not enforcer.can_fetch(source.url): return []
    enforcer.throttle()
    feed = feedparser.parse(source.url)
    items = []
    for entry in feed.entries[:20]:
        url = entry.get("link", "")
        if not enforcer.can_fetch(url): continue
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        # try fetch full article text
        text = BeautifulSoup(summary, "lxml").get_text(separator=" ") if summary else ""
        published = entry.get("published_parsed")
        published_at = None
        if published:
            try: published_at = datetime.datetime(*published[:6])
            except: pass
        items.append({"url": url, "title": title, "content_text": text or summary, "published_at": published_at})
    return items
