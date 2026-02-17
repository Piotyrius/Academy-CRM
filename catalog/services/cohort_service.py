"""
Cohort service for automatic cohort creation and management.
"""
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from ..models import Cohort, CohortStatus
from admissions.models import EnrollmentStatus


class CohortService:
    """Service for cohort operations."""
    
    @staticmethod
    def get_or_create_cohort_for_course(course, organization):
        """
        Get an available cohort for a course or create a new one.
        
        Args:
            course: Course instance
            organization: Organization instance
            
        Returns:
            Cohort instance
        """
        # Try to find an available cohort
        cohort = CohortService.find_available_cohort(course, organization)
        
        if cohort:
            return cohort
        
        # No available cohort, create a new one
        return CohortService.create_new_cohort(course, organization)
    
    @staticmethod
    def find_available_cohort(course, organization):
        """
        Find an available cohort for a course that has capacity.
        
        Args:
            course: Course instance
            organization: Organization instance
            
        Returns:
            Cohort instance or None
        """
        # Find cohorts that:
        # 1. Are for this course
        # 2. Are in PLANNED or ENROLLING status
        # 3. Have capacity available
        # 4. Belong to the same organization
        
        from django.db.models import Count, Q
        
        cohorts = Cohort.objects.filter(
            course=course,
            organization=organization,
            status__in=[CohortStatus.PLANNED, CohortStatus.ENROLLING]
        ).annotate(
            active_enrollments_count=Count(
                'enrollments',
                filter=Q(enrollments__status=EnrollmentStatus.ACTIVE)
            )
        )
        
        # Filter cohorts that have capacity
        for cohort in cohorts:
            if cohort.active_enrollments_count < cohort.capacity:
                return cohort
        
        return None
    
    @staticmethod
    def create_new_cohort(course, organization):
        """
        Create a new cohort for a course with default settings.
        
        Args:
            course: Course instance
            organization: Organization instance
            
        Returns:
            Cohort instance
        """
        # Generate cohort name: Course Title - YYYY-MM-DD
        date_str = timezone.now().strftime('%Y-%m-%d')
        cohort_name = f"{course.title} - {date_str}"
        
        # Set default dates (start 1 month from now, end 3 months from start)
        start_date = timezone.now().date() + timedelta(days=30)
        end_date = start_date + timedelta(days=90)
        
        cohort = Cohort.objects.create(
            course=course,
            organization=organization,
            name=cohort_name,
            capacity=20,  # Default max capacity
            min_enrollment=8,  # Default min enrollment
            start_date=start_date,
            end_date=end_date,
            status=CohortStatus.PLANNED
        )
        
        return cohort
    
    @staticmethod
    def check_and_notify_readiness(cohort):
        """
        Check if cohort has reached minimum enrollment and notify admins.
        
        Args:
            cohort: Cohort instance
        """
        if cohort.is_ready_to_start:
            # Import here to avoid circular imports
            from notifications.services.notification_service import NotificationService
            NotificationService.notify_cohort_ready(cohort)
    
    @staticmethod
    def create_invoices_for_cohort_enrollments(cohort):
        """
        Create invoices for all enrollments in a cohort that don't have invoices.
        
        Args:
            cohort: Cohort instance
        """
        from payments.services.invoice_service import InvoiceService
        
        enrollments = cohort.enrollments.filter(
            status=EnrollmentStatus.ACTIVE
        ).select_related('student', 'organization')
        
        for enrollment in enrollments:
            # Check if enrollment already has an invoice
            if not enrollment.invoices.exists():
                try:
                    InvoiceService.create_invoice_for_enrollment_auto(
                        enrollment, 
                        enrollment.organization
                    )
                except Exception as e:
                    # Log error but continue with other enrollments
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create invoice for enrollment {enrollment.id}: {e}")

