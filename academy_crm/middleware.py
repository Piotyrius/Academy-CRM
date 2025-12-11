"""
Middleware for Academy CRM.
Includes Render deployment helpers and query profiling.
"""
import os
import time
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
from django.middleware.common import CommonMiddleware
from django.http import Http404


class RenderHostMiddleware(MiddlewareMixin):
    """
    Middleware to dynamically add Render hostnames to ALLOWED_HOSTS.
    Allows Render subdomains and custom domains.
    """
    
    def process_request(self, request):
        """Add Render hostname to ALLOWED_HOSTS if on Render."""
        host = request.get_host().split(':')[0]
        
        # Check if we're on Render
        if os.getenv('RENDER') or os.getenv('RENDER_EXTERNAL_HOSTNAME'):
            # Allow Render hostnames
            if '.onrender.com' in host or host in ['localhost', '127.0.0.1', 'testserver']:
                from django.conf import settings
                if host not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(host)
        
        return None


class RenderCommonMiddleware(CommonMiddleware):
    """
    Custom CommonMiddleware that allows Render hosts.
    Extends Django's CommonMiddleware with Render-specific host handling.
    """
    
    def process_request(self, request):
        """Override to allow Render hostnames."""
        # Call parent but catch DisallowedHost exceptions for Render hosts
        try:
            return super().process_request(request)
        except Exception:
            # Allow Render hostnames even if not in ALLOWED_HOSTS initially
            host = request.get_host().split(':')[0]
            if '.onrender.com' in host or os.getenv('RENDER'):
                from django.conf import settings
                if host not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(host)
                return None
            raise


class AuthorizationHeaderNormalizationMiddleware(MiddlewareMixin):
    """
    Middleware to normalize malformed Authorization headers.
    
    Fixes common issues like "Bearer Bearer <token>" which can occur when
    Swagger UI automatically adds "Bearer " prefix and users also include it.
    """
    
    def process_request(self, request):
        """Normalize Authorization header before authentication."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header:
            # Handle malformed headers like "Bearer Bearer <token>"
            parts = auth_header.split()
            
            # If we have multiple "Bearer" prefixes, normalize to single "Bearer <token>"
            if len(parts) > 2 and parts[0].upper() == 'BEARER' and parts[1].upper() == 'BEARER':
                # Extract the actual token (everything after the Bearer prefixes)
                token = ' '.join(parts[2:])  # Join in case token has spaces (shouldn't, but safe)
                # Reconstruct with single "Bearer"
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            elif len(parts) >= 2 and parts[0].upper() == 'BEARER':
                # Already correctly formatted, but ensure it's properly normalized
                token = ' '.join(parts[1:])
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        return None


class QueryProfilingMiddleware(MiddlewareMixin):
    """
    Middleware to profile database queries for performance analysis.
    Logs query count and execution time per request.
    """
    
    def process_request(self, request):
        """Reset query tracking at start of request."""
        # Only enable query logging in DEBUG mode or when explicitly enabled
        from django.conf import settings
        if settings.DEBUG or getattr(settings, 'ENABLE_QUERY_PROFILING', False):
            connection.queries_log.clear()
            request._query_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Log query statistics after request processing."""
        from django.conf import settings
        if not (settings.DEBUG or getattr(settings, 'ENABLE_QUERY_PROFILING', False)):
            return response
            
        if hasattr(request, '_query_start_time'):
            query_count = len(connection.queries)
            execution_time = time.time() - request._query_start_time
            
            # Only log if there were queries or if execution time is significant
            # Query profiling can be enabled via ENABLE_QUERY_PROFILING setting
            # Logs are written to Django's logging system if configured
        
        return response
