from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", "") == "admin"

class IsAnalyst(BasePermission):
    # Analyst = admin OR analyst
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", "") in ("admin", "analyst")

class IsViewerReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(request.user, "role", "") in ("admin", "analyst")

# Object-level: analysts can only mutate their own watchlists/alerts
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "role", "") == "admin":
            return True
        # assume obj has user or watchlist.user
        owner_id = getattr(obj, "user_id", None)
        if owner_id is None and hasattr(obj, "watchlist"):
            owner_id = getattr(obj.watchlist, "user_id", None)
        if owner_id is None and hasattr(obj, "rule"):
            owner_id = getattr(getattr(obj.rule, "watchlist", None), "user_id", None)
        return owner_id == getattr(request.user, "id", None)
