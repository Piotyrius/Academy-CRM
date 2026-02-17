from django.test import TestCase
from django.utils import timezone
from accounts.models import User, Role
from catalog.models import Program, Course, Cohort, Session
from .models import WorkLog


class WorkLogGenerationTest(TestCase):
    def setUp(self):
        self.lecturer = User.objects.create_user(email='lect@example.com', password='pass', role=Role.LECTURER)
        prog = Program.objects.create(name='P', code='P1')
        course = Course.objects.create(program=prog, title='C', code='C1', hours=10)
        self.cohort = Cohort.objects.create(course=course, name='T1', lecturer=self.lecturer, capacity=10, start_date=timezone.now().date(), end_date=timezone.now().date())

    def test_session_save_creates_worklog(self):
        start = timezone.now()
        end = start + timezone.timedelta(hours=2)
        session = Session.objects.create(cohort=self.cohort, start_at=start, end_at=end)
        self.assertTrue(WorkLog.objects.filter(session=session, lecturer=self.lecturer).exists())


