"""
URL configuration for catalog app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProgramViewSet, CourseViewSet, CohortViewSet, SessionViewSet

router = DefaultRouter()
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'cohorts', CohortViewSet, basename='cohort')
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]
