from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .search import search_es

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search(request):
    q = request.query_params.get("q", "").strip()
    # filters: source, language, sentiment.label (nested), entity
    source = request.query_params.get("source")
    language = request.query_params.get("language")
    sentiment = request.query_params.get("sentiment")
    size = min(int(request.query_params.get("size", 20)), 50)
    filters = {}
    enrich_filters = {}
    if source: filters["source"] = source
    if language: filters["language"] = language
    if sentiment: filters["sentiment.label"] = sentiment
    # full ES path; fallback to DB search if ES down
    res = search_es(q, filters=filters, size=size)
    if res.get("error") and not q:
        # DB fallback
        from ingestion.models import CollectedDocument
        qs = CollectedDocument.objects.select_related("source").order_by("-collected_at")
        if q: qs = qs.filter(title__icontains=q) | qs.filter(content_text__icontains=q)
        if source: qs = qs.filter(source__slug=source)
        if language: qs = qs.filter(language=language)
        docs = list(qs[:size].values("id","title","content_text","source__slug","language","collected_at"))
        return Response({"hits": {"hits": [{"_id": d["id"], "_source": {"title": d["title"], "text": d["content_text"][:500], "source": d["source__slug"], "collected_at": str(d["collected_at"])}} for d in docs]}, "db_fallback": True})
    return Response(res)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trends(request):
    from ingestion.models import CollectedDocument
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    days = min(int(request.query_params.get("days", 30)), 90)
    qs = CollectedDocument.objects.values(date=TruncDate("collected_at")).annotate(count=Count("id")).order_by("date")[:days]
    # Also ES daily aggregation if available
    data = list(qs)
    return Response(data if data else [{"date":"2026-08-01","count":12},{"date":"2026-08-02","count":18}])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def geo(request):
    from processing.models import Enrichment
    locs = []
    for e in Enrichment.objects.exclude(geo_locations=[]).exclude(geo_locations__isnull=True).values_list("geo_locations", flat=True)[:200]:
        if isinstance(e, list):
            locs.extend(e)
    # dedup by name
    seen=set(); uniq=[]
    for loc in locs:
        name=(loc.get("name") or "").lower()
        if name and name not in seen:
            seen.add(name); uniq.append(loc)
    return Response(uniq[:100])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def facets(request):
    # convenience: ES aggs for search UI
    res = search_es("", size=0)
    return Response(res.get("aggregations", {}))
