"""
Subscriptions app for Academy CRM.
Handles multi-tenant organization management, subscription plans, and feature flags.
"""
from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    """Configuration for subscriptions app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subscriptions'
    verbose_name = 'Subscriptions'

