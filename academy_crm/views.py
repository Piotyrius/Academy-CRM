"""
Custom views for Academy CRM.
"""
import logging

from django.conf import settings
from django.db import connection
from drf_spectacular.views import SpectacularAPIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class CustomSpectacularAPIView(SpectacularAPIView):
    """
    Custom schema view that handles errors gracefully.
    Works even if database is not available.

    In production, access is restricted to authenticated users; in DEBUG,
    schema remains publicly accessible for easier local development.
    """

    # Use JWT for authentication when protection is enabled
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        # Allow open access in DEBUG to simplify local development.
        if getattr(settings, "DEBUG", False):
            return [AllowAny()]
        # Require authentication otherwise.
        return [IsAuthenticated()]

    def get_authenticators(self):
        # In DEBUG, don't require authentication for schema access.
        if getattr(settings, "DEBUG", False):
            return []
        return super().get_authenticators()

    def get(self, request, *args, **kwargs):
        try:
            # Try to generate schema normally
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error generating schema: {e}", exc_info=True)

            # Check if it's a database error
            error_str = str(e).lower()
            if (
                "database" in error_str
                or "connection" in error_str
                or "operationalerror" in error_str
            ):
                logger.warning(
                    "Database not available for schema generation, returning basic schema"
                )

            # Return a basic schema even if generation fails
            # This allows Swagger UI to load, even if endpoints aren't fully documented
            return Response(
                {
                    "openapi": "3.0.3",
                    "info": {
                        "title": "Academy CRM API",
                        "version": "1.0.0",
                        "description": "REST API for Academy CRM Backend. Note: Full schema requires database connection.",
                    },
                    "servers": [
                        {
                            "url": request.build_absolute_uri("/"),
                            "description": "Current server",
                        }
                    ],
                    "paths": {
                        "/api/v1/auth/login/": {
                            "post": {
                                "tags": ["Authentication"],
                                "summary": "Login",
                                "description": "Obtain JWT token",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "username": {"type": "string"},
                                                    "password": {"type": "string"},
                                                },
                                            }
                                        }
                                    },
                                },
                                "responses": {
                                    "200": {
                                        "description": "Success",
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "type": "object",
                                                    "properties": {
                                                        "access": {"type": "string"},
                                                        "refresh": {"type": "string"},
                                                    },
                                                }
                                            }
                                        },
                                    }
                                },
                            }
                        }
                    },
                    "components": {
                        "securitySchemes": {
                            "BearerAuth": {
                                "type": "http",
                                "scheme": "bearer",
                                "bearerFormat": "JWT",
                                "description": "JWT token obtained from /api/v1/auth/login/ endpoint",
                            }
                        }
                    },
                },
                status=status.HTTP_200_OK,
                content_type="application/vnd.oai.openapi+json",
            )

