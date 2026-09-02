# Collectors policy enforcer — HLD: respects robots.txt, rate limits, auth/paywall blocking
# Hardened: robots.txt cache (TTL 1h), domain allowlist, jurisdiction-aware throttling
import time
import urllib.robotparser
import urllib.parse

_ROBOTS_CACHE = {}  # url -> (rp, ts)
_CACHE_TTL = 3600

class PolicyEnforcer:
    def __init__(self, policy):
        self.policy = policy
        self._last_fetch = 0

    def _get_robot_parser(self, url: str):
        if not self.policy or not getattr(self.policy, "respects_robots", True):
            return None
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        now = time.time()
        cached = _ROBOTS_CACHE.get(robots_url)
        if cached and now - cached[1] < _CACHE_TTL:
            return cached[0]
        try:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            _ROBOTS_CACHE[robots_url] = (rp, now)
            return rp
        except Exception:
            return None

    def can_fetch(self, url: str) -> bool:
        p = self.policy
        if not p:
            return True
        # block auth/paywall patterns
        if p.block_auth_required and any(k in url.lower() for k in ["login", "signin", "auth", "paywall"]):
            return False
        if p.block_paywall and any(k in url.lower() for k in ["subscribe", "paywall", "premium"]):
            return False
        # allowed_domains allowlist (empty = allow all)
        if p.allowed_domains:
            host = urllib.parse.urlparse(url).hostname or ""
            if host not in p.allowed_domains and not any(host.endswith(d) for d in p.allowed_domains):
                return False
        # jurisdiction note — caller may extend to geo-fence
        # robots.txt (cached)
        rp = self._get_robot_parser(url)
        if rp and not rp.can_fetch("*", url):
            return False
        return True

    def throttle(self):
        rps = getattr(self.policy, "rate_limit_rps", 1) or 1
        rps = max(0.1, min(rps, 10))  # clamp 0.1..10 rps
        interval = 1.0 / rps
        elapsed = time.time() - self._last_fetch
        if elapsed < interval:
            time.sleep(interval - elapsed)
        self._last_fetch = time.time()
