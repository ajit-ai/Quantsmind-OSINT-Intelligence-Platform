from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count
from django.db.models.functions import TruncDate
from .models import CollectedDocument
from .serializers import CollectedDocumentSerializer

class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CollectedDocument.objects.select_related("source","enrichment").order_by("-collected_at")
    serializer_class = CollectedDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "source": ["exact"],
        "status": ["exact","in"],
        "language": ["exact"],
        "source__slug": ["exact"],
    }
    search_fields = ["title", "content_text", "url", "source__name"]
    ordering_fields = ["collected_at", "published_at", "title"]
    ordering = ["-collected_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        # viewer can read all; row-level filtering could go here (e.g. source allowlist)
        return qs

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        qs = self.get_queryset()
        from django.db.models import Count
        by_status = list(qs.values("status").annotate(count=Count("id")).order_by("status"))
        by_source = list(qs.values("source__slug").annotate(count=Count("id")).order_by("-count")[:10])
        by_language = list(qs.values("language").annotate(count=Count("id")).order_by("-count")[:10])
        return Response({"by_status": by_status, "by_source": by_source, "by_language": by_language, "total": qs.count()})
