from django.urls import path
from .views import search, trends, geo
urlpatterns = [path("search/", search), path("trends/", trends), path("geo/", geo)]
