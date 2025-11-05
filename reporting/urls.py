"""
URL configuration for reporting app.
"""
from django.urls import path
from .views import (
    ApplicationExportView,
    EnrollmentExportView,
    AttendanceExportView,
    GradeExportView,
    CertificateExportView
)

urlpatterns = [
    path('reports/applications/', ApplicationExportView.as_view(), name='export-applications'),
    path('reports/enrollments/', EnrollmentExportView.as_view(), name='export-enrollments'),
    path('reports/attendance/', AttendanceExportView.as_view(), name='export-attendance'),
    path('reports/grades/', GradeExportView.as_view(), name='export-grades'),
    path('reports/certificates/', CertificateExportView.as_view(), name='export-certificates'),
]
