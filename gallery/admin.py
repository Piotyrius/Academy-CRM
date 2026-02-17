from django.contrib import admin
from .models import Work


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'is_public', 'created_at')
    list_filter = ('status', 'is_public')
    search_fields = ('title', 'owner__email')


