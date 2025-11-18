"""
Utility functions for admissions app.
"""
from accounts.models import User
from catalog.models import Cohort
from .models import Enrollment, EnrollmentStatus


def is_student_enrolled(student: User, cohort: Cohort, status: str = 'ACTIVE') -> bool:
    """
    Check if student is enrolled in cohort with given status.
    
    Args:
        student: Student user instance
        cohort: Cohort instance
        status: Enrollment status to check ('ACTIVE', 'PENDING', 'WITHDRAWN', 'COMPLETED')
                Defaults to 'ACTIVE'
    
    Returns:
        bool: True if student has enrollment with specified status, False otherwise
    """
    if status == 'ACTIVE':
        enrollment_status = EnrollmentStatus.ACTIVE
    elif status == 'PENDING':
        enrollment_status = EnrollmentStatus.PENDING
    elif status == 'WITHDRAWN':
        enrollment_status = EnrollmentStatus.WITHDRAWN
    elif status == 'COMPLETED':
        enrollment_status = EnrollmentStatus.COMPLETED
    else:
        # If status is not recognized, default to ACTIVE
        enrollment_status = EnrollmentStatus.ACTIVE
    
    return Enrollment.objects.filter(
        student=student,
        cohort=cohort,
        status=enrollment_status
    ).exists()


def get_student_enrollment(student: User, cohort: Cohort):
    """
    Get enrollment instance for student in cohort, if it exists.
    
    Args:
        student: Student user instance
        cohort: Cohort instance
    
    Returns:
        Enrollment instance or None if not found
    """
    try:
        return Enrollment.objects.get(student=student, cohort=cohort)
    except Enrollment.DoesNotExist:
        return None

