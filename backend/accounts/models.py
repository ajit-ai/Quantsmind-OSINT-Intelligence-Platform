from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ANALYST = "analyst", "Analyst"
        VIEWER = "viewer", "Viewer"
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ANALYST)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def is_admin(self): return self.role == self.Role.ADMIN
    def is_analyst(self): return self.role in (self.Role.ADMIN, self.Role.ANALYST)
