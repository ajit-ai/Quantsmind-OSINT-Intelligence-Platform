# Scrapy + Playwright collector — hardened for JS-heavy pages with fallback
import requests
from bs4 import BeautifulSoup
from collectors.policies import PolicyEnforcer

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    pass

HEADERS = {"User-Agent": "Quantsmind-OSINT/1.0 (+https://quantsmind.example.com/bot; public data only; respects robots.txt)"}

def _fetch_requests(url, timeout=15):
    resp = requests.get(url, timeout=timeout, headers=HEADERS)
    resp.raise_for_status()
    return resp.text

def _fetch_playwright(url, timeout=15000):
    if not PLAYWRIGHT_AVAILABLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # wait for network idle for JS rendering
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[playwright] fetch failed {url}: {e}")
        return None

def collect_scrape(source, policy=None, use_playwright=None):
    enforcer = PolicyEnforcer(policy)
    if not enforcer.can_fetch(source.url):
        print(f"[scrape] blocked by policy: {source.url}")
        return []
    enforcer.throttle()
    # auto: use playwright if source config requests it or source_type scrape + js flag
    if use_playwright is None:
        use_playwright = bool((source.config or {}).get("use_playwright") or (source.config or {}).get("js_render"))
    html = None
    if use_playwright:
        html = _fetch_playwright(source.url)
    if html is None:
        try:
            html = _fetch_requests(source.url)
        except Exception as e:
            print(f"[scrape] requests failed {source.url}: {e}")
            return []
    soup = BeautifulSoup(html, "lxml")
    items = []
    # Scrapy-like selector logic (covers quotes.toscrape and generic news)
    for el in soup.select(".quote"):
        text = el.select_one(".text")
        author = el.select_one(".author")
        tags = [t.get_text(strip=True) for t in el.select(".tag")]
        items.append({
            "url": source.url,
            "title": author.get_text(strip=True) if author else (soup.title.string.strip() if soup.title else ""),
            "content_text": text.get_text(strip=True) if text else el.get_text(" ", strip=True),
            "published_at": None,
            "meta": {"tags": tags},
        })
    if not items:
        # Generic: article tags
        for art in soup.select("article, .article, .post, .news-item"):
            title_el = art.select_one("h1,h2,h3,a")
            link = art.select_one("a[href]")
            items.append({
                "url": (link.get("href") if link and link.get("href","").startswith("http") else source.url),
                "title": title_el.get_text(strip=True) if title_el else "",
                "content_text": art.get_text(" ", strip=True)[:5000],
                "published_at": None,
            })
            if len(items) >= 20:
                break
    if not items:
        # fallback: paragraphs
        for p in soup.find_all("p")[:10]:
            txt = p.get_text(strip=True)
            if len(txt) > 40:
                items.append({"url": source.url, "title": soup.title.string.strip() if soup.title and soup.title.string else "", "content_text": txt, "published_at": None})
    return items[:20]
