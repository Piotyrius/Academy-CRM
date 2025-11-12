"""
Pytest configuration and shared fixtures for Academy CRM tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from accounts.models import Role

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        email='admin@test.com',
        password='testpass123',
        first_name='Admin',
        last_name='User',
        role=Role.ADMIN,
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def lecturer_user(db):
    """Create a lecturer user."""
    return User.objects.create_user(
        email='lecturer@test.com',
        password='testpass123',
        first_name='Lecturer',
        last_name='User',
        role=Role.LECTURER
    )


@pytest.fixture
def student_user(db):
    """Create a student user."""
    return User.objects.create_user(
        email='student@test.com',
        password='testpass123',
        first_name='Student',
        last_name='User',
        role=Role.STUDENT
    )


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def authenticated_lecturer_client(api_client, lecturer_user):
    """API client authenticated as lecturer."""
    api_client.force_authenticate(user=lecturer_user)
    return api_client


@pytest.fixture
def authenticated_student_client(api_client, student_user):
    """API client authenticated as student."""
    api_client.force_authenticate(user=student_user)
    return api_client


