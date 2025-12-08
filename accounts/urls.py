"""
URL configuration for accounts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, CustomTokenObtainPairView, StudentPortalViewSet,
    password_reset_request, password_reset_confirm, CustomTokenBlacklistView,
    verify_token
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'me', StudentPortalViewSet, basename='me')

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', CustomTokenBlacklistView.as_view(), name='token_blacklist'),
    path('auth/verify/', verify_token, name='token_verify'),
    path('auth/password-reset/', password_reset_request, name='password_reset_request'),
    path('auth/password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    path('', include(router.urls)),
]