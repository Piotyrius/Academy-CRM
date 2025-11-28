"""
URL configuration for reporting app.
"""
from django.urls import path
from .views import (
    ApplicationExportView,
    EnrollmentExportView,
    AttendanceExportView,
    GradeExportView,
    CertificateExportView,
    AnalyticsOverviewView,
    StudentFinancialReportView,
    TimeSeriesAnalyticsView,
    FinancialAnalyticsView,
    CohortAnalyticsView,
)

urlpatterns = [
    # Existing CSV exports
    path('reports/applications/', ApplicationExportView.as_view(), name='export-applications'),
    path('reports/enrollments/', EnrollmentExportView.as_view(), name='export-enrollments'),
    path('reports/attendance/', AttendanceExportView.as_view(), name='export-attendance'),
    path('reports/grades/', GradeExportView.as_view(), name='export-grades'),
    path('reports/certificates/', CertificateExportView.as_view(), name='export-certificates'),

    # New JSON analytics/reporting endpoints
    path('analytics/overview/', AnalyticsOverviewView.as_view(), name='analytics-overview'),
    path('analytics/student-financial/', StudentFinancialReportView.as_view(), name='student-financial-report'),
    path('analytics/timeseries/', TimeSeriesAnalyticsView.as_view(), name='analytics-timeseries'),
    path('analytics/financial/', FinancialAnalyticsView.as_view(), name='analytics-financial'),
    path('analytics/by-cohort/', CohortAnalyticsView.as_view(), name='analytics-by-cohort'),
]
