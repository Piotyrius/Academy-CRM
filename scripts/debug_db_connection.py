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
    'DATABASE_URL': os.getenv('DATABASE_URL', 'NOT SET'),
    'DB_HOST': os.getenv('DB_HOST', 'NOT SET'),
    'DB_NAME': os.getenv('DB_NAME', 'NOT SET'),
    'DB_USER': os.getenv('DB_USER', 'NOT SET'),
    'DB_PASSWORD': os.getenv('DB_PASSWORD', 'NOT SET')[:10] + '...' if os.getenv('DB_PASSWORD') else 'NOT SET',
    'DB_PORT': os.getenv('DB_PORT', 'NOT SET'),
}

for key, value in db_vars.items():
    if key == 'DATABASE_URL' and value != 'NOT SET':
        # Parse DATABASE_URL to show database name
        try:
            from urllib.parse import urlparse
            parsed = urlparse(value)
            db_name_from_url = parsed.path.lstrip('/') if parsed.path else 'NOT SPECIFIED'
            print(f"  {key}: {value[:50]}... (database: {db_name_from_url})")
        except:
            print(f"  {key}: {value[:50]}...")
    else:
        print(f"  {key}: {value}")

# 2. Check Django database settings
print("\n2. DJANGO DATABASE SETTINGS (ACTUAL CONFIGURATION):")
print("-" * 80)
db_config = settings.DATABASES['default']
print(f"  ENGINE: {db_config.get('ENGINE')}")
print(f"  NAME: {db_config.get('NAME')} ⬅️ THIS IS THE DATABASE BEING USED")
print(f"  USER: {db_config.get('USER')}")
print(f"  HOST: {db_config.get('HOST')}")
print(f"  PORT: {db_config.get('PORT')}")
print(f"  PASSWORD: {'SET' if db_config.get('PASSWORD') else 'NOT SET'}")

# 3. Test raw connection and get current database
print("\n3. TESTING RAW DATABASE CONNECTION:")
print("-" * 80)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"  ✅ Connection successful!")
        print(f"  PostgreSQL version: {version[0][:60]}...")
        
        # Get current database name
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"  📊 CURRENT DATABASE: {current_db}")
        
        # Get current user
        cursor.execute("SELECT current_user;")
        current_user = cursor.fetchone()[0]
        print(f"  👤 CURRENT USER: {current_user}")
        
        # Check if database matches expected
        expected_db = db_config.get('NAME')
        if current_db == expected_db:
            print(f"  ✅ Database matches expected: {expected_db}")
        else:
            print(f"  ⚠️  WARNING: Database mismatch!")
            print(f"     Expected: {expected_db}")
            print(f"     Actual: {current_db}")
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

# 7. Check users table and mfa_secret field
print("\n7. CHECKING USERS TABLE AND MFA_SECRET FIELD:")
print("-" * 80)
try:
    with connection.cursor() as cursor:
        # Check if users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        users_exists = cursor.fetchone()[0]
        
        if users_exists:
            # Check if mfa_secret column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users' 
                    AND column_name = 'mfa_secret'
                );
            """)
            mfa_secret_exists = cursor.fetchone()[0]
            
            print(f"  ✅ Users table exists")
            print(f"  ✅ mfa_secret column exists: {mfa_secret_exists}")
            
            if mfa_secret_exists:
                # Check data type of mfa_secret
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users' 
                    AND column_name = 'mfa_secret';
                """)
                data_type = cursor.fetchone()[0] if cursor.rowcount > 0 else None
                print(f"  📊 mfa_secret data type: {data_type}")
                
                # Check if there are any users with mfa_secret set
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE mfa_secret IS NOT NULL AND mfa_secret != '';
                """)
                users_with_mfa = cursor.fetchone()[0]
                print(f"  👥 Users with mfa_secret set: {users_with_mfa}")
                
                if users_with_mfa > 0:
                    # Try to read one mfa_secret value to test fernet_fields
                    cursor.execute("""
                        SELECT mfa_secret 
                        FROM users 
                        WHERE mfa_secret IS NOT NULL AND mfa_secret != ''
                        LIMIT 1;
                    """)
                    result = cursor.fetchone()
                    if result:
                        mfa_value = result[0]
                        print(f"  📝 Sample mfa_secret type: {type(mfa_value).__name__}")
                        print(f"  📝 Sample mfa_secret length: {len(mfa_value) if mfa_value else 0}")
        else:
            print(f"  ⚠️  Users table doesn't exist yet")
            
except Exception as e:
    print(f"  ❌ Failed to check users table: {e}")
    traceback.print_exc()

# 8. Test fernet_fields patch
print("\n8. TESTING FERNET_FIELDS PATCH:")
print("-" * 80)
try:
    import fernet_fields.fields
    print(f"  ✅ fernet_fields imported successfully")
    
    # Check if patch is applied
    if hasattr(fernet_fields.fields.FernetField, 'from_db_value'):
        print(f"  ✅ FernetField.from_db_value exists")
        # Check if it's our patched version (has specific attributes)
        import inspect
        source = inspect.getsource(fernet_fields.fields.FernetField.from_db_value)
        if 'patched_from_db_value' in source or 'base64' in source:
            print(f"  ✅ Patch appears to be applied (found patch indicators)")
        else:
            print(f"  ⚠️  Patch might not be applied (no patch indicators found)")
    else:
        print(f"  ❌ FernetField.from_db_value not found!")
        
except Exception as e:
    print(f"  ❌ Failed to check fernet_fields patch: {e}")
    traceback.print_exc()

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)

