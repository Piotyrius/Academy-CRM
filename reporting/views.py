"""
Views for reporting app.
"""
from rest_framework import views
from rest_framework.response import Response
from django.http import HttpResponse
from django.db.models import Sum
import csv
from io import StringIO

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from accounts.permissions import IsAdminUser
from admissions.models import Application, Enrollment
from attendance.models import AttendanceRecord
from assessment.models import Grade
from certificates.models import Certificate

from .query import (
    get_student_financial_queryset,
    get_timeseries_analytics,
    get_financial_analytics,
    get_cohort_performance,
)
from .filters import AnalyticsFilterSerializer


class CSVExportView(views.APIView):
    """Base view for CSV exports."""
    permission_classes = [IsAdminUser]
    
    def get_csv_response(self, filename, rows, headers):
        """Generate CSV response."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ApplicationExportView(CSVExportView):
    """Export applications to CSV."""
    
    def get(self, request):
        program_id = request.query_params.get('program')
        status = request.query_params.get('status')
        
        queryset = Application.objects.select_related('program').all()
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if status:
            queryset = queryset.filter(status=status)
        
        rows = []
        for app in queryset:
            rows.append([
                app.id,
                app.name,
                app.email,
                app.phone,
                app.program.name,
                app.status,
                app.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        headers = ['ID', 'Name', 'Email', 'Phone', 'Program', 'Status', 'Created At']
        return self.get_csv_response('applications.csv', rows, headers)


class EnrollmentExportView(CSVExportView):
    """Export enrollments to CSV."""
    
    def get(self, request):
        program_id = request.query_params.get('program')
        cohort_id = request.query_params.get('cohort')
        
        queryset = Enrollment.objects.select_related('student', 'cohort').all()
        if program_id:
            queryset = queryset.filter(cohort__course__program_id=program_id)
        if cohort_id:
            queryset = queryset.filter(cohort_id=cohort_id)
        
        rows = []
        for enrollment in queryset:
            rows.append([
                enrollment.id,
                enrollment.student.email,
                enrollment.student.get_full_name(),
                enrollment.cohort.name,
                enrollment.status,
                enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        headers = ['ID', 'Student Email', 'Student Name', 'Cohort', 'Status', 'Enrolled At']
        return self.get_csv_response('enrollments.csv', rows, headers)


class AttendanceExportView(CSVExportView):
    """Export attendance to CSV."""
    
    def get(self, request):
        cohort_id = request.query_params.get('cohort')
        threshold = request.query_params.get('threshold')
        
        queryset = AttendanceRecord.objects.select_related('student', 'session').all()
        if cohort_id:
            queryset = queryset.filter(session__cohort_id=cohort_id)
        
        rows = []
        for record in queryset:
            rows.append([
                record.id,
                record.student.email,
                record.student.get_full_name(),
                record.session.cohort.name,
                record.session.start_at.strftime('%Y-%m-%d %H:%M:%S'),
                record.status,
                record.marked_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        headers = ['ID', 'Student Email', 'Student Name', 'Cohort', 'Session Start', 'Status', 'Marked At']
        return self.get_csv_response('attendance.csv', rows, headers)


class GradeExportView(CSVExportView):
    """Export grades to CSV."""
    
    def get(self, request):
        cohort_id = request.query_params.get('cohort')
        
        queryset = Grade.objects.select_related('student', 'assessment').all()
        if cohort_id:
            queryset = queryset.filter(assessment__cohort_id=cohort_id)
        
        rows = []
        for grade in queryset:
            rows.append([
                grade.id,
                grade.student.email,
                grade.student.get_full_name(),
                grade.assessment.title,
                grade.score,
                grade.max_score,
                float(grade.percentage),
                grade.graded_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        headers = ['ID', 'Student Email', 'Student Name', 'Assessment', 'Score', 'Max Score', 'Percentage', 'Graded At']
        return self.get_csv_response('grades.csv', rows, headers)


class CertificateExportView(CSVExportView):
    """Export certificates to CSV."""
    
    def get(self, request):
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        
        queryset = Certificate.objects.select_related('student', 'cohort').all()
        if from_date:
            queryset = queryset.filter(issued_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(issued_at__lte=to_date)
        
        rows = []
        for cert in queryset:
            rows.append([
                cert.serial,
                cert.student.email,
                cert.student.get_full_name(),
                cert.cohort.name,
                cert.status,
                cert.issued_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        headers = ['Serial', 'Student Email', 'Student Name', 'Cohort', 'Status', 'Issued At']
        return self.get_csv_response('certificates.csv', rows, headers)


class AnalyticsOverviewView(views.APIView):
    """
    Return high-level mixed student + financial metrics as JSON.

    This is intended for dashboards and charts on the reporting page.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Analytics overview (student + financial)",
        description=(
            "Return aggregated metrics for enrollments and payments, filtered by "
            "date range, program, cohort, student, or lecturer."
        ),
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("program_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("cohort_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("student_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("lecturer_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
        ],
        tags=["Reporting"],
    )
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        qs = get_student_financial_queryset(params)

        total_enrollments = qs.count()
        total_paid = qs.aggregate(total_paid_sum=Sum("total_paid"))["total_paid_sum"] or 0

        # Simple breakdown by program for charts (frontend can aggregate further)
        by_program = {}
        for enrollment in qs:
            program = getattr(getattr(enrollment.cohort, "course", None), "program", None)
            program_name = getattr(program, "name", "Unknown")
            entry = by_program.setdefault(program_name, {"enrollments": 0, "total_paid": 0})
            entry["enrollments"] += 1
            entry["total_paid"] += float(enrollment.total_paid or 0)

        return Response(
            {
                "total_enrollments": total_enrollments,
                "total_paid": float(total_paid),
                "by_program": by_program,
            }
        )


class StudentFinancialReportView(views.APIView):
    """
    Return per-student rows combining enrollment and financial info.

    This is suitable for tabular views and for the frontend to build more
    advanced aggregations and charts.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Student financial report",
        description=(
            "Return per-enrollment/student records with basic academic and "
            "financial information. Supports the same filters as the analytics "
            "overview endpoint."
        ),
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("program_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("cohort_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("student_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("lecturer_id", OpenApiTypes.UUID, OpenApiParameter.QUERY),
        ],
        tags=["Reporting"],
    )
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        qs = get_student_financial_queryset(params)

        rows = []
        for enrollment in qs:
            student = enrollment.student
            cohort = enrollment.cohort
            course = getattr(cohort, "course", None)
            program = getattr(course, "program", None)
            rows.append(
                {
                    "enrollment_id": str(enrollment.id),
                    "student_id": str(student.id),
                    "student_email": student.email,
                    "student_name": student.get_full_name(),
                    "program_name": getattr(program, "name", None),
                    "cohort_name": getattr(cohort, "name", None),
                    "status": enrollment.status,
                    "enrolled_at": enrollment.enrolled_at,
                    "total_paid": float(enrollment.total_paid or 0),
                }
            )

        return Response({"results": rows})


class TimeSeriesAnalyticsView(views.APIView):
    """
    Time-series analytics for enrollments and payments.

    Supports grouping by day, week, or month for use in charts.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Time-series analytics",
        description=(
            "Return time-series data for enrollments and completed payments. "
            "Use the 'group_by' query parameter to group by day, week, or month."
        ),
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter(
                "group_by",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["day", "week", "month"],
            ),
        ],
        tags=["Reporting"],
    )
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        group_by = params.get("group_by") or "day"
        if group_by not in {"day", "week", "month"}:
            group_by = "day"

        series = get_timeseries_analytics(params, group_by=group_by)  # type: ignore[arg-type]
        return Response({"group_by": group_by, "series": series})


class FinancialAnalyticsView(views.APIView):
    """
    Financial analytics: invoices and payments, with breakdowns.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Financial analytics",
        description=(
            "Return high-level financial metrics based on invoices and payments, "
            "including totals and breakdowns by program, cohort, and invoice status."
        ),
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
        ],
        tags=["Reporting"],
    )
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        data = get_financial_analytics(params)
        return Response(data)


class CohortAnalyticsView(views.APIView):
    """
    Cohort performance analytics: students, attendance, grades, finances.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Cohort performance analytics",
        description=(
            "Return per-cohort performance metrics including student count, "
            "attendance rate, average grade, and financial totals."
        ),
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
        ],
        tags=["Reporting"],
    )
    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        rows = get_cohort_performance(params)
        return Response({"results": rows})