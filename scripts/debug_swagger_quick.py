from django.urls import resolve
from django.test import RequestFactory
from academy_crm.views import CustomSpectacularAPIView
from django.conf import settings
from django.db import connection
import json

print("=" * 80)
print("SWAGGER DEBUG")
print("=" * 80)

# Test URLs
print("\n1. URL RESOLUTION:")
for url in ['/api/docs/', '/api/schema/']:
    try:
        resolved = resolve(url)
        print(f"✅ {url} -> {resolved.view_name}")
    except Exception as e:
        print(f"❌ {url} -> {e}")

# Test database
print("\n2. DATABASE:")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print(f"✅ Connected to {settings.DATABASES['default']['HOST']}")
except Exception as e:
    print(f"❌ Database error: {e}")

# Test schema
print("\n3. SCHEMA GENERATION:")
try:
    factory = RequestFactory()
    request = factory.get('/api/schema/')
    request.META['HTTP_HOST'] = 'academy-crm.onrender.com'
    view = CustomSpectacularAPIView.as_view()
    response = view(request)
    if response.status_code == 200:
        schema = response.data if hasattr(response, 'data') else json.loads(response.content)
        paths_count = len(schema.get('paths', {}))
        print(f"✅ Schema OK: {paths_count} API paths found")
        if paths_count == 0:
            print("⚠️  WARNING: No paths! Swagger will be empty.")
        else:
            print("   First 5 paths:")
            for path in list(schema.get('paths', {}).keys())[:5]:
                print(f"      - {path}")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

