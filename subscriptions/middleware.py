"""
Tenant middleware for multi-tenant support.
Identifies organization from request and adds it to request context.
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import Http404
from django.db import OperationalError, ProgrammingError
from django.core.exceptions import ValidationError
from .models import Organization

class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to identify organization from request and add to request context.
    
    Supports multiple identification methods:
    1. Subdomain-based: academy1.yourdomain.com -> organization with domain='academy1'
    2. Header-based: X-Organization-ID header
    3. Query parameter: ?org_id=xxx (for testing/API)
    
    Gracefully handles missing database tables (e.g., before migrations run).
    """
    
    def process_request(self, request):
        """Process request to identify organization."""
        organization = None
        
        # Check if Organization table exists (for graceful handling before migrations)
        # This prevents errors during initial deployment before migrations run
        try:
            # Quick check: try to access the model's table
            # If table doesn't exist, we'll catch the exception and skip organization lookup
            Organization._meta.db_table
        except (AttributeError, Exception):
            # Model not properly configured or table doesn't exist
            request.organization = None
            return None
        
        # Import settings lazily to avoid circular imports at module import time
        from django.conf import settings
        
        # Try to query the database, but handle missing tables gracefully
        try:
            # Method 1: Subdomain-based identification
            host = request.get_host().split(':')[0]  # Remove port if present
            subdomain = self._extract_subdomain(host)
            
            if subdomain:
                try:
                    organization = Organization.objects.get(domain=subdomain, status__in=['ACTIVE', 'TRIAL'])
                except Organization.DoesNotExist:
                    pass
                except (OperationalError, ProgrammingError) as e:
                    # Table doesn't exist yet (migrations not run)
                    # Log and continue without organization
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Organization table not found (migrations may not be run): {e}")
                    request.organization = None
                    return None
            
            # Method 2: Header-based identification (for API clients)
            if not organization:
                org_id = request.headers.get('X-Organization-ID')
                if org_id:
                    try:
                        organization = Organization.objects.get(id=org_id, status__in=['ACTIVE', 'TRIAL'])
                    except (Organization.DoesNotExist, ValueError, ValidationError):
                        pass
                    except (OperationalError, ProgrammingError):
                        request.organization = None
                        return None
            
            # Method 3: Query parameter (primarily for testing/development or superusers)
            # To avoid tenant spoofing in production, only honor ?org_id= when:
            #   - DEBUG is True (local/dev), OR
            #   - the requesting user is an authenticated superuser.
            if not organization:
                can_use_query_param = False
                user = getattr(request, 'user', None)
                if getattr(settings, 'DEBUG', False):
                    can_use_query_param = True
                elif user is not None and getattr(user, 'is_authenticated', False) and getattr(user, 'is_superuser', False):
                    can_use_query_param = True
                
                if can_use_query_param:
                    org_id = request.GET.get('org_id')
                    if org_id:
                        try:
                            organization = Organization.objects.get(id=org_id, status__in=['ACTIVE', 'TRIAL'])
                        except (Organization.DoesNotExist, ValueError, ValidationError):
                            pass
                        except (OperationalError, ProgrammingError):
                            request.organization = None
                            return None
            
            # Method 4: User's organization (if authenticated)
            if not organization and hasattr(request, 'user') and request.user.is_authenticated:
                if hasattr(request.user, 'organization'):
                    organization = request.user.organization
            
            # For superusers or if no organization found, try to get default
            if not organization:
                # Try to get a default organization (first active one)
                # This is a fallback - in production you might want to require organization
                try:
                    organization = Organization.objects.filter(status__in=['ACTIVE', 'TRIAL']).first()
                except (OperationalError, ProgrammingError):
                    organization = None
        
        except (OperationalError, ProgrammingError) as e:
            # Database table doesn't exist yet (migrations not run)
            # This is expected during initial deployment
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Organization table not found (migrations may not be run): {e}")
            organization = None
        
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

