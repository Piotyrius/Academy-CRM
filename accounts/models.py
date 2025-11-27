"""
Accounts models for Academy CRM.
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from fernet_fields import EncryptedCharField


class Role(models.TextChoices):
    """User role choices."""
    ADMIN = 'ADMIN', _('Admin')
    LECTURER = 'LECTURER', _('Lecturer')
    STUDENT = 'STUDENT', _('Student')


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def create_user(self, email, password=None, organization=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Set organization if provided
        if organization:
            extra_fields['organization'] = organization
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Role.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with UUID primary key and role-based access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text=_('User role in the system')
    )
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    mfa_enabled = models.BooleanField(default=False, help_text=_('Multi-factor authentication enabled'))
    mfa_secret = EncryptedCharField(max_length=32, blank=True, help_text=_('MFA secret key'))
    
    # Organization/tenant relationship (nullable for backward compatibility during migration)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        help_text=_('Organization this user belongs to')
    )
    
    # Override username to use email
    username = None
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['organization']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.role == Role.ADMIN or self.is_superuser
    
    @property
    def is_lecturer(self):
        """Check if user is lecturer."""
        return self.role == Role.LECTURER
    
    @property
    def is_student(self):
        """Check if user is student."""
        return self.role == Role.STUDENT