#!/usr/bin/env python
"""
Simpler debug script for Swagger/API documentation issues.
Run this in Render shell: python manage.py shell < scripts/debug_swagger_simple.py
OR: python -c "exec(open('scripts/debug_swagger_simple.py').read())"
"""
from django.urls import resolve
from django.test import RequestFactory
from academy_crm.views import CustomSpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from django.conf import settings
from django.db import connection
import json

print("=" * 80)
print("SWAGGER/API DOCUMENTATION DEBUG")
print("=" * 80)
print()

# 1. Check URL resolution
print("1. TESTING URL RESOLUTION")
print("-" * 80)
test_urls = ['/api/docs/', '/api/docs', '/api/schema/', '/api/schema']
for url in test_urls:
    try:
        resolved = resolve(url)
        print(f"✅ {url} -> {resolved.view_name}")
    except Exception as e:
        print(f"❌ {url} -> ERROR: {e}")

print()

# 2. Check database
print("2. CHECKING DATABASE CONNECTION")
print("-" * 80)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✅ Database: OK")
    print(f"   Host: {settings.DATABASES['default']['HOST']}")
    print(f"   Name: {settings.DATABASES['default']['NAME']}")
except Exception as e:
    print(f"❌ Database: FAILED - {e}")

print()

# 3. Test schema generation
print("3. TESTING SCHEMA GENERATION")
print("-" * 80)
try:
    factory = RequestFactory()
    request = factory.get('/api/schema/')
    request.META['HTTP_HOST'] = 'academy-crm.onrender.com'
    
    view = CustomSpectacularAPIView.as_view()
    response = view(request)
    
    if response.status_code == 200:
        schema = response.data if hasattr(response, 'data') else json.loads(response.content)
        paths_count = len(schema.get('paths', {}))
        print(f"✅ Schema generated: {paths_count} paths found")
        
        if paths_count == 0:
            print("   ⚠️  WARNING: No API paths in schema!")
            print("   This means Swagger will be empty.")
        else:
            print("   ✅ First few paths:")
            for i, path in enumerate(list(schema.get('paths', {}).keys())[:5]):
                print(f"      - {path}")
            if paths_count > 5:
                print(f"      ... and {paths_count - 5} more")
    else:
        print(f"❌ Schema generation failed: Status {response.status_code}")
except Exception as e:
    print(f"❌ Schema generation error: {e}")
    import traceback
    traceback.print_exc()

print()

# 4. Check settings
print("4. CHECKING SETTINGS")
print("-" * 80)
print(f"✅ drf_spectacular installed: {'drf_spectacular' in settings.INSTALLED_APPS}")
if hasattr(settings, 'SPECTACULAR_SETTINGS'):
    spec = settings.SPECTACULAR_SETTINGS
    print(f"✅ Title: {spec.get('TITLE', 'N/A')}")
    print(f"✅ Schema prefix: {spec.get('SCHEMA_PATH_PREFIX', 'N/A')}")

print()
print("=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)

