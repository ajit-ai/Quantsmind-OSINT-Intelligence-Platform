from django.core.management.base import BaseCommand
from sources.models import Source
from collectors.tasks import poll_source

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--source", help="slug of source to poll")
    def handle(self, *args, **opts):
        slug = opts.get("source")
        qs = Source.objects.filter(slug=slug) if slug else Source.objects.filter(is_active=True)
        for s in qs:
            poll_source.delay(str(s.id))
            self.stdout.write(f"Queued {s.slug}")
