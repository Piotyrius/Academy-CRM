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
    Get list of enabled modules for an organization based on their subscription.
    
    Args:
        organization: Organization instance
        
    Returns:
        list: List of enabled module names
    """
    if not organization:
        return []
    
    # Cache key for enabled modules
    cache_key = f'org_{organization.id}_enabled_modules'
    
    # Try to get from cache
    enabled_modules = cache.get(cache_key)
    if enabled_modules is not None:
        return enabled_modules
    
    # Get subscription
    try:
        subscription = organization.subscription
    except Subscription.DoesNotExist:
        # No subscription - return empty list or default modules
        enabled_modules = ['accounts']  # Always enable accounts
        cache.set(cache_key, enabled_modules, 300)  # Cache for 5 minutes
        return enabled_modules
    
    # Check if subscription is active
    if not subscription.is_active:
        enabled_modules = ['accounts']  # Only accounts if subscription inactive
        cache.set(cache_key, enabled_modules, 300)
        return enabled_modules
    
    # Get enabled features from plan
    plan_features = PlanFeature.objects.filter(
        plan=subscription.plan,
        enabled=True
    ).values_list('module_name', flat=True)
    
    enabled_modules = list(plan_features)
    
    # Always include accounts module
    if 'accounts' not in enabled_modules:
        enabled_modules.append('accounts')
    
    # Cache for 5 minutes
    cache.set(cache_key, enabled_modules, 300)
    
    return enabled_modules


def has_feature(organization, module_name):
    """
    Check if an organization has access to a specific module/feature.
    
    Args:
        organization: Organization instance
        module_name: Name of the module to check
        
    Returns:
        bool: True if organization has access to the module
    """
    if not organization:
        return False
    
    # Accounts is always enabled
    if module_name == 'accounts':
        return True
    
    # Get enabled modules
    enabled_modules = get_enabled_modules(organization)
    
    return module_name in enabled_modules


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

