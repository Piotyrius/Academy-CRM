#!/usr/bin/env python
"""
Debug script for Swagger/API documentation issues.
Run this in Render shell: python scripts/debug_swagger.py
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Change to project root directory
os.chdir(project_root)

import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

from django.urls import reverse, resolve
from django.test import RequestFactory
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.openapi import AutoSchema
from academy_crm.views import CustomSpectacularAPIView
from django.conf import settings
import json

print("=" * 80)
print("SWAGGER/API DOCUMENTATION DEBUG")
print("=" * 80)
print()

# 1. Check URL configuration
print("1. CHECKING URL CONFIGURATION")
print("-" * 80)
try:
    from academy_crm.urls import urlpatterns
    print(f"✅ URL patterns loaded: {len(urlpatterns)} patterns found")
    
    # Check for Swagger URLs
    swagger_urls = []
    for pattern in urlpatterns:
        if hasattr(pattern, 'name') and pattern.name:
            if 'swagger' in pattern.name.lower() or 'docs' in pattern.name.lower() or 'schema' in pattern.name.lower():
                swagger_urls.append(f"  - {pattern.pattern} (name: {pattern.name})")
    
    if swagger_urls:
        print("✅ Swagger-related URLs found:")
        for url in swagger_urls:
            print(url)
    else:
        print("❌ No Swagger URLs found!")
except Exception as e:
    print(f"❌ Error checking URLs: {e}")
    import traceback
    traceback.print_exc()

print()

# 2. Test URL resolution
print("2. TESTING URL RESOLUTION")
print("-" * 80)
test_urls = [
    '/api/docs/',
    '/api/docs',
    '/api/schema/',
    '/api/schema',
]

for url in test_urls:
    try:
        resolved = resolve(url)
        print(f"✅ {url} -> {resolved.view_name} ({resolved.func.__name__})")
    except Exception as e:
        print(f"❌ {url} -> ERROR: {e}")

print()

# 3. Check database connection
print("3. CHECKING DATABASE CONNECTION")
print("-" * 80)
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
    print("✅ Database connection: OK")
    print(f"   Database: {settings.DATABASES['default']['NAME']}")
    print(f"   Host: {settings.DATABASES['default']['HOST']}")
    print(f"   User: {settings.DATABASES['default']['USER']}")
except Exception as e:
    print(f"❌ Database connection: FAILED")
    print(f"   Error: {e}")
    print("   ⚠️  Schema generation may fail without database connection")

print()

# 4. Check SPECTACULAR_SETTINGS
print("4. CHECKING SPECTACULAR SETTINGS")
print("-" * 80)
if hasattr(settings, 'SPECTACULAR_SETTINGS'):
    spectacular = settings.SPECTACULAR_SETTINGS
    print("✅ SPECTACULAR_SETTINGS found")
    print(f"   Title: {spectacular.get('TITLE', 'N/A')}")
    print(f"   Version: {spectacular.get('VERSION', 'N/A')}")
    print(f"   Schema Path Prefix: {spectacular.get('SCHEMA_PATH_PREFIX', 'N/A')}")
    print(f"   Serve Permissions: {spectacular.get('SERVE_PERMISSIONS', 'N/A')}")
    print(f"   Serve Authentication: {spectacular.get('SERVE_AUTHENTICATION', 'N/A')}")
else:
    print("❌ SPECTACULAR_SETTINGS not found!")

print()

# 5. Test schema generation
print("5. TESTING SCHEMA GENERATION")
print("-" * 80)
try:
    factory = RequestFactory()
    request = factory.get('/api/schema/')
    
    # Try to generate schema
    view = CustomSpectacularAPIView.as_view()
    response = view(request)
    
    if response.status_code == 200:
        print("✅ Schema generation: SUCCESS")
        try:
            schema_data = response.data if hasattr(response, 'data') else json.loads(response.content)
            if isinstance(schema_data, dict):
                print(f"   OpenAPI version: {schema_data.get('openapi', 'N/A')}")
                print(f"   Info title: {schema_data.get('info', {}).get('title', 'N/A')}")
                paths_count = len(schema_data.get('paths', {}))
                print(f"   Paths found: {paths_count}")
                
                if paths_count == 0:
                    print("   ⚠️  WARNING: No API paths found in schema!")
                    print("   This might mean:")
                    print("      - No API views are registered")
                    print("      - Views don't have @extend_schema decorator")
                    print("      - Database connection issue")
                else:
                    print("   ✅ API paths found:")
                    for path in list(schema_data.get('paths', {}).keys())[:10]:
                        print(f"      - {path}")
                    if paths_count > 10:
                        print(f"      ... and {paths_count - 10} more")
        except Exception as e:
            print(f"   ⚠️  Could not parse schema data: {e}")
            print(f"   Response content type: {response.get('Content-Type', 'N/A')}")
            print(f"   Response length: {len(response.content) if hasattr(response, 'content') else 'N/A'} bytes")
    else:
        print(f"❌ Schema generation: FAILED (Status: {response.status_code})")
        if hasattr(response, 'data'):
            print(f"   Error: {response.data}")
except Exception as e:
    print(f"❌ Schema generation: ERROR")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

print()

# 6. Check installed apps
print("6. CHECKING INSTALLED APPS")
print("-" * 80)
if 'drf_spectacular' in settings.INSTALLED_APPS:
    print("✅ drf_spectacular is installed")
else:
    print("❌ drf_spectacular is NOT installed!")

if 'rest_framework' in settings.INSTALLED_APPS:
    print("✅ rest_framework is installed")
else:
    print("❌ rest_framework is NOT installed!")

print()

# 7. Check API views
print("7. CHECKING API VIEWS")
print("-" * 80)
try:
    from accounts.urls import urlpatterns as accounts_urls
    from catalog.urls import urlpatterns as catalog_urls
    
    total_api_urls = 0
    for url_pattern in accounts_urls + catalog_urls:
        if hasattr(url_pattern, 'pattern'):
            total_api_urls += 1
    
    print(f"✅ Found API URL patterns: {total_api_urls}")
    print("   (Checking accounts and catalog apps)")
except Exception as e:
    print(f"⚠️  Could not check API views: {e}")

print()

# 8. Test Swagger view directly
print("8. TESTING SWAGGER VIEW DIRECTLY")
print("-" * 80)
try:
    from drf_spectacular.views import SpectacularSwaggerView
    
    factory = RequestFactory()
    request = factory.get('/api/docs/')
    request.META['HTTP_HOST'] = 'academy-crm.onrender.com'
    request.META['SERVER_NAME'] = 'academy-crm.onrender.com'
    request.META['SERVER_PORT'] = '443'
    
    view = SpectacularSwaggerView.as_view(
        url_name='schema-slash',
        authentication_classes=[],
        permission_classes=[]
    )
    
    response = view(request)
    print(f"✅ Swagger view response: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Swagger UI should load")
    elif response.status_code == 301 or response.status_code == 302:
        print(f"   ⚠️  Redirect detected: {response.status_code}")
        if hasattr(response, 'url'):
            print(f"   Redirect to: {response.url}")
except Exception as e:
    print(f"❌ Swagger view test: ERROR")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
print()
print("NEXT STEPS:")
print("1. If schema has 0 paths, check that your API views use @extend_schema decorator")
print("2. If database connection failed, fix DB_HOST environment variable")
print("3. If URLs don't resolve, check academy_crm/urls.py")
print("4. Check Render logs for any errors during startup")

