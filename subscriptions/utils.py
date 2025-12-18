"""
Feature flag utilities for checking module access based on subscriptions.
"""
from django.core.cache import cache
from django.utils import timezone
from .models import Organization, Subscription, PlanFeature, SubscriptionStatus


# Define all available modules
AVAILABLE_MODULES = [
    'accounts',      # User management (always enabled)
    'catalog',      # Programs, courses, cohorts
    'admissions',   # Applications, enrollments
    'attendance',   # Attendance tracking
    'assessment',   # Assessments, grades
    'certificates', # Certificate management
    'documents',    # Document management
    'timekeeping',  # Timesheets, payroll
    'gallery',      # Gallery works
    'reporting',    # Reports and exports
    'notifications', # Notifications
    'ops',          # Operations
]


def get_enabled_modules(organization):
    """
    Get list of enabled modules for an organization.

    The subscription gating layer has been disabled, so we now always return
    the full list of AVAILABLE_MODULES. This prevents feature checks from
    blocking access when no subscription/plan is configured.
    """
    # Previously this depended on Subscription / PlanFeature records.
    # We intentionally ignore subscription state now.
    return list(AVAILABLE_MODULES)


def has_feature(organization, module_name):
    """
    Check if an organization has access to a specific module/feature.

    Subscription-based feature gating has been turned off, so this now always
    returns True for known modules. This ensures FeatureRequiredMixin never
    blocks access due to missing subscription data.
    """
    # If we ever add completely unknown module names, we can still allow them;
    # the goal is to avoid gating on subscription plans entirely.
    return True


def clear_feature_cache(organization):
    """
    Clear feature flag cache for an organization.
    Useful when subscription changes.
    
    Args:
        organization: Organization instance
    """
    if organization:
        cache_key = f'org_{organization.id}_enabled_modules'
        cache.delete(cache_key)


def get_subscription_status(organization):
    """
    Get subscription status information for an organization.
    
    Args:
        organization: Organization instance
        
    Returns:
        dict: Subscription status information
    """
    if not organization:
        return {
            'has_subscription': False,
            'is_active': False,
            'status': 'NO_SUBSCRIPTION',
            'plan_name': None,
            'enabled_modules': ['accounts'],
        }
    
    try:
        subscription = organization.subscription
    except Subscription.DoesNotExist:
        return {
            'has_subscription': False,
            'is_active': False,
            'status': 'NO_SUBSCRIPTION',
            'plan_name': None,
            'enabled_modules': ['accounts'],
        }
    
    enabled_modules = get_enabled_modules(organization)
    
    return {
        'has_subscription': True,
        'is_active': subscription.is_active,
        'status': subscription.status,
        'plan_name': subscription.plan.name,
        'plan_id': str(subscription.plan.id),
        'enabled_modules': enabled_modules,
        'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
        'trial_ends_at': subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
    }

