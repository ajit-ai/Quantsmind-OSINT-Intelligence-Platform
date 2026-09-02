from django.core.management.base import BaseCommand
from sources.models import Source, CollectionPolicy

SEEDS = [
    {"name": "Reuters World RSS", "slug": "reuters_rss", "source_type": "rss", "url": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"},
    {"name": "BBC World RSS", "slug": "bbc_rss", "source_type": "rss", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "GDELT Doc API", "slug": "gdelt_api", "source_type": "news_api", "url": "https://api.gdeltproject.org/api/v2/doc/doc"},
    {"name": "Example Scrape (quotes.toscrape)", "slug": "quotes_scrape", "source_type": "scrape", "url": "https://quotes.toscrape.com/"},
]

class Command(BaseCommand):
    def handle(self, *args, **opts):
        for s in SEEDS:
            src, created = Source.objects.get_or_create(slug=s["slug"], defaults=s)
            CollectionPolicy.objects.get_or_create(source=src, defaults={"respects_robots": True, "rate_limit_rps": 1.0})
            self.stdout.write(f"{'Created' if created else 'Exists'}: {src.name}")
