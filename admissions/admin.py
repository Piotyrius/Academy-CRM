"""
Admin configuration for admissions app.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Application, Enrollment


@admin.register(Application)
class ApplicationAdmin(SimpleHistoryAdmin):
    """Admin for Application model."""
    list_display = ['name', 'email', 'phone', 'program', 'status', 'created_at']
    list_filter = ['status', 'program', 'created_at']
    search_fields = ['name', 'email', 'phone']
    ordering = ['-created_at']
    raw_id_fields = ['program']
    date_hierarchy = 'created_at'


@admin.register(Enrollment)
class EnrollmentAdmin(SimpleHistoryAdmin):
    """Admin for Enrollment model."""
    list_display = ['student', 'cohort', 'status', 'enrolled_at', 'completed_at']
    list_filter = ['status', 'cohort__course', 'enrolled_at']
    search_fields = ['student__email', 'student__first_name', 'student__last_name', 'cohort__name']
    ordering = ['-enrolled_at']
    raw_id_fields = ['student', 'cohort']
    date_hierarchy = 'enrolled_at'