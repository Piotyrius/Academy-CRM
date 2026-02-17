"""
Admin configuration for certificates app.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(SimpleHistoryAdmin):
    """Admin for Certificate model."""
    list_display = ['serial', 'student', 'cohort', 'status', 'issued_at']
    list_filter = ['status', 'issued_at', 'cohort']
    search_fields = ['serial', 'qr_token', 'student__email', 'student__first_name']
    ordering = ['-issued_at']
    raw_id_fields = ['student', 'cohort']
    date_hierarchy = 'issued_at'
    readonly_fields = ['serial', 'qr_token', 'issued_at']