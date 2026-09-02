from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView

def health(request):
    # Liveness + dependency checks (DB/Redis/ES/S3 best-effort)
    checks = {"status":"ok"}
    try:
        from django.db import connection
        with connection.cursor() as cur: cur.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as e: checks["db"] = f"error: {e}"
    return JsonResponse(checks)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/health/", health, name="api-health"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("api/auth/logout/", TokenBlacklistView.as_view(), name="logout"),
    path("api/auth/", include("accounts.urls")),
    path("api/sources/", include("sources.urls")),
    path("api/documents/", include("ingestion.urls")),
    path("api/alerts/", include("alerts.urls")),
    path("api/audit/", include("audit.urls")),
    path("api/processing/", include("processing.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
