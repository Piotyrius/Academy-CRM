"""
Admin configuration for attendance app.
"""
from django.contrib import admin
from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """Admin for AttendanceRecord model."""
    list_display = ['student', 'session', 'status', 'marked_by', 'marked_at']
    list_filter = ['status', 'session__cohort', 'marked_at']
    search_fields = ['student__email', 'student__first_name', 'student__last_name', 'session__cohort__name']
    ordering = ['-marked_at']
    raw_id_fields = ['session', 'student', 'marked_by']
    date_hierarchy = 'marked_at'