from django.db import models

class Source(models.Model):
    class SourceType(models.TextChoices):
        RSS = "rss", "RSS"
        NEWS_API = "news_api", "News API"
        SCRAPE = "scrape", "Web Scrape"
        SOCIAL = "social", "Social API"
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, help_text="used for S3 prefix raw/{slug}/ and ES source term")
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    url = models.URLField(help_text="feed URL, scrape URL, or API endpoint")
    config = models.JSONField(default=dict, blank=True, help_text='e.g. {"fetch_full_text": true, "use_playwright": true, "js_render": true, "endpoint": "...", "params": {...}}')
    is_active = models.BooleanField(default=True)
    collection_interval_minutes = models.IntegerField(default=15, help_text="Celery Beat per-source interval; 0 = manual only")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["name"]
    def __str__(self): return f"{self.name} ({self.source_type})"

class CollectionPolicy(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="policies")
    respects_robots = models.BooleanField(default=True, help_text="Honor robots.txt via cached RobotFileParser (TTL 1h)")
    rate_limit_rps = models.FloatField(default=1.0, help_text="Throttle per-source; clamped 0.1..10 rps")
    allowed_domains = models.JSONField(default=list, blank=True, help_text="Allowlist; empty = allow all domains")
    block_auth_required = models.BooleanField(default=True)
    block_paywall = models.BooleanField(default=True)
    jurisdiction = models.CharField(max_length=100, blank=True, default="", help_text="Per-jurisdiction tuning; policy may differ by region")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Policy:{self.source.slug} rps={self.rate_limit_rps}"
