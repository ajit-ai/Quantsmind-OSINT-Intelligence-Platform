from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Watchlist, WatchlistRule, Alert
from .serializers import WatchlistSerializer, WatchlistRuleSerializer, AlertSerializer
from accounts.permissions import IsOwnerOrAdmin

class WatchlistViewSet(viewsets.ModelViewSet):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Watchlist.objects.filter(user=self.request.user).prefetch_related("rules").order_by("-created_at")
        if self.request.user.role == "admin":
            # admins see all (for ops)
            qs = Watchlist.objects.all().prefetch_related("rules").order_by("-created_at")
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action in ("list","retrieve","create","update","partial_update","destroy"):
            return [IsAuthenticated(), IsOwnerOrAdmin() if self.action in ("update","partial_update","destroy") else IsAuthenticated()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["get","post"], url_path="rules")
    def rules(self, request, pk=None):
        wl = self.get_object()
        if request.method == "GET":
            ser = WatchlistRuleSerializer(wl.rules.all(), many=True)
            return Response(ser.data)
        # POST create rule under watchlist
        data = request.data.copy()
        data["watchlist"] = wl.id
        ser = WatchlistRuleSerializer(data=data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="rules/(?P<rule_id>[^/.]+)")
    def delete_rule(self, request, pk=None, rule_id=None):
        wl = self.get_object()
        rule = get_object_or_404(WatchlistRule, id=rule_id, watchlist=wl)
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Alert.objects.select_related("rule__watchlist","document").order_by("-triggered_at")
        if self.request.user.role == "admin":
            return qs
        return qs.filter(rule__watchlist__user=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        alert = self.get_object()
        # owner check
        if alert.rule.watchlist.user != request.user and request.user.role != "admin":
            return Response({"detail":"forbidden"}, status=403)
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response({"is_read": True})

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        qs = self.get_queryset().filter(is_read=False)
        qs.update(is_read=True)
        return Response({"updated": qs.count()})
