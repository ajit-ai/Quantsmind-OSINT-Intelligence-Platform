from django.db import models

class Source(models.Model):
    class SourceType(models.TextChoices):
        RSS = "rss", "RSS"
        NEWS_API = "news_api", "News API"
        SCRAPE = "scrape", "Web Scrape"
        SOCIAL = "social", "Social API"
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    url = models.URLField()
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name} ({self.source_type})"

class CollectionPolicy(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="policies")
    respects_robots = models.BooleanField(default=True)
    rate_limit_rps = models.FloatField(default=1.0)
    allowed_domains = models.JSONField(default=list, blank=True)
    block_auth_required = models.BooleanField(default=True)
    block_paywall = models.BooleanField(default=True)
    jurisdiction = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
