from django.db import models
from django.conf import settings
from ingestion.models import CollectedDocument

class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlists")
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class WatchlistRule(models.Model):
    class RuleType(models.TextChoices):
        KEYWORD = "keyword", "Keyword"
        ENTITY = "entity", "Entity"
        TOPIC = "topic", "Topic"
        SENTIMENT = "sentiment", "Sentiment"
    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=20, choices=RuleType.choices)
    value = models.CharField(max_length=300)
    threshold = models.FloatField(default=0.0)

class Alert(models.Model):
    rule = models.ForeignKey(WatchlistRule, on_delete=models.CASCADE, related_name="alerts")
    document = models.ForeignKey(CollectedDocument, on_delete=models.CASCADE, related_name="alerts")
    triggered_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    severity = models.CharField(max_length=20, default="medium")
