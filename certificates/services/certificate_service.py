"""
Certificate service for eligibility checking and certificate generation.
"""
from decimal import Decimal
from django.db.models import Q, Avg, Count
from accounts.models import User
from catalog.models import Cohort
from attendance.models import AttendanceRecord, AttendanceStatus
from assessment.models import Grade
from .pdf_generator import PDFGenerator


class CertificateService:
    """Service for certificate operations."""
    
    ATTENDANCE_THRESHOLD = 80  # 80% attendance required
    GRADE_THRESHOLD = 60  # 60% weighted grade required
    
    @classmethod
    def check_eligibility(cls, student: User, cohort: Cohort) -> tuple[bool, dict]:
        """
        Check if student is eligible for certificate.
        
        Returns:
            (is_eligible, details)
        """
        details = {
            'enrolled': False,
            'enrollment_status': None,
            'attendance_percentage': 0,
            'weighted_grade': 0,
            'attendance_eligible': False,
            'grade_eligible': False,
            'eligible': False
        }
        
        # Check enrollment status first
        from admissions.utils import get_student_enrollment
        enrollment = get_student_enrollment(student, cohort)
        
        if not enrollment:
            details['eligible'] = False
            return False, details
        
        details['enrolled'] = True
        details['enrollment_status'] = enrollment.status
        
        # Student must have ACTIVE enrollment to be eligible
        from admissions.models import EnrollmentStatus
        if enrollment.status != EnrollmentStatus.ACTIVE:
            details['eligible'] = False
            return False, details
        
        # Check attendance
        total_sessions = cohort.sessions.filter(is_cancelled=False).count()
        if total_sessions > 0:
            present_count = AttendanceRecord.objects.filter(
                session__cohort=cohort,
                student=student,
                status__in=[AttendanceStatus.PRESENT, AttendanceStatus.LATE]
            ).count()
            
            attendance_percentage = (present_count / total_sessions) * 100
            details['attendance_percentage'] = float(attendance_percentage)
            details['attendance_eligible'] = attendance_percentage >= cls.ATTENDANCE_THRESHOLD
        else:
            details['attendance_eligible'] = False
        
        # Check grades
        assessments = cohort.assessments.filter(published=True)
        if assessments.exists():
            total_weight = Decimal('0')
            weighted_score = Decimal('0')
            
            for assessment in assessments:
                try:
                    grade = Grade.objects.get(assessment=assessment, student=student)
                    percentage = grade.percentage
                    weight = Decimal(str(assessment.weight))
                    weighted_score += (percentage * weight / 100)
                    total_weight += weight
                except Grade.DoesNotExist:
                    pass
            
            if total_weight > 0:
                weighted_grade = (weighted_score / total_weight) * 100
                details['weighted_grade'] = float(weighted_grade)
                details['grade_eligible'] = weighted_grade >= cls.GRADE_THRESHOLD
            else:
                details['grade_eligible'] = False
        else:
            details['grade_eligible'] = False
        
        details['eligible'] = details['attendance_eligible'] and details['grade_eligible']
        
        return details['eligible'], details
    
    @classmethod
    def issue_certificate(cls, student: User, cohort: Cohort, force: bool = False) -> 'Certificate':
        """
        Issue certificate for student.
        
        Args:
            student: Student user
            cohort: Cohort
            force: Force issue even if not eligible (admin override)
        
        Returns:
            Certificate instance
        """
        from certificates.models import Certificate, CertificateStatus
        
        # Check if certificate already exists
        cert, created = Certificate.objects.get_or_create(
            student=student,
            cohort=cohort,
            defaults={'status': CertificateStatus.ISSUED}
        )
        
        if not created and cert.status == CertificateStatus.REVOKED:
            # Re-issue revoked certificate
            cert.status = CertificateStatus.ISSUED
            cert.revoked_at = None
            cert.revoked_reason = ''
            cert.save()
        
        # Generate PDF if not exists
        if not cert.pdf_file or not cert.pdf_file.name:
            pdf_generator = PDFGenerator(cert)
            pdf_file = pdf_generator.generate()
            cert.pdf_file = pdf_file
            cert.save()
        
        return cert
