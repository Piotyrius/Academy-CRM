"""
Custom middleware for Academy CRM.
"""
from django.core.exceptions import DisallowedHost
from django.utils.deprecation import MiddlewareMixin
from django.http import Http404


class RenderHostMiddleware(MiddlewareMixin):
    """
    Middleware to automatically allow Render.com subdomains.
    This works around Django's ALLOWED_HOSTS limitation with wildcards.
    Must be placed before CommonMiddleware to intercept host validation.
    """
    def process_request(self, request):
        host = request.get_host().split(':')[0]  # Remove port if present
        
        # Allow any .onrender.com subdomain
        if host.endswith('.onrender.com'):
            from django.conf import settings
            # Add to ALLOWED_HOSTS if not already present
            # Use list() to ensure we're modifying the actual list, not a copy
            if host not in settings.ALLOWED_HOSTS:
                # Modify the actual ALLOWED_HOSTS list
                settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + [host]
        
        return None

