"""
Mixins for ViewSets to handle organization filtering and feature checks.
"""
from rest_framework.response import Response
from rest_framework import status
from .utils import has_feature


class OrganizationFilterMixin:
    """
    Mixin to filter queryset by organization.
    Add this to ViewSets that need organization-based filtering.
    """
    
    def get_queryset(self):
        """Filter queryset by organization."""
        queryset = super().get_queryset()
        
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
    
    def dispatch(self, request, *args, **kwargs):
        """Check feature access before processing request."""
        if self.required_feature:
            # Get organization from request
            organization = getattr(request, 'organization', None)
            
            # If no organization in request, try to get from user
            if not organization and hasattr(request, 'user') and request.user.is_authenticated:
                if hasattr(request.user, 'organization'):
                    organization = request.user.organization
            
            # Check if organization has access to this feature
            if not has_feature(organization, self.required_feature):
                return Response(
                    {
                        'error': 'Feature not available',
                        'message': f'The {self.required_feature} module is not included in your subscription plan.',
                        'module': self.required_feature,
                        'upgrade_required': True,
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().dispatch(request, *args, **kwargs)


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

