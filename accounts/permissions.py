"""
Custom permissions for accounts app.
"""
from rest_framework import permissions


class IsAdminOrSelf(permissions.BasePermission):
    """
    Permission to allow users to view/edit themselves,
    and admins to view/edit anyone.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.is_admin:
            return True
        
        # Users can only access their own records
        return obj == request.user
