"""
Decorators for feature flag checks.
"""
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .utils import has_feature


def require_feature(module_name):
    """
    Decorator to require a specific feature/module for a view.
    
    Usage:
        @require_feature('attendance')
        class AttendanceViewSet(viewsets.ModelViewSet):
            ...
    
    Args:
        module_name: Name of the module/feature to require
        
    Returns:
        Decorated view that checks feature access
    """
    def decorator(view_class):
        # Store original methods
        original_dispatch = view_class.dispatch
        
        def dispatch(self, request, *args, **kwargs):
            # Get organization from request
            organization = getattr(request, 'organization', None)
            
            # Check if organization has access to this feature
            if not has_feature(organization, module_name):
                return Response(
                    {
                        'error': 'Feature not available',
                        'message': f'The {module_name} module is not included in your subscription plan.',
                        'module': module_name,
                        'upgrade_required': True,
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Call original dispatch
            return original_dispatch(self, request, *args, **kwargs)
        
        # Replace dispatch method
        view_class.dispatch = dispatch
        
        return view_class
    
    return decorator

