from django.core.management.base import BaseCommand
import time
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    def handle(self, *a, **o):
        self.stdout.write("Waiting for DB...")
        for i in range(30):
            try:
                connections['default'].cursor()
                self.stdout.write(self.style.SUCCESS("DB ready"))
                return
            except OperationalError:
                self.stdout.write(f"DB not ready {i}/30, retry 1s")
                time.sleep(1)
        self.stdout.write(self.style.ERROR("DB not available"))
