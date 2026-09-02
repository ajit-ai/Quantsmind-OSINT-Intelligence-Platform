from django.core.management.base import BaseCommand
from django.conf import settings
class Command(BaseCommand):
    def handle(self, *args, **opts):
        try:
            import boto3
            s3 = boto3.client("s3", endpoint_url=settings.AWS_S3_ENDPOINT_URL, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, region_name=settings.AWS_S3_REGION_NAME, use_ssl=settings.AWS_S3_USE_SSL)
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            try:
                s3.create_bucket(Bucket=bucket)
                self.stdout.write(f"Created bucket {bucket}")
            except s3.exceptions.BucketAlreadyOwnedByYou:
                self.stdout.write(f"Bucket {bucket} already exists")
            except Exception as e:
                if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
                    self.stdout.write(f"Bucket {bucket} exists")
                else: self.stdout.write(f"Bucket check: {e}")
        except Exception as e:
            self.stdout.write(f"Skipped bucket creation: {e}")
