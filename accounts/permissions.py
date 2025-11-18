"""
Custom permissions for accounts app.
"""
from rest_framework import permissions


class IsAdminOrSelf(permissions.BasePermission):
    """
    Permission to allow users to view/edit themselves,
    and admins to view/edit anyone.
    """
    
    def has_permission(self, request, view):
        """Check permission for list and destroy actions."""
        # For list and destroy, only admins are allowed
        if view.action in ['list', 'destroy']:
            return request.user.is_authenticated and request.user.is_admin
        # For other actions, allow authenticated users (object-level check will apply)
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.is_admin:
            return True
        
        # Users can only access their own records
        return obj == request.user
