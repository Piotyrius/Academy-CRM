from accounts.models import User

# Create admin user
user = User.objects.create_user(
    email='admin@academy.ge',
    password='admin123',
    first_name='Admin',
    last_name='User',
    role='admin',
    is_staff=True,
    is_superuser=True
)
print(f"✅ Superuser created: {user.email}")
print(f"Email: admin@academy.ge")
print(f"Password: admin123")
