from django.db import models
from ingestion.models import CollectedDocument

class Enrichment(models.Model):
    document = models.OneToOneField(CollectedDocument, on_delete=models.CASCADE, related_name="enrichment")
    entities = models.JSONField(default=list, blank=True)
    sentiment = models.JSONField(default=dict, blank=True)  # {label, score}
    topics = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=10, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    geo_locations = models.JSONField(default=list, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

class Entity(models.Model):
    name = models.CharField(max_length=300, db_index=True)
    entity_type = models.CharField(max_length=20, choices=[("PERSON","Person"),("ORG","Org"),("GPE","GPE"),("EVENT","Event"),("MISC","Misc")], default="MISC")
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = [("name","entity_type")]
