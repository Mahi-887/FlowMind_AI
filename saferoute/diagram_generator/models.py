import os
import random
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils import timezone
from datetime import timedelta


# ─────────────────────────────────────────────────────────────
#  Custom User Manager
# ─────────────────────────────────────────────────────────────
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra):
        if not phone_number:
            raise ValueError('Phone number is required.')
        user = self.model(phone_number=phone_number, **extra)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        user = self.model(phone_number=phone_number, **extra)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


# ─────────────────────────────────────────────────────────────
#  Custom User Model
# ─────────────────────────────────────────────────────────────
class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.phone_number


# ─────────────────────────────────────────────────────────────
#  OTP Session
# ─────────────────────────────────────────────────────────────
class OTPSession(models.Model):
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """OTP is valid for 5 minutes."""
        return timezone.now() < self.created_at + timedelta(minutes=5)

    @classmethod
    def generate_otp(cls, phone_number):
        """Delete old OTPs for this number and create a fresh one."""
        cls.objects.filter(phone_number=phone_number).delete()
        otp = str(random.randint(1000, 9999))
        instance = cls.objects.create(phone_number=phone_number, otp=otp)
        return instance

    class Meta:
        verbose_name = 'OTP Session'

    def __str__(self):
        return f"{self.phone_number} → {self.otp}"


# ─────────────────────────────────────────────────────────────
#  Diagram History
# ─────────────────────────────────────────────────────────────
DIAGRAM_TYPES = [
    ('flowchart', 'Flowchart'),
    ('sequence', 'Sequence Diagram'),
    ('mindmap', 'Mindmap'),
]


class DiagramHistory(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='diagrams',
        null=True, blank=True,
    )
    prompt = models.TextField()
    mermaid_code = models.TextField()
    diagram_type = models.CharField(
        max_length=20, choices=DIAGRAM_TYPES, default='flowchart'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_diagram_type_display()}] {self.prompt[:50]}"
