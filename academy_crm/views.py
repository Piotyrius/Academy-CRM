"""
Custom views for Academy CRM.
"""
from drf_spectacular.views import SpectacularAPIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class CustomSpectacularAPIView(SpectacularAPIView):
    """
    Custom schema view that handles errors gracefully.
    Works even if database is not available.
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, *args, **kwargs):
        try:
            # Try to generate schema normally
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error generating schema: {e}", exc_info=True)
            
            # Check if it's a database error
            error_str = str(e).lower()
            if 'database' in error_str or 'connection' in error_str or 'operationalerror' in error_str:
                logger.warning("Database not available for schema generation, returning basic schema")
            
            # Return a basic schema even if generation fails
            # This allows Swagger UI to load, even if endpoints aren't fully documented
            return Response(
                {
                    'openapi': '3.0.3',
                    'info': {
                        'title': 'Academy CRM API',
                        'version': '1.0.0',
                        'description': 'REST API for Academy CRM Backend. Note: Full schema requires database connection.',
                    },
                    'servers': [
                        {
                            'url': request.build_absolute_uri('/'),
                            'description': 'Current server'
                        }
                    ],
                    'paths': {
                        '/api/v1/auth/login/': {
                            'post': {
                                'tags': ['Authentication'],
                                'summary': 'Login',
                                'description': 'Obtain JWT token',
                                'requestBody': {
                                    'required': True,
                                    'content': {
                                        'application/json': {
                                            'schema': {
                                                'type': 'object',
                                                'properties': {
                                                    'username': {'type': 'string'},
                                                    'password': {'type': 'string'}
                                                }
                                            }
                                        }
                                    }
                                },
                                'responses': {
                                    '200': {
                                        'description': 'Success',
                                        'content': {
                                            'application/json': {
                                                'schema': {
                                                    'type': 'object',
                                                    'properties': {
                                                        'access': {'type': 'string'},
                                                        'refresh': {'type': 'string'}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    'components': {
                        'securitySchemes': {
                            'Bearer': {
                                'type': 'http',
                                'scheme': 'bearer',
                                'bearerFormat': 'JWT',
                            }
                        }
                    },
                },
                status=status.HTTP_200_OK,
                content_type='application/vnd.oai.openapi+json'
            )

