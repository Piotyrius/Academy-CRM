"""
Comprehensive tests for admissions app.
"""
import pytest
from datetime import date, timedelta
from rest_framework import status
from admissions.models import Application, Enrollment, ApplicationStatus, EnrollmentStatus
from catalog.models import Program, Course, Cohort, CohortStatus
from accounts.models import Role


@pytest.mark.django_db
class TestApplicationAPI:
    """Test Application endpoints."""
    
    def test_create_application(self, authenticated_admin_client):
        """Test creating an application."""
        program = Program.objects.create(name='Test Program', code='TP')
        response = authenticated_admin_client.post('/api/v1/admissions/applications/', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'program': str(program.id),
            'status': ApplicationStatus.NEW
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Application.objects.filter(email='john@example.com').exists()
    
    def test_list_applications(self, authenticated_admin_client):
        """Test listing applications."""
        program = Program.objects.create(name='Test Program', code='TP')
        Application.objects.create(
            name='App 1',
            email='app1@test.com',
            phone='123',
            program=program
        )
        Application.objects.create(
            name='App 2',
            email='app2@test.com',
            phone='456',
            program=program
        )
        
        response = authenticated_admin_client.get('/api/v1/admissions/applications/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2
    
    def test_accept_application(self, authenticated_admin_client):
        """Test accepting an application and creating enrollment."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        program = Program.objects.create(name='Test Program', code='TP')
        course = Course.objects.create(program=program, title='Test Course', code='TC', hours=40)
        start_date = date.today()
        end_date = start_date + timedelta(days=90)
        cohort = Cohort.objects.create(
            course=course,
            name='Test Cohort',
            capacity=20,
            start_date=start_date,
            end_date=end_date
        )
        
        application = Application.objects.create(
            name='John Doe',
            email='john@test.com',
            phone='123',
            program=program,
            status=ApplicationStatus.ACCEPTED  # Set status to ACCEPTED first
        )
        
        # The endpoint will create a student user if it doesn't exist
        response = authenticated_admin_client.post(
            f'/api/v1/admissions/applications/{application.id}/accept/',
            {'cohort_id': str(cohort.id)},
            format='json'
        )
        # Should return 200 or 201 depending on whether enrollment was created
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        # Enrollment should be created (either for existing or newly created student)
        assert Enrollment.objects.filter(cohort=cohort).exists()


@pytest.mark.django_db
class TestEnrollmentAPI:
    """Test Enrollment endpoints."""
    
    def test_create_enrollment(self, authenticated_admin_client, student_user):
        """Test creating an enrollment."""
        program = Program.objects.create(name='Test Program', code='TP')
        course = Course.objects.create(program=program, title='Test Course', code='TC', hours=40)
        start_date = date.today()
        end_date = start_date + timedelta(days=90)
        cohort = Cohort.objects.create(
            course=course,
            name='Test Cohort',
            capacity=20,
            start_date=start_date,
            end_date=end_date
        )
        
        response = authenticated_admin_client.post('/api/v1/admissions/enrollments/', {
            'student': str(student_user.id),
            'cohort': str(cohort.id),
            'status': EnrollmentStatus.PENDING
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Enrollment.objects.filter(student=student_user, cohort=cohort).exists()
    
    def test_activate_enrollment(self, authenticated_admin_client, student_user):
        """Test activating an enrollment."""
        program = Program.objects.create(name='Test Program', code='TP')
        course = Course.objects.create(program=program, title='Test Course', code='TC', hours=40)
        start_date = date.today()
        end_date = start_date + timedelta(days=90)
        cohort = Cohort.objects.create(
            course=course,
            name='Test Cohort',
            capacity=20,
            start_date=start_date,
            end_date=end_date
        )
        
        enrollment = Enrollment.objects.create(
            student=student_user,
            cohort=cohort,
            status=EnrollmentStatus.PENDING
        )
        
        response = authenticated_admin_client.post(
            f'/api/v1/admissions/enrollments/{enrollment.id}/activate/'
        )
        assert response.status_code == status.HTTP_200_OK
        enrollment.refresh_from_db()
        assert enrollment.status == EnrollmentStatus.ACTIVE
