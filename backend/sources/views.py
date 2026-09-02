from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Source, CollectionPolicy
from .serializers import SourceSerializer, CollectionPolicySerializer
from accounts.permissions import IsAnalyst, IsAdmin

class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all().order_by("name")
    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list","retrieve"):
            return [IsAuthenticated()]
        if self.action in ("create","update","partial_update","destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"], permission_classes=[IsAnalyst])
    def trigger(self, request, pk=None):
        from collectors.tasks import poll_source
        src = self.get_object()
        # respect policy: disabled sources cannot be triggered
        if not src.is_active:
            return Response({"detail":"source disabled"}, status=400)
        # enqueue with Celery; idempotent
        poll_source.delay(str(src.id))
        # audit log via middleware; also explicit
        return Response({"status": "queued", "source": src.slug, "id": str(src.id)})

    @action(detail=True, methods=["get","post"], url_path="policies")
    def policies(self, request, pk=None):
        src = self.get_object()
        if request.method == "GET":
            ser = CollectionPolicySerializer(src.policies.all(), many=True)
            return Response(ser.data)
        # POST create/update policy
        if request.user.role not in ("admin",):
            return Response({"detail":"admin only"}, status=403)
        data = request.data.copy()
        data["source"] = src.id
        ser = CollectionPolicySerializer(data=data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[IsAnalyst], url_path="trigger-all")
    def trigger_all(self, request):
        from collectors.tasks import poll_all_sources
        count = poll_all_sources.delay()
        return Response({"status":"queued_all"})
