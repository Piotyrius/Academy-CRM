"""
Clear mfa_secret data using raw SQL before migrations run.
This prevents fernet_fields encoding errors when guardian queries User during migrations.
Uses psycopg2 directly to avoid Django setup issues.
"""
import os
import sys

try:
    import psycopg2
    from urllib.parse import urlparse
except ImportError:
    print("⚠️  psycopg2 not available, skipping data clear")
    print("   This is OK if the database is fresh")
    sys.exit(0)

print("=" * 80)
print("CLEARING MFA_SECRET DATA (Pre-Migration)")
print("=" * 80)

# Get database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Fallback to individual variables
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'academy_crm'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
    }
else:
    # Parse DATABASE_URL
    parsed = urlparse(DATABASE_URL)
    db_config = {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password,
    }

try:
    # Connect directly with psycopg2 (no Django needed)
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
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
        print("✅ Users table doesn't exist yet - no data to clear")
        conn.close()
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
        print("✅ mfa_secret column doesn't exist yet - no data to clear")
        conn.close()
        sys.exit(0)
    
    # Check for data
    cursor.execute("""
        SELECT COUNT(*) 
        FROM users 
        WHERE mfa_secret IS NOT NULL 
        AND mfa_secret != '';
    """)
    data_count = cursor.fetchone()[0]
    
    if data_count == 0:
        print("✅ No mfa_secret data to clear")
        conn.close()
        sys.exit(0)
    
    print(f"⚠️  Found {data_count} users with mfa_secret data")
    print("   Clearing to prevent encoding errors during migrations...")
    print("   (Users can re-enable MFA after migration)")
    
    # Clear mfa_secret values using raw SQL
    cursor.execute("""
        UPDATE users 
        SET mfa_secret = NULL, mfa_enabled = FALSE 
        WHERE mfa_secret IS NOT NULL;
    """)
    
    affected = cursor.rowcount
    conn.commit()
    print(f"✅ Cleared mfa_secret for {affected} users")
    
    conn.close()
    
except Exception as e:
    print(f"⚠️  Error clearing data: {e}")
    print("   Continuing anyway - migration will handle it")
    sys.exit(0)

print("=" * 80)
print("Data clear completed!")
print("=" * 80)

