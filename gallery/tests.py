from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, Role
from .models import Work, WorkStatus


class GalleryWorkTest(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(email='stud@example.com', password='pass', role=Role.STUDENT)

    def test_create_work_draft(self):
        file = SimpleUploadedFile('test.txt', b'hello')
        work = Work.objects.create(owner=self.student, title='My work', media=file)
        self.assertEqual(work.status, WorkStatus.DRAFT)


