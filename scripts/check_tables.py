"""
Quick script to check if required tables exist.
Run: python scripts/check_tables.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

from django.db import connection

print("=" * 60)
print("CHECKING REQUIRED TABLES")
print("=" * 60)

required_tables = [
    'organizations',
    'subscription_plans',
    'subscriptions',
    'plan_features',
    'billings',
    'users',
]

try:
    with connection.cursor() as cursor:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\nTotal tables in database: {len(existing_tables)}\n")
        
        print("Required tables status:")
        print("-" * 60)
        all_exist = True
        for table in required_tables:
            exists = table in existing_tables
            status = "✅" if exists else "❌"
            print(f"  {status} {table}")
            if not exists:
                all_exist = False
        
        if all_exist:
            print("\n✅ All required tables exist!")
        else:
            print("\n⚠️  Some tables are missing - migrations may not have run")
            print("   Run: python manage.py migrate")
        
        # Show subscriptions-related tables
        print("\nSubscriptions-related tables:")
        print("-" * 60)
        sub_tables = [t for t in existing_tables if 'subscription' in t or 'organization' in t or 'billing' in t or 'plan' in t]
        for table in sorted(sub_tables):
            print(f"  ✅ {table}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("=" * 60)

