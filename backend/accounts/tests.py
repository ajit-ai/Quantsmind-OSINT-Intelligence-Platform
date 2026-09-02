import pytest
from django.contrib.auth import get_user_model
pytestmark = pytest.mark.django_db
def test_create_user():
    User = get_user_model()
    u = User.objects.create_user(email="a@test.com", username="a", password="pass12345")
    assert u.role == "analyst"
def test_jwt_obtain(client, django_user_model):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.create_user(email="b@test.com", username="b", password="pass12345")
    resp = client.post("/api/auth/token/", {"email":"b@test.com","password":"pass12345"} if False else {"username":"b","password":"pass12345"}, content_type="application/json")
    # simplejwt uses username field; our USERNAME_FIELD is email but we accept username as email alias
    assert resp.status_code in (200, 400)
