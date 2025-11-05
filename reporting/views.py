"""
Views for reporting app.
"""
from rest_framework import views, permissions
from rest_framework.response import Response
from django.http import HttpResponse
import csv
from io import StringIO
from accounts.models import User
from catalog.models import Program, Cohort
from admissions.models import Application, Enrollment
from attendance.models import AttendanceRecord
from assessment.models import Grade
from certificates.models import Certificate


class CSVExportView(views.APIView):
    """Base view for CSV exports."""
    permission_classes = [permissions.IsAdminUser]
    
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