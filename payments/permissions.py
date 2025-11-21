"""
Permissions for payments app.
"""
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Permission for admins to manage, others read-only."""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and getattr(request.user, 'is_admin', False)


class CanViewOwnInvoices(permissions.BasePermission):
    """Permission for students to view their own invoices."""
    
    def has_object_permission(self, request, view, obj):
        # Admins can view all
        if getattr(request.user, 'is_admin', False):
            return True
        
        # Students can view their own invoices
        if hasattr(obj, 'enrollment'):
            return obj.enrollment.student == request.user
        if hasattr(obj, 'student'):
            return obj.student == request.user
        if hasattr(obj, 'invoice'):
            return obj.invoice.enrollment.student == request.user
        
        return False

