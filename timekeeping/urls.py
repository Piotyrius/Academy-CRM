from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkLogViewSet, RateViewSet, TimesheetViewSet, payroll_export


router = DefaultRouter()
router.register(r'worklogs', WorkLogViewSet, basename='worklog')
router.register(r'rates', RateViewSet, basename='rate')
router.register(r'timesheets', TimesheetViewSet, basename='timesheet')

urlpatterns = [
    path('', include(router.urls)),
    path('payroll/export/', payroll_export, name='payroll-export'),  # Added trailing slash for consistency
]


