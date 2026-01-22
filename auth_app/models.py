from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    """Manager für CustomUser ohne username"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email ist erforderlich')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('account_activated', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser muss is_staff=True haben')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser muss is_superuser=True haben')
        
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    account_activated = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    username = None  # ← Username-Feld entfernen!
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()  # ← Custom Manager verwenden!

    def __str__(self):
        return f"User {self.pk}: {self.email} (Active: {self.is_active})"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'