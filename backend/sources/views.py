from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Source
from .serializers import SourceSerializer
from accounts.permissions import IsAnalyst

class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all().order_by("name")
    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], permission_classes=[IsAnalyst])
    def trigger(self, request, pk=None):
        from collectors.tasks import poll_source
        poll_source.delay(str(self.get_object().id))
        return Response({"status": "queued"})
