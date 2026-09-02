import requests, datetime
def collect_news_api(source, policy=None):
    # Generic GDELT / NewsAPI-style collector - source.config holds endpoint/params
    cfg = source.config or {}
    # GDELT example: https://api.gdeltproject.org/api/v2/doc/doc?query=world&mode=ArtList&maxrecords=20&format=json
    url = cfg.get("endpoint") or source.url
    params = cfg.get("params", {"query": "world", "mode": "ArtList", "maxrecords": "20", "format": "json"})
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        articles = data.get("articles", []) if isinstance(data, dict) else []
        items = []
        for a in articles[:20]:
            items.append({"url": a.get("url",""), "title": a.get("title",""), "content_text": a.get("seentone","") or a.get("title",""), "published_at": None})
        return items
    except Exception as e:
        print(f"news_api collect failed: {e}")
        return []
