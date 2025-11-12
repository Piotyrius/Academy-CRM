"""
Comprehensive tests for attendance app.
"""
import pytest
from datetime import date, datetime, timedelta
from rest_framework import status
from attendance.models import AttendanceRecord, AttendanceStatus
from catalog.models import Program, Course, Cohort, Session
from accounts.models import Role


@pytest.mark.django_db
class TestAttendanceAPI:
    """Test Attendance endpoints."""
    
    def test_create_attendance_record(self, authenticated_admin_client, student_user, lecturer_user):
        """Test creating an attendance record."""
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
        start_at = datetime.now() + timedelta(days=1)
        end_at = start_at + timedelta(hours=2)
        session = Session.objects.create(
            cohort=cohort,
            start_at=start_at,
            end_at=end_at
        )
        
        response = authenticated_admin_client.post('/api/v1/attendance/attendance/', {
            'session': str(session.id),
            'student': str(student_user.id),
            'status': AttendanceStatus.PRESENT,
            'marked_by': str(lecturer_user.id)
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert AttendanceRecord.objects.filter(session=session, student=student_user).exists()
    
    def test_list_attendance_records(self, authenticated_admin_client, student_user):
        """Test listing attendance records."""
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
        start_at = datetime.now() + timedelta(days=1)
        end_at = start_at + timedelta(hours=2)
        session = Session.objects.create(
            cohort=cohort,
            start_at=start_at,
            end_at=end_at
        )
        
        AttendanceRecord.objects.create(
            session=session,
            student=student_user,
            status=AttendanceStatus.PRESENT
        )
        
        response = authenticated_admin_client.get('/api/v1/attendance/attendance/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_update_attendance_status(self, authenticated_admin_client, student_user, lecturer_user):
        """Test updating attendance status."""
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
        start_at = datetime.now() + timedelta(days=1)
        end_at = start_at + timedelta(hours=2)
        session = Session.objects.create(
            cohort=cohort,
            start_at=start_at,
            end_at=end_at
        )
        
        record = AttendanceRecord.objects.create(
            session=session,
            student=student_user,
            status=AttendanceStatus.PRESENT,
            marked_by=lecturer_user
        )
        
        response = authenticated_admin_client.patch(
            f'/api/v1/attendance/attendance/{record.id}/',
            {'status': AttendanceStatus.LATE}
        )
        assert response.status_code == status.HTTP_200_OK
        record.refresh_from_db()
        assert record.status == AttendanceStatus.LATE
