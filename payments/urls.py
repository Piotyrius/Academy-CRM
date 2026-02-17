"""
URL configuration for payments app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PricingViewSet, PaymentPlanViewSet, DiscountViewSet,
    InvoiceViewSet, PaymentViewSet, PaymentScheduleViewSet,
    PaymentMethodViewSet
)

router = DefaultRouter()
router.register(r'pricings', PricingViewSet, basename='pricing')
router.register(r'payment-plans', PaymentPlanViewSet, basename='payment-plan')
router.register(r'discounts', DiscountViewSet, basename='discount')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'payment-schedules', PaymentScheduleViewSet, basename='payment-schedule')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')

urlpatterns = [
    path('', include(router.urls)),
]

