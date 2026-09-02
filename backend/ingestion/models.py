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
    content_html_s3_key = models.CharField(max_length=1000, blank=True, default="", help_text="S3 key for raw HTML; verified via head_object after put")
    language = models.CharField(max_length=10, blank=True, default="", db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # sha256(content_text) for exact dedup; near-dup via simhash in processing.nlp.simhash_near_dup
    hash = models.CharField(max_length=64, db_index=True, blank=True, default="", help_text="sha256 of content_text[:10000]; unique where non-empty")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RAW, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["hash"], name="uniq_doc_hash", condition=models.Q(hash__gt=""))]
        indexes = [models.Index(fields=["collected_at"]), models.Index(fields=["status"]), models.Index(fields=["language"])]

    def save(self, *args, **kwargs):
        if self.content_text and not self.hash:
            self.hash = hashlib.sha256(self.content_text.encode()[:10000]).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.source.slug if self.source_id else 'no-source'}:{self.title[:60]}"

class RawArtifact(models.Model):
    document = models.OneToOneField(CollectedDocument, on_delete=models.CASCADE, related_name="artifact")
    s3_bucket = models.CharField(max_length=200, default="osint-raw")
    s3_key = models.CharField(max_length=1000, help_text="Verified via S3 head_object after put")
    content_type = models.CharField(max_length=100, default="text/html")
    size_bytes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
