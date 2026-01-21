from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    
    account_activated = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"User {self.pk}: {self.email} (Active: {self.is_active})"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users' 