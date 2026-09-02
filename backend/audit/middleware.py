import logging
from .models import AuditLog
logger = logging.getLogger("audit")

SENSITIVE_PATHS = ("/api/auth/token", "/admin", "/api/audit")

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            # log all state-changing + sensitive reads + all admin/audit
            should = False
            path = request.path or ""
            if path.startswith("/api/"):
                if request.method in ("POST","PUT","PATCH","DELETE"):
                    should = True
                elif "export" in path or path.startswith("/api/audit") or path.startswith("/admin"):
                    should = True
                elif request.method == "GET" and request.user.is_authenticated and request.user.role == "admin":
                    # optional: log admin reads
                    should = path.startswith("/api/")
            if should and not any(path.startswith(p) for p in ("/api/docs","/api/schema","/api/redoc","/health")):
                # avoid logging health/docs noise
                user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
                # truncate payload to avoid PII explosion
                payload = {}
                if request.method in ("POST","PUT","PATCH"):
                    try:
                        # don't log passwords
                        body = dict(request.POST) if request.POST else {}
                        if request.content_type == "application/json":
                            import json
                            try: body = json.loads(request.body.decode()[:2000] or "{}")
                            except Exception: body = {}
                            for k in list(body.keys()):
                                if "password" in k.lower() or "secret" in k.lower():
                                    body[k] = "***"
                        payload = {"body_keys": list(body.keys())[:10], "content_type": request.content_type}
                    except Exception:
                        payload = {}
                try:
                    AuditLog.objects.create(
                        user=user,
                        action=f"{request.method} {path}",
                        resource_type=path.split("/")[2] if len(path.split("/"))>2 else path,
                        resource_id=request.GET.get("id","")[:100] if request.method=="GET" else "",
                        ip=request.META.get("HTTP_X_FORWARDED_FOR","").split(",")[0].strip() or request.META.get("REMOTE_ADDR"),
                        user_agent=(request.META.get("HTTP_USER_AGENT","") or "")[:500],
                        payload={"query": dict(request.GET) if len(request.GET)<20 else {"truncated": True}, "status": response.status_code, **payload},
                    )
                except Exception as e:
                    logger.warning(f"audit log failed: {e}")
        except Exception as e:
            logger.debug(f"audit middleware error: {e}")
        return response
