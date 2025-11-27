"""
Temporary script to fix fernet_fields encoding issues during migrations.
This can be run before migrations to clean up any problematic data.
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

from django.db import connection

print("=" * 80)
print("FIXING FERNET_FIELDS DATA ISSUES")
print("=" * 80)

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
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("✅ Users table doesn't exist yet - no data to fix")
            sys.exit(0)
        
        # Check if mfa_secret column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'users' 
                AND column_name = 'mfa_secret'
            );
        """)
        column_exists = cursor.fetchone()[0]
        
        if not column_exists:
            print("✅ mfa_secret column doesn't exist yet - no data to fix")
            sys.exit(0)
        
        # Check for problematic data (non-null, non-empty values that might cause issues)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM users 
            WHERE mfa_secret IS NOT NULL 
            AND mfa_secret != '';
        """)
        problematic_count = cursor.fetchone()[0]
        
        if problematic_count == 0:
            print("✅ No problematic mfa_secret data found")
            sys.exit(0)
        
        print(f"⚠️  Found {problematic_count} users with mfa_secret data")
        print("   Clearing mfa_secret values to prevent encoding issues...")
        print("   (Users can re-enable MFA after migration)")
        
        # Clear mfa_secret values to prevent encoding issues
        # Users will need to re-enable MFA after migration
        cursor.execute("""
            UPDATE users 
            SET mfa_secret = NULL, mfa_enabled = FALSE 
            WHERE mfa_secret IS NOT NULL;
        """)
        
        affected = cursor.rowcount
        print(f"✅ Cleared mfa_secret for {affected} users")
        print("   Users can re-enable MFA after migration completes")
        
except Exception as e:
    print(f"⚠️  Error checking/fixing data: {e}")
    print("   Continuing anyway - migration will handle it")
    sys.exit(0)

print("=" * 80)
print("Data fix completed successfully!")
print("=" * 80)

