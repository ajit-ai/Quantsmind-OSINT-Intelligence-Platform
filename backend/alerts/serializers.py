from rest_framework import serializers
from .models import Watchlist, WatchlistRule, Alert
class WatchlistRuleSerializer(serializers.ModelSerializer):
    class Meta: model = WatchlistRule; fields = "__all__"
class WatchlistSerializer(serializers.ModelSerializer):
    rules = WatchlistRuleSerializer(many=True, read_only=True)
    class Meta: model = Watchlist; fields = ["id","name","is_active","created_at","rules"]
class AlertSerializer(serializers.ModelSerializer):
    class Meta: model = Alert; fields = "__all__"
