"""
Admin configuration for assessment app.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Assessment, Submission, Grade


@admin.register(Assessment)
class AssessmentAdmin(SimpleHistoryAdmin):
    """Admin for Assessment model."""
    list_display = ['title', 'cohort', 'kind', 'weight', 'due_at', 'published']
    list_filter = ['kind', 'published', 'cohort', 'due_at']
    search_fields = ['title', 'description']
    ordering = ['-due_at']
    raw_id_fields = ['cohort']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """Admin for Submission model."""
    list_display = ['student', 'assessment', 'submitted_at', 'late_flag']
    list_filter = ['late_flag', 'submitted_at', 'assessment']
    search_fields = ['student__email', 'assessment__title']
    ordering = ['-submitted_at']
    raw_id_fields = ['assessment', 'student']


@admin.register(Grade)
class GradeAdmin(SimpleHistoryAdmin):
    """Admin for Grade model."""
    list_display = ['student', 'assessment', 'score', 'max_score', 'graded_by', 'graded_at']
    list_filter = ['assessment', 'graded_at']
    search_fields = ['student__email', 'assessment__title']
    ordering = ['-graded_at']
    raw_id_fields = ['assessment', 'student', 'graded_by']