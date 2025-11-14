from accounts.models import User, Role

# Fix admin user role
admin = User.objects.get(email='admin@academy.ge')
print(f"Before: role = '{admin.role}'")

admin.role = Role.ADMIN
admin.save()

print(f"After: role = '{admin.role}'")
print(f"Role now matches ADMIN: {admin.role == Role.ADMIN}")
print("\n✅ Admin user role fixed! Please logout and login again in the browser.")

