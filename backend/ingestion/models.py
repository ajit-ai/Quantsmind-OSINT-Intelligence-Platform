import hashlib
from django.db import models
from sources.models import Source

class CollectedDocument(models.Model):
    class Status(models.TextChoices):
        RAW = "raw", "Raw"
        ENRICHED = "enriched", "Enriched"
        INDEXED = "indexed", "Indexed"
        FAILED = "failed", "Failed"
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="documents")
    url = models.URLField(max_length=2000)
    canonical_url = models.URLField(max_length=2000, blank=True, default="")
    title = models.CharField(max_length=1000, blank=True, default="")
    content_text = models.TextField(blank=True, default="")
    content_html_s3_key = models.CharField(max_length=1000, blank=True, default="")
    language = models.CharField(max_length=10, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    hash = models.CharField(max_length=64, db_index=True, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RAW)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["hash"], name="uniq_doc_hash", condition=models.Q(hash__gt=""))]
        indexes = [models.Index(fields=["collected_at"]), models.Index(fields=["status"])]

    def save(self, *args, **kwargs):
        if self.content_text and not self.hash:
            self.hash = hashlib.sha256(self.content_text.encode()[:10000]).hexdigest()
        super().save(*args, **kwargs)

class RawArtifact(models.Model):
    document = models.OneToOneField(CollectedDocument, on_delete=models.CASCADE, related_name="artifact")
    s3_bucket = models.CharField(max_length=200, default="osint-raw")
    s3_key = models.CharField(max_length=1000)
    content_type = models.CharField(max_length=100, default="text/html")
    size_bytes = models.IntegerField(default=0)
