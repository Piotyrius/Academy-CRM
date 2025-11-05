"""
Permissions for documents app.
"""
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission for owners and admins."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        return obj.owner == request.user
