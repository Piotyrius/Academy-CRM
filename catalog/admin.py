"""
Admin configuration for catalog app.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Program, Course, Cohort, Session


@admin.register(Program)
class ProgramAdmin(SimpleHistoryAdmin):
    """Admin for Program model."""
    list_display = ['name', 'code', 'active', 'version', 'created_at']
    list_filter = ['active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']


@admin.register(Course)
class CourseAdmin(SimpleHistoryAdmin):
    """Admin for Course model."""
    list_display = ['title', 'code', 'program', 'hours', 'credits', 'created_at']
    list_filter = ['program', 'created_at']
    search_fields = ['title', 'code', 'description']
    ordering = ['title']
    raw_id_fields = ['program']


@admin.register(Cohort)
class CohortAdmin(SimpleHistoryAdmin):
    """Admin for Cohort model."""
    list_display = ['name', 'course', 'lecturer', 'status', 'start_date', 'end_date', 'capacity', 'current_enrollment_count']
    list_filter = ['status', 'course__program', 'start_date']
    search_fields = ['name', 'course__title']
    ordering = ['-start_date']
    raw_id_fields = ['course', 'lecturer']
    date_hierarchy = 'start_date'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin for Session model."""
    list_display = ['cohort', 'start_at', 'end_at', 'location', 'is_cancelled']
    list_filter = ['is_cancelled', 'start_at', 'cohort']
    search_fields = ['cohort__name']
    ordering = ['-start_at']
    date_hierarchy = 'start_at'
    raw_id_fields = ['cohort']