from django.contrib import admin
from .models import WorkLog, Rate, Timesheet


@admin.register(Rate)
class RateAdmin(admin.ModelAdmin):
    list_display = ('lecturer', 'per_hour_minor', 'currency', 'active', 'created_at')
    list_filter = ('active', 'currency')
    search_fields = ('lecturer__email',)


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ('lecturer', 'start_at', 'end_at', 'minutes', 'source', 'session')
    list_filter = ('source',)
    search_fields = ('lecturer__email', 'session__cohort__name')
    autocomplete_fields = ('lecturer', 'session')

    actions = ['export_selected_csv']

    def export_selected_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="worklogs.csv"'
        writer = csv.writer(resp)
        writer.writerow(['lecturer', 'start_at', 'end_at', 'minutes', 'source', 'session'])
        for wl in queryset:
            writer.writerow([wl.lecturer.email, wl.start_at, wl.end_at, wl.minutes, wl.source, wl.session_id])
        return resp

    export_selected_csv.short_description = 'Export selected work logs to CSV'


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ('lecturer', 'period_start', 'period_end', 'status', 'total_minutes', 'amount_minor', 'currency')
    list_filter = ('status', 'currency')
    search_fields = ('lecturer__email',)


