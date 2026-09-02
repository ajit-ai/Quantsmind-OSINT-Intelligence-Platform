import time, urllib.robotparser, urllib.parse, requests

class PolicyEnforcer:
    def __init__(self, policy):
        self.policy = policy
        self._last_fetch = 0

    def can_fetch(self, url: str) -> bool:
        p = self.policy
        if not p: return True
        if p.block_auth_required and "login" in url: return False
        if p.allowed_domains and urllib.parse.urlparse(url).hostname not in p.allowed_domains:
            # allow if allowed_domains empty -> all allowed
            pass
        if p.respects_robots:
            try:
                parsed = urllib.parse.urlparse(url)
                robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                if not rp.can_fetch("*", url): return False
            except: pass
        return True

    def throttle(self):
        rps = getattr(self.policy, "rate_limit_rps", 1) or 1
        interval = 1.0 / rps
        elapsed = time.time() - self._last_fetch
        if elapsed < interval: time.sleep(interval - elapsed)
        self._last_fetch = time.time()
