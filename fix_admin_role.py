"""
Script to verify and fix admin user role
"""
from accounts.models import User, Role

# Find the admin user
try:
    admin = User.objects.get(email='admin@academy.ge')
    print(f"Found admin user: {admin.email}")
    print(f"Current role: {admin.role}")
    print(f"Is staff: {admin.is_staff}")
    print(f"Is superuser: {admin.is_superuser}")
    
    # Fix the role if needed
    if admin.role != Role.ADMIN:
        print(f"\n⚠️  Admin role is incorrect! Fixing...")
        admin.role = Role.ADMIN
        admin.save()
        print(f"✅ Admin role updated to: {admin.role}")
    else:
        print(f"\n✅ Admin role is correct: {admin.role}")
        
except User.DoesNotExist:
    print("❌ Admin user not found!")
