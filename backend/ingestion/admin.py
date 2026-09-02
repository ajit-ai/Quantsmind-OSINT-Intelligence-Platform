from django.contrib import admin
from .models import CollectedDocument, RawArtifact
admin.site.register(CollectedDocument)
admin.site.register(RawArtifact)
