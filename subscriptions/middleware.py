"""
Tenant middleware for multi-tenant support.
Identifies organization from request and adds it to request context.
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import Http404
from .models import Organization


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to identify organization from request and add to request context.
    
    Supports multiple identification methods:
    1. Subdomain-based: academy1.yourdomain.com -> organization with domain='academy1'
    2. Header-based: X-Organization-ID header
    3. Query parameter: ?org_id=xxx (for testing/API)
    """
    
    def process_request(self, request):
        """Process request to identify organization."""
        organization = None
        
        # Method 1: Subdomain-based identification
        host = request.get_host().split(':')[0]  # Remove port if present
        subdomain = self._extract_subdomain(host)
        
        if subdomain:
            try:
                organization = Organization.objects.get(domain=subdomain, status__in=['ACTIVE', 'TRIAL'])
            except Organization.DoesNotExist:
                pass
        
        # Method 2: Header-based identification (for API clients)
        if not organization:
            org_id = request.headers.get('X-Organization-ID')
            if org_id:
                try:
                    organization = Organization.objects.get(id=org_id, status__in=['ACTIVE', 'TRIAL'])
                except (Organization.DoesNotExist, ValueError):
                    pass
        
        # Method 3: Query parameter (for testing/development)
        if not organization:
            org_id = request.GET.get('org_id')
            if org_id:
                try:
                    organization = Organization.objects.get(id=org_id, status__in=['ACTIVE', 'TRIAL'])
                except (Organization.DoesNotExist, ValueError):
                    pass
        
        # Method 4: User's organization (if authenticated)
        if not organization and hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'organization'):
                organization = request.user.organization
        
        # For superusers or if no organization found, try to get default
        if not organization:
            # Try to get a default organization (first active one)
            # This is a fallback - in production you might want to require organization
            organization = Organization.objects.filter(status__in=['ACTIVE', 'TRIAL']).first()
        
        # Add organization to request
        request.organization = organization
        
        return None
    
    def _extract_subdomain(self, host):
        """
        Extract subdomain from host.
        
        Examples:
        - academy1.example.com -> academy1
        - academy1.onrender.com -> academy1
        - localhost -> None
        - example.com -> None
        """
        parts = host.split('.')
        
        # If we have at least 3 parts, the first is likely the subdomain
        # localhost, 127.0.0.1, or single-word domains don't have subdomains
        if len(parts) >= 3:
            # Check if it's a known TLD pattern (e.g., .onrender.com, .com, .org)
            # For now, assume first part is subdomain if we have 3+ parts
            return parts[0]
        
        return None

