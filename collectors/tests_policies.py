import time
import types
from unittest.mock import patch, MagicMock
from collectors.policies import PolicyEnforcer

def _policy(**kw):
    defaults = dict(respects_robots=True, rate_limit_rps=2.0, allowed_domains=[], block_auth_required=True, block_paywall=True, jurisdiction="")
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)

def test_can_fetch_blocks_login_and_paywall():
    pol = _policy(block_auth_required=True, block_paywall=True, respects_robots=False)
    en = PolicyEnforcer(pol)
    assert not en.can_fetch("http://example.com/login")
    assert not en.can_fetch("http://example.com/paywall/subscribe")
    assert en.can_fetch("http://example.com/news/article")

def test_can_fetch_allows_when_policy_none():
    en = PolicyEnforcer(None)
    assert en.can_fetch("http://example.com/anything")

def test_allowed_domains_allowlist():
    pol = _policy(allowed_domains=["example.com"], respects_robots=False)
    en = PolicyEnforcer(pol)
    assert en.can_fetch("http://example.com/page")
    # subdomain allowed via endswith
    assert en.can_fetch("http://sub.example.com/page")
    assert not en.can_fetch("http://other.com/page")

def test_respects_robots_cached(monkeypatch):
    pol = _policy(respects_robots=True)
    en = PolicyEnforcer(pol)
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = False
    with patch("collectors.policies.urllib.robotparser.RobotFileParser") as MockParser:
        MockParser.return_value = mock_rp
        mock_rp.read.return_value = None
        assert not en.can_fetch("http://example.com/blocked")
        # second call uses cache - MockParser not called again
        MockParser.reset_mock()
        assert not en.can_fetch("http://example.com/blocked2")
        # should not create new parser due to cache
        # (depends on TTL; within same second cache hit)
        assert MockParser.call_count == 0

def test_throttle_sleeps():
    pol = _policy(rate_limit_rps=2.0)
    en = PolicyEnforcer(pol)
    start = time.time()
    en.throttle()
    en.throttle()  # second should sleep ~0.5s
    elapsed = time.time() - start
    assert elapsed >= 0.4
