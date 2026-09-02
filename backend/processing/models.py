from django.db import models
from ingestion.models import CollectedDocument

class Enrichment(models.Model):
    document = models.OneToOneField(CollectedDocument, on_delete=models.CASCADE, related_name="enrichment")
    entities = models.JSONField(default=list, blank=True, help_text="[{text,type,start,end}] from spaCy/HF")
    sentiment = models.JSONField(default=dict, blank=True, help_text="{label: positive|negative|neutral, score: 0..1} via HF pipeline or lexicon")
    topics = models.JSONField(default=list, blank=True, help_text="topic keywords; BERTopic if ENABLE_BERTOPIC=1 else KeyBERT fallback")
    language = models.CharField(max_length=10, blank=True, default="", db_index=True)
    summary = models.TextField(blank=True, default="")
    geo_locations = models.JSONField(default=list, blank=True, help_text="[{name, type, lat, lon}] from GPE/LOC entities")
    processed_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["language"])]

class Entity(models.Model):
    name = models.CharField(max_length=300, db_index=True)
    entity_type = models.CharField(max_length=20, choices=[("PERSON","Person"),("ORG","Org"),("GPE","GPE"),("LOC","LOC"),("EVENT","Event"),("MISC","Misc")], default="MISC")
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = [("name","entity_type")]
        indexes = [models.Index(fields=["entity_type"])]
