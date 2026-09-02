import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("osint")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
# Beat schedule for collectors
app.conf.beat_schedule = {
    "poll-rss-every-15m": {"task": "collectors.tasks.poll_all_sources", "schedule": 900},
    "enrich-pending-every-2m": {"task": "processing.tasks.enrich_pending", "schedule": 120},
}
