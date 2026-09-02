from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import CollectedDocument
from .serializers import CollectedDocumentSerializer

class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CollectedDocument.objects.select_related("source").order_by("-collected_at")
    serializer_class = CollectedDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["source", "status", "language"]
    search_fields = ["title", "content_text", "url"]
    ordering_fields = ["collected_at", "published_at"]
