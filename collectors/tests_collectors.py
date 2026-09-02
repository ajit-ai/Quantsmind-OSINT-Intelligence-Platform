import types
from unittest.mock import patch, MagicMock
import datetime

def _source(url="http://example.com/rss", slug="test", source_type="rss", config=None):
    return types.SimpleNamespace(url=url, slug=slug, source_type=source_type, config=config or {})

def test_collect_rss_parses_feed():
    src = _source(url="http://example.com/rss")
    pol = types.SimpleNamespace(respects_robots=False, rate_limit_rps=10, allowed_domains=[], block_auth_required=False, block_paywall=False)
    fake_entry = {"link":"http://example.com/1","title":"Hello","summary":"<p>Summary text</p>","published_parsed": (2024,1,1,0,0,0,0,0,0)}
    fake_feed = types.SimpleNamespace(entries=[fake_entry], bozo=0)
    with patch("collectors.rss_collector.feedparser.parse", return_value=fake_feed):
        from collectors.rss_collector import collect_rss
        items = collect_rss(src, pol)
        assert len(items)==1
        assert items[0]["url"]=="http://example.com/1"
        assert "Hello" in items[0]["title"]

def test_collect_rss_fetch_full_text_flag():
    src = _source(config={"fetch_full_text": True})
    pol = types.SimpleNamespace(respects_robots=False, rate_limit_rps=10, allowed_domains=[], block_auth_required=False, block_paywall=False)
    fake_entry = {"link":"http://example.com/full","title":"T","summary":"short","published_parsed": None}
    fake_feed = types.SimpleNamespace(entries=[fake_entry], bozo=0)
    with patch("collectors.rss_collector.feedparser.parse", return_value=fake_feed), \
         patch("collectors.rss_collector._fetch_full_text", return_value="full article content extracted") as mock_fetch:
        from collectors.rss_collector import collect_rss
        items = collect_rss(src, pol)
        assert mock_fetch.called
        assert items[0]["content_text"]=="full article content extracted"

def test_collect_scrape_requests_fallback():
    src = _source(url="http://example.com", config={})
    pol = types.SimpleNamespace(respects_robots=False, rate_limit_rps=10, allowed_domains=[], block_auth_required=False, block_paywall=False)
    html = "<html><head><title>Test</title></head><body><div class=\"quote\"><span class=\"text\">A quote</span><small class=\"author\">Author</small></div></body></html>"
    with patch("collectors.scrapy_collector._fetch_requests", return_value=html):
        from collectors.scrapy_collector import collect_scrape
        items = collect_scrape(src, pol, use_playwright=False)
        assert len(items)>=1
        assert "A quote" in items[0]["content_text"]

def test_collect_scrape_playwright_path():
    src = _source(config={"use_playwright": True})
    pol = types.SimpleNamespace(respects_robots=False, rate_limit_rps=10, allowed_domains=[], block_auth_required=False, block_paywall=False)
    html = "<html><body><p>Paragraph content longer than forty characters for testing purpose</p></body></html>"
    with patch("collectors.scrapy_collector._fetch_playwright", return_value=html):
        from collectors.scrapy_collector import collect_scrape
        items = collect_scrape(src, pol)
        assert len(items)>=1

def test_collect_news_api_parses_gdelt():
    src = _source(url="http://example.com/api", config={"params":{"query":"world"}})
    fake_json = {"articles":[{"url":"http://example.com/a1","title":"Title 1","description":"Desc 1"}, {"url":"http://example.com/a2","title":"Title 2","seentone":"Tone"}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_json
    mock_resp.raise_for_status.return_value = None
    with patch("collectors.news_api_collector.requests.get", return_value=mock_resp):
        from collectors.news_api_collector import collect_news_api
        items = collect_news_api(src, pol=None)
        assert len(items)==2
        assert items[0]["title"]=="Title 1"
