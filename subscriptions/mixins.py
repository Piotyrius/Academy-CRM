"""
Mixins for ViewSets to handle organization filtering and feature checks.
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from .utils import has_feature

class OrganizationFilterMixin:
    """
    Mixin to filter queryset by organization.
    Add this to ViewSets that need organization-based filtering.
    
    Admin users bypass organization filtering and can see all records.
    """
    
    def get_queryset(self):
        """Filter queryset by organization."""
        queryset = super().get_queryset()
        
        # Admin users bypass organization filtering - they can see all records
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if getattr(self.request.user, 'is_admin', False):
                return queryset  # Admins see everything
        
        # Get organization from request
        organization = getattr(self.request, 'organization', None)
        
        # If no organization in request, try to get from user
        if not organization and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if hasattr(self.request.user, 'organization'):
                organization = self.request.user.organization
        
        # Filter by organization if model has organization field
        if organization and hasattr(queryset.model, 'organization'):
            queryset = queryset.filter(organization=organization)
        
        return queryset


class FeatureRequiredMixin:
    """
    Mixin to require a specific feature/module for a ViewSet.
    
    Usage:
        class MyViewSet(FeatureRequiredMixin, viewsets.ModelViewSet):
            required_feature = 'attendance'  # Module name required
    """
    required_feature = None  # Override in subclass
    
    def initial(self, request, *args, **kwargs):
        """Check feature access before processing request."""
        super().initial(request, *args, **kwargs)
        
        if self.required_feature:
            # Admin users bypass feature checks - they have access to all features
            if hasattr(request, 'user') and request.user.is_authenticated:
                if getattr(request.user, 'is_admin', False):
                    return  # Admin users have access to all features
            
            # Get organization from request
            organization = getattr(request, 'organization', None)
            
            # If no organization in request, try to get from user (user's org takes precedence)
            if hasattr(request, 'user') and request.user.is_authenticated:
                if hasattr(request.user, 'organization') and request.user.organization:
                    organization = request.user.organization
            
            # Check if organization has access to this feature
            if not has_feature(organization, self.required_feature):
                raise PermissionDenied(
                    detail={
                        'error': 'Feature not available',
                        'message': f'The {self.required_feature} module is not included in your subscription plan.',
                        'module': self.required_feature,
                        'upgrade_required': True,
                    }
                )


class OrganizationAutoSetMixin:
    """
    Mixin to automatically set organization when creating objects.
    Add this to ViewSets that need automatic organization assignment.
    """
    
    def perform_create(self, serializer):
        """Automatically set organization when creating objects."""
        # Get organization from request
        organization = getattr(self.request, 'organization', None)
        
        # If no organization in request, try to get from user
        if not organization and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if hasattr(self.request.user, 'organization'):
                organization = self.request.user.organization
        
        # Set organization if serializer has organization field
        if organization and 'organization' in serializer.fields:
            serializer.save(organization=organization)
        else:
            serializer.save()

