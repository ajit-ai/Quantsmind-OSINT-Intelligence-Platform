import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("osint")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Hardened: acks_late + prefetch 1 + per-source jitter
from celery.schedules import crontab

app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    broker_transport_options={"visibility_timeout": 3600},
    task_time_limit=300,
    task_soft_time_limit=240,
)

app.conf.beat_schedule = {
    "poll-rss-every-15m": {"task": "collectors.tasks.poll_all_sources", "schedule": 900},
    "enrich-pending-every-2m": {"task": "processing.tasks.enrich_pending", "schedule": 120, "args": (20,)},
    "reindex-failed-every-10m": {"task": "processing.tasks.reindex_failed", "schedule": 600},
    "requeue-dlq-every-30m": {"task": "collectors.tasks.requeue_dlq", "schedule": 1800},
}
# Optional per-source schedules can be added dynamically via django-celery-beat
