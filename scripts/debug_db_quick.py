"""
Quick one-liner database connection test.
Run in Render shell: python scripts/debug_db_quick.py
Or paste this in shell:
python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings'); django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT version()'); print('✅ DB Connected:', cursor.fetchone()[0][:50])"
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

from django.db import connection
from django.conf import settings

print("=" * 60)
print("QUICK DB CONNECTION TEST")
print("=" * 60)

print(f"\nDB_HOST: {settings.DATABASES['default']['HOST']}")
print(f"DB_NAME: {settings.DATABASES['default']['NAME']}")
print(f"DB_USER: {settings.DATABASES['default']['USER']}")

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n✅ Connection OK!")
        print(f"PostgreSQL: {version[:60]}...")
        
        # Check tables
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        table_count = cursor.fetchone()[0]
        print(f"\nTables in database: {table_count}")
        
        # Check organizations table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'organizations'
            );
        """)
        org_exists = cursor.fetchone()[0]
        print(f"Organizations table exists: {'✅ YES' if org_exists else '❌ NO'}")
        
except Exception as e:
    print(f"\n❌ Connection FAILED: {e}")
    print(f"Error type: {type(e).__name__}")

print("=" * 60)

