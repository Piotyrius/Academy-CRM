"""
Permissions for catalog app.
"""
from rest_framework import permissions


class IsAdminOrLecturerOwner(permissions.BasePermission):
    """
    Permission to allow admins full access,
    lecturers access to their own cohorts.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.is_admin:
            return True
        
        # Lecturers can only access their own cohorts
        if hasattr(obj, 'lecturer'):
            return obj.lecturer == request.user
        if hasattr(obj, 'cohort'):
            return obj.cohort.lecturer == request.user
        
        return False
