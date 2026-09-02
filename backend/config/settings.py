import os
import environ
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR.parent / ".env", overwrite=False)
environ.Env.read_env(BASE_DIR.parent / ".env.example", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret-key-change-me-please-32chars-rotate-in-prod")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "channels",
    "accounts",
    "sources",
    "ingestion",
    "processing",
    "alerts",
    "audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "audit.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database - parse DATABASE_URL or use individual vars
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="osint"),
        "USER": env("POSTGRES_USER", default="osint"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="osint_password"),
        "HOST": env("POSTGRES_HOST", default="postgres"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}
_db_url = env("DATABASE_URL", default="")
if _db_url:
    import urllib.parse as _url
    u = _url.urlparse(_db_url)
    DATABASES["default"].update({
        "NAME": u.path.lstrip("/"),
        "USER": u.username,
        "PASSWORD": u.password,
        "HOST": u.hostname or "postgres",
        "PORT": u.port or 5432,
    })

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend", "rest_framework.filters.SearchFilter", "rest_framework.filters.OrderingFilter"),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle", "rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "anon": "100/day", "burst": "60/min"},
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

from datetime import timedelta as _td
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": _td(minutes=env.int("JWT_ACCESS_TTL_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": _td(days=env.int("JWT_REFRESH_TTL_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "OSINT Platform API",
    "DESCRIPTION": "Secure OSINT Intelligence API — RBAC, audit, real-time alerts. See docs/high-level-design.md",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [{"name":"sources","description":"Collection sources & policies"},{"name":"documents","description":"Ingested docs + S3 artifacts"},{"name":"processing","description":"NLP search/trends/geo"},{"name":"alerts","description":"Watchlists & alerts (WS)"},{"name":"audit","description":"Admin audit log"}],
}

# CORS — allow frontend origins via env
_cors_origins = env.list("CORS_ALLOWED_ORIGINS", default=[])
if _cors_origins:
    CORS_ALLOWED_ORIGINS = _cors_origins
    CORS_ALLOW_ALL_ORIGINS = False
else:
    CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = ["Authorization","Content-Type","X-CSRFToken"]

# Channels — JWT via query ?token= or Authorization header (see alerts/middleware)
CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [env("REDIS_URL", default="redis://redis:6379/0")]}}}

# Celery — hardened: acks_late, prefetch, DLQ, result expiry
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_RESULT_EXPIRES = 3600
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600}

# S3 / MinIO
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="minioadmin")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="minioadmin")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="osint-raw")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="http://minio:9000")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_USE_SSL = env.bool("AWS_S3_USE_SSL", default=False)
AWS_DEFAULT_ACL = None
AWS_S3_VERIFY = env.bool("AWS_S3_VERIFY", default=False)

ELASTICSEARCH_URL = env("ELASTICSEARCH_URL", default="http://elasticsearch:9200")

# Neo4j optional (entity graph)
NEO4J_URL = env("NEO4J_URL", default="")
NEO4J_AUTH = env("NEO4J_AUTH", default="neo4j/password")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security headers — TLS, HSTS, CSP friendly defaults
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    # trust X-Forwarded-Proto from nginx/ingress
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

# Logging — structured, per-layer
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "pythonjsonlogger.jsonlogger.JsonFormatter", "format": "%(asctime)s %(levelname)s %(name)s %(message)s"} if False else {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json" if False else "console"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.request": {"level": "WARNING", "propagate": True}, "celery": {"level": "INFO"}, "collectors": {"level": "INFO"}},
}
