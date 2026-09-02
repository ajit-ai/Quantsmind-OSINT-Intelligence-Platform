from rest_framework.routers import DefaultRouter
from .views import WatchlistViewSet, AlertViewSet
router = DefaultRouter()
router.register("watchlists", WatchlistViewSet, basename="watchlist")
router.register("", AlertViewSet, basename="alert")
urlpatterns = router.urls
