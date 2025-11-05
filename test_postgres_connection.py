"""
Test PostgreSQL connection script.
Run this to verify your database connection works.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection

try:
    # Ensure connection
    connection.ensure_connection()
    
    # Get database info
    db_info = connection.settings_dict
    engine = db_info['ENGINE']
    db_name = db_info['NAME']
    
    print("=" * 60)
    print("✅ PostgreSQL Connection Successful!")
    print("=" * 60)
    print(f"Engine: {engine}")
    print(f"Database: {db_name}")
    print(f"Host: {db_info.get('HOST', 'localhost')}")
    print(f"Port: {db_info.get('PORT', '5432')}")
    print(f"User: {db_info.get('USER', 'postgres')}")
    print("=" * 60)
    print("\n✅ You can now run migrations:")
    print("   python manage.py migrate")
    print()
    
except Exception as e:
    print("=" * 60)
    print("ERROR: Connection Failed!")
    print("=" * 60)
    print(f"Error: {str(e)}")
    print()
    print("Please check:")
    print("1. Database 'academy_crm' exists in pgAdmin")
    print("2. .env file has correct DB_PASSWORD")
    print("3. PostgreSQL service is running")
    print()
    print("To fix password:")
    print("1. Open pgAdmin")
    print("2. Right-click on PostgreSQL server -> Properties -> Connection")
    print("3. Note the password you use to connect")
    print("4. Update .env file: DB_PASSWORD=your_actual_password")
    print("=" * 60)
    sys.exit(1)
