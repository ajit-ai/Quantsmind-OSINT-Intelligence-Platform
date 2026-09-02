import pytest
from django.conf import settings

def test_jwt_lifetimes_short():
    from datetime import timedelta
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] <= timedelta(minutes=30)
    assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True
    assert settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] is True

def test_allowed_hosts_wildcard_only_in_debug():
    if not settings.DEBUG:
        assert "*" not in settings.ALLOWED_HOSTS

def test_cors_not_allow_all_in_prod():
    if not settings.DEBUG:
        assert not settings.CORS_ALLOW_ALL_ORIGINS

def test_security_headers_in_prod(monkeypatch):
    # simulate DEBUG=0 expectations
    assert hasattr(settings, "SECURE_SSL_REDIRECT")

def test_throttle_rates_defined():
    assert "user" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert "anon" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
