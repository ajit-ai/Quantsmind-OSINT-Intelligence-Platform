from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .search import search_es

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search(request):
    q = request.query_params.get("q", "")
    filters = {k: v for k,v in request.query_params.items() if k in ("source","language","sentiment.label")}
    return Response(search_es(q, filters))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trends(request):
    from ingestion.models import CollectedDocument
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    qs = CollectedDocument.objects.values(date=TruncDate("collected_at")).annotate(count=Count("id")).order_by("date")[:30]
    return Response(list(qs))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def geo(request):
    from processing.models import Enrichment
    locs = []
    for e in Enrichment.objects.exclude(geo_locations=[]).values_list("geo_locations", flat=True)[:100]:
        locs.extend(e)
    return Response(locs)
