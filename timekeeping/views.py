from rest_framework import viewsets, permissions, decorators, response
from django.db.models import Sum
from django.utils.dateparse import parse_date
from .models import WorkLog, Rate, Timesheet
from .serializers import WorkLogSerializer, RateSerializer, TimesheetSerializer
from django.http import HttpResponse
import csv


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'is_admin', False))


class WorkLogViewSet(viewsets.ModelViewSet):
    queryset = WorkLog.objects.select_related('lecturer', 'session').all()
    serializer_class = WorkLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['lecturer', 'session', 'source']
    ordering = ['-start_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return qs
        return qs.filter(lecturer=user)
    
    def perform_create(self, serializer):
        """Auto-assign lecturer from authenticated user for non-admin users."""
        user = self.request.user
        if not getattr(user, 'is_admin', False):
            # Non-admin users (lecturers) are automatically assigned as lecturer
            serializer.save(lecturer=user)
        else:
            # Admin can specify lecturer, but default to current user if not provided
            if 'lecturer' not in serializer.validated_data:
                serializer.save(lecturer=user)
            else:
                serializer.save()


class RateViewSet(viewsets.ModelViewSet):
    queryset = Rate.objects.select_related('lecturer').all()
    serializer_class = RateSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['lecturer', 'active', 'currency']
    ordering = ['-created_at']  # Add ordering to prevent pagination warning
    
    def perform_create(self, serializer):
        """Admin can create rates for any lecturer."""
        # Admin must specify lecturer explicitly
        serializer.save()


class TimesheetViewSet(viewsets.ModelViewSet):
    queryset = Timesheet.objects.select_related('lecturer').all()
    serializer_class = TimesheetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['lecturer', 'status']
    ordering = ['-period_start']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return qs
        return qs.filter(lecturer=user)
    
    def perform_create(self, serializer):
        """Auto-assign lecturer from authenticated user for non-admin users."""
        user = self.request.user
        if not getattr(user, 'is_admin', False):
            # Non-admin users (lecturers) are automatically assigned as lecturer
            serializer.save(lecturer=user)
        else:
            # Admin can specify lecturer, but default to current user if not provided
            if 'lecturer' not in serializer.validated_data:
                serializer.save(lecturer=user)
            else:
                serializer.save()


@decorators.api_view(['GET'])
@decorators.permission_classes([IsAdmin])
def payroll_export(request):
    """CSV export of payroll totals for a date range.

    Query params: from=YYYY-MM-DD, to=YYYY-MM-DD
    """
    from_date = parse_date(request.query_params.get('from'))
    to_date = parse_date(request.query_params.get('to'))
    filters = {}
    if from_date:
        filters['start_at__date__gte'] = from_date
    if to_date:
        filters['end_at__date__lte'] = to_date
    totals = (
        WorkLog.objects.filter(**filters)
        .values('lecturer')
        .annotate(total_minutes=Sum('minutes'))
    )
    # Include current rate if any
    # Build CSV
    output = []
    for row in totals:
        lecturer_id = row['lecturer']
        total_minutes = row['total_minutes'] or 0
        rate = Rate.objects.filter(lecturer_id=lecturer_id, active=True).first()
        per_hour_minor = rate.per_hour_minor if rate else 0
        amount_minor = int((total_minutes / 60) * per_hour_minor)
        output.append([
            str(lecturer_id),
            total_minutes,
            per_hour_minor,
            amount_minor,
            rate.currency if rate else 'USD',
        ])

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="payroll.csv"'
    writer = csv.writer(resp)
    writer.writerow(['lecturer_id', 'total_minutes', 'per_hour_minor', 'amount_minor', 'currency'])
    writer.writerows(output)
    return resp


