from .models import AuditLog
class AuditMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and request.user.is_authenticated and request.method in ("POST","PUT","PATCH","DELETE","GET"):
            # only log state-changing + sensitive reads; keep lightweight
            if request.method != "GET" or "export" in request.path:
                try:
                    AuditLog.objects.create(
                        user=request.user, action=f"{request.method} {request.path}",
                        ip=request.META.get("REMOTE_ADDR"), user_agent=request.META.get("HTTP_USER_AGENT","")[:500],
                        payload={"query": dict(request.GET), "status": response.status_code}
                    )
                except: pass
        return response
