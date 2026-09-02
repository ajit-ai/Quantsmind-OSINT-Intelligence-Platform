from rest_framework import serializers
from .models import CollectedDocument
class CollectedDocumentSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    class Meta:
        model = CollectedDocument
        fields = ["id","source","source_name","url","canonical_url","title","content_text","language","published_at","collected_at","hash","status"]
        read_only_fields = ["id","collected_at","hash"]
