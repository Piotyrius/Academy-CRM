"""
Test settings for Academy CRM.
Uses SQLite in-memory database for faster tests.
"""
from .base import *
import os

DEBUG = True

# Use SQLite for testing (faster than PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster test setup
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable Redis for tests
USE_REDIS = False
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Disable Celery for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable Axes for tests
AXES_ENABLED = False

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# CORS
CORS_ALLOW_ALL_ORIGINS = True

