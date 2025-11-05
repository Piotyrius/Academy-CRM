"""
URL configuration for admissions app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, EnrollmentViewSet

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')

urlpatterns = [
    path('', include(router.urls)),
]
