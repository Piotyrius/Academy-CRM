"""
Custom middleware for Academy CRM.
"""
from django.core.exceptions import DisallowedHost
from django.utils.deprecation import MiddlewareMixin
from django.middleware.common import CommonMiddleware
from django.http import Http404
import os


class RenderHostMiddleware(MiddlewareMixin):
    """
    Middleware to automatically allow Render.com subdomains.
    This works around Django's ALLOWED_HOSTS limitation with wildcards.
    Must be placed before CommonMiddleware to intercept host validation.
    """
    def process_request(self, request):
        # Get host without triggering validation
        host_header = request.META.get('HTTP_HOST', '')
        if ':' in host_header:
            host = host_header.split(':')[0]
        else:
            host = host_header
        
        # Allow any .onrender.com subdomain by modifying ALLOWED_HOSTS before CommonMiddleware checks it
        if host and host.endswith('.onrender.com'):
            from django.conf import settings
            # Directly modify the ALLOWED_HOSTS list
            # Convert to list if it's a tuple (Django sometimes uses tuples)
            if isinstance(settings.ALLOWED_HOSTS, tuple):
                settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS)
            
            # Add host if not present
            if host not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS.append(host)
                # Also add without port variations
                if f'{host}:8000' not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(f'{host}:8000')
            
            # Patch request.get_host() to bypass validation for Render domains
            # This prevents DisallowedHost exception before CommonMiddleware runs
            original_get_host = request.get_host
            
            def patched_get_host():
                try:
                    return original_get_host()
                except DisallowedHost:
                    # If validation fails but it's a Render domain, return the host anyway
                    if host.endswith('.onrender.com'):
                        return host_header if host_header else host
                    raise
            
            request.get_host = patched_get_host
        
        return None


class RenderCommonMiddleware(CommonMiddleware):
    """
    Custom CommonMiddleware that allows Render.com subdomains.
    This overrides Django's host validation to automatically allow .onrender.com domains.
    """
    def process_request(self, request):
        # Get host from header directly to avoid validation
        host_header = request.META.get('HTTP_HOST', '')
        if ':' in host_header:
            host = host_header.split(':')[0]
        else:
            host = host_header
        
        # Allow Render domains before validation
        if host and host.endswith('.onrender.com'):
            from django.conf import settings
            # Ensure host is in ALLOWED_HOSTS
            if isinstance(settings.ALLOWED_HOSTS, tuple):
                settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS)
            if host not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS.append(host)
            
            # Also patch get_host() here as a backup
            original_get_host = request.get_host
            def patched_get_host():
                try:
                    return original_get_host()
                except DisallowedHost:
                    if host.endswith('.onrender.com'):
                        return host_header if host_header else host
                    raise
            request.get_host = patched_get_host
        
        # Call parent CommonMiddleware
        try:
            return super().process_request(request)
        except DisallowedHost as e:
            # Catch DisallowedHost and allow Render domains
            if host and host.endswith('.onrender.com'):
                # Add to ALLOWED_HOSTS and retry
                from django.conf import settings
                if isinstance(settings.ALLOWED_HOSTS, tuple):
                    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS)
                if host not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(host)
                # Retry the parent method
                return super().process_request(request)
            raise

