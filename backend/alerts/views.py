from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Watchlist, Alert
from .serializers import WatchlistSerializer, AlertSerializer

class WatchlistViewSet(viewsets.ModelViewSet):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Watchlist.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Alert.objects.filter(rule__watchlist__user=self.request.user).order_by("-triggered_at")
