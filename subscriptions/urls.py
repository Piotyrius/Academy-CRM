"""
URLs for subscriptions app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationViewSet, SubscriptionPlanViewSet,
    SubscriptionViewSet, FeatureStatusViewSet
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'plans', SubscriptionPlanViewSet, basename='plan')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'features', FeatureStatusViewSet, basename='feature')

urlpatterns = [
    path('', include(router.urls)),
]

