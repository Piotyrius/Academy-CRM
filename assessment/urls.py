"""
URL configuration for assessment app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssessmentViewSet, SubmissionViewSet, GradeViewSet

router = DefaultRouter()
router.register(r'assessments', AssessmentViewSet, basename='assessment')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'grades', GradeViewSet, basename='grade')

urlpatterns = [
    path('', include(router.urls)),
]
