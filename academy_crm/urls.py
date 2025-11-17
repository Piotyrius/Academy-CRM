"""
URL configuration for academy_crm project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from academy_crm.views import CustomSpectacularAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', include('health_check.urls')),
    
    # API Documentation (publicly accessible for frontend developers)
    # Using trailing slashes consistently - Django will handle redirects
    path('api/schema/', CustomSpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(
        url='/api/schema/',
        authentication_classes=[],
        permission_classes=[]
    ), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(
        url='/api/schema/',
        authentication_classes=[],
        permission_classes=[]
    ), name='redoc'),
    
    # API v1
    path('api/v1/subscriptions/', include('subscriptions.urls')),  # Subscription management
    path('api/v1/', include('accounts.urls')),
    path('api/v1/catalog/', include('catalog.urls')),
    path('api/v1/admissions/', include('admissions.urls')),
    path('api/v1/attendance/', include('attendance.urls')),
    path('api/v1/assessment/', include('assessment.urls')),
    path('api/v1/certificates/', include('certificates.urls')),
    path('api/v1/documents/', include('documents.urls')),
    path('api/v1/reporting/', include('reporting.urls')),
    path('api/v1/timekeeping/', include('timekeeping.urls')),
    path('api/v1/gallery/', include('gallery.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar URLs
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass