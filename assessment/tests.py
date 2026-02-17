"""
Comprehensive tests for assessment app.
"""
import pytest
from datetime import date, datetime, timedelta
from rest_framework import status
from assessment.models import Assessment, Submission, Grade, AssessmentKind
from catalog.models import Program, Course, Cohort
from accounts.models import Role


@pytest.mark.django_db
class TestAssessmentAPI:
    """Test Assessment endpoints."""
    
    def test_create_assessment(self, authenticated_admin_client):
        """Test creating an assessment."""
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
        
        due_at = datetime.now() + timedelta(days=7)
        response = authenticated_admin_client.post('/api/v1/assessment/assessments/', {
            'cohort': str(cohort.id),
            'title': 'Midterm Exam',
            'kind': AssessmentKind.EXAM,
            'weight': 30.0,
            'due_at': due_at.isoformat(),
            'published': True,
            'description': 'Midterm examination'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Assessment.objects.filter(title='Midterm Exam').exists()
    
    def test_list_assessments(self, authenticated_admin_client):
        """Test listing assessments."""
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
        
        due_at = datetime.now() + timedelta(days=7)
        Assessment.objects.create(
            cohort=cohort,
            title='Assessment 1',
            kind=AssessmentKind.QUIZ,
            weight=10.0,
            due_at=due_at
        )
        
        response = authenticated_admin_client.get('/api/v1/assessment/assessments/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1


@pytest.mark.django_db
class TestSubmissionAPI:
    """Test Submission endpoints."""
    
    def test_create_submission(self, authenticated_student_client, student_user):
        """Test creating a submission."""
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
        due_at = datetime.now() + timedelta(days=7)
        assessment = Assessment.objects.create(
            cohort=cohort,
            title='Test Assessment',
            kind=AssessmentKind.QUIZ,
            weight=10.0,
            due_at=due_at,
            published=True
        )
        
        response = authenticated_student_client.post('/api/v1/assessment/submissions/', {
            'assessment': str(assessment.id),
            'student': str(student_user.id),
            'notes': 'My submission notes'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Submission.objects.filter(assessment=assessment, student=student_user).exists()


@pytest.mark.django_db
class TestGradeAPI:
    """Test Grade endpoints."""
    
    def test_create_grade(self, authenticated_admin_client, student_user):
        """Test creating a grade."""
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
        due_at = datetime.now() + timedelta(days=7)
        assessment = Assessment.objects.create(
            cohort=cohort,
            title='Test Assessment',
            kind=AssessmentKind.QUIZ,
            weight=10.0,
            due_at=due_at
        )
        
        response = authenticated_admin_client.post('/api/v1/assessment/grades/', {
            'assessment': str(assessment.id),
            'student': str(student_user.id),
            'score': 85,
            'max_score': 100
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Grade.objects.filter(assessment=assessment, student=student_user).exists()
        grade = Grade.objects.get(assessment=assessment, student=student_user)
        assert float(grade.percentage) == 85.0
