from rest_framework import serializers
from .models import Source, CollectionPolicy
class CollectionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionPolicy
        fields = "__all__"
class SourceSerializer(serializers.ModelSerializer):
    policies = CollectionPolicySerializer(many=True, read_only=True)
    class Meta:
        model = Source
        fields = ["id","name","slug","source_type","url","config","is_active","created_at","policies"]
