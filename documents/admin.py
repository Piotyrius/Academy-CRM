"""
Admin configuration for documents app.
"""
from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for Document model."""
    list_display = ['owner', 'kind', 'visibility', 'created_at']
    list_filter = ['kind', 'visibility', 'created_at']
    search_fields = ['owner__email', 'description']
    ordering = ['-created_at']
    raw_id_fields = ['owner']