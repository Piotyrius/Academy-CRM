"""
Permissions for attendance app.
"""
from rest_framework import permissions


class IsAdminOrLecturerOwner(permissions.BasePermission):
    """Permission for admins and lecturers on their cohorts."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        
        if hasattr(obj, 'session'):
            return obj.session.cohort.lecturer == request.user
        
        return False
