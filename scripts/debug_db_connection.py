"""
Debug script to test database connection.
Run this in Render shell: python scripts/debug_db_connection.py
"""
import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

from django.db import connection
from django.conf import settings
import traceback

print("=" * 80)
print("DATABASE CONNECTION DEBUG")
print("=" * 80)

# 1. Check environment variables
print("\n1. ENVIRONMENT VARIABLES:")
print("-" * 80)
db_vars = {
    'DB_HOST': os.getenv('DB_HOST', 'NOT SET'),
    'DB_NAME': os.getenv('DB_NAME', 'NOT SET'),
    'DB_USER': os.getenv('DB_USER', 'NOT SET'),
    'DB_PASSWORD': os.getenv('DB_PASSWORD', 'NOT SET')[:10] + '...' if os.getenv('DB_PASSWORD') else 'NOT SET',
    'DB_PORT': os.getenv('DB_PORT', 'NOT SET'),
}

for key, value in db_vars.items():
    print(f"  {key}: {value}")

# 2. Check Django database settings
print("\n2. DJANGO DATABASE SETTINGS:")
print("-" * 80)
db_config = settings.DATABASES['default']
print(f"  ENGINE: {db_config.get('ENGINE')}")
print(f"  NAME: {db_config.get('NAME')}")
print(f"  USER: {db_config.get('USER')}")
print(f"  HOST: {db_config.get('HOST')}")
print(f"  PORT: {db_config.get('PORT')}")
print(f"  PASSWORD: {'SET' if db_config.get('PASSWORD') else 'NOT SET'}")

# 3. Test raw connection
print("\n3. TESTING RAW DATABASE CONNECTION:")
print("-" * 80)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"  ✅ Connection successful!")
        print(f"  PostgreSQL version: {version[0]}")
except Exception as e:
    print(f"  ❌ Connection failed: {e}")
    print(f"  Error type: {type(e).__name__}")
    traceback.print_exc()

# 4. Test simple query
print("\n4. TESTING SIMPLE QUERY:")
print("-" * 80)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()
        print(f"  ✅ Query successful: {result}")
except Exception as e:
    print(f"  ❌ Query failed: {e}")
    traceback.print_exc()

# 5. Check if tables exist
print("\n5. CHECKING DATABASE TABLES:")
print("-" * 80)
try:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  ✅ Found {len(tables)} tables")
        if tables:
            print(f"  First 10 tables: {', '.join(tables[:10])}")
        else:
            print("  ⚠️  No tables found - migrations may not have run")
        
        # Check for specific tables
        important_tables = ['organizations', 'users', 'subscriptions', 'subscription_plans']
        print(f"\n  Checking important tables:")
        for table in important_tables:
            exists = table in tables
            status = "✅" if exists else "❌"
            print(f"    {status} {table}: {'EXISTS' if exists else 'NOT FOUND'}")
except Exception as e:
    print(f"  ❌ Failed to check tables: {e}")
    traceback.print_exc()

# 6. Test Django model access
print("\n6. TESTING DJANGO MODEL ACCESS:")
print("-" * 80)
try:
    from subscriptions.models import Organization
    count = Organization.objects.count()
    print(f"  ✅ Organization model accessible")
    print(f"  Organizations in database: {count}")
except Exception as e:
    print(f"  ❌ Failed to access Organization model: {e}")
    print(f"  Error type: {type(e).__name__}")
    if 'relation "organizations" does not exist' in str(e):
        print("  ⚠️  Organizations table doesn't exist - migrations need to run")
    traceback.print_exc()

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)

