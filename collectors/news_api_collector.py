import requests
import datetime

def collect_news_api(source, policy=None):
    cfg = source.config or {}
    # Supports GDELT and generic NewsAPI-style. Config schema:
    # { "endpoint": "https://api.gdeltproject.org/api/v2/doc/doc", "params": {...}, "headers": {...} }
    url = cfg.get("endpoint") or source.url
    params = cfg.get("params", {"query": "world", "mode": "ArtList", "maxrecords": "20", "format": "json"})
    headers = cfg.get("headers", {"User-Agent": "Quantsmind-OSINT/1.0"})
    # Respect rate limit via policy enforcer
    if policy:
        from collectors.policies import PolicyEnforcer
        enforcer = PolicyEnforcer(policy)
        if not enforcer.can_fetch(url):
            print(f"[news_api] blocked by policy: {url}")
            return []
        enforcer.throttle()
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        if isinstance(data, dict):
            articles = data.get("articles", []) or data.get("results", []) or data.get("items", []) or []
            # GDELT nests under articles
            if not articles and "articles" in str(data)[:500]:
                articles = data.get("articles", [])
        elif isinstance(data, list):
            articles = data
        items = []
        for a in articles[:20]:
            if not isinstance(a, dict):
                continue
            link = a.get("url") or a.get("link") or a.get("guid") or ""
            title = (a.get("title") or a.get("name") or "")[:1000]
            text = (a.get("description") or a.get("content") or a.get("seentone") or a.get("summary") or title)[:5000]
            published_at = None
            for k in ["publishedAt", "pubDate", "date", "published", "seendate"]:
                if a.get(k):
                    try:
                        published_at = a[k]
                        if isinstance(published_at, str):
                            # try parse ISO
                            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
                                try:
                                    published_at = datetime.datetime.strptime(published_at, fmt)
                                    break
                                except Exception:
                                    continue
                            if isinstance(published_at, str):
                                published_at = None
                        break
                    except Exception:
                        published_at = None
            items.append({"url": link or url, "title": title, "content_text": text, "published_at": published_at})
        # fallback: if API returned HTML or nothing, log
        if not items:
            print(f"[news_api] no articles from {url} params={params} resp keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
        return items
    except Exception as e:
        print(f"[news_api] collect failed {url}: {e}")
        return []
