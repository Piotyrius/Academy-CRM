"""
Pricing service for managing flexible pricing.
"""
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from catalog.models import Program, Course, Cohort
from admissions.models import Enrollment
from ..models import Pricing


class PricingService:
    """Service for pricing operations."""
    
    @staticmethod
    def get_pricing_for_enrollment(enrollment):
        """
        Get effective pricing for an enrollment.
        
        Logic: Check cohort pricing first, then course, then program (inheritance).
        Returns the most specific pricing found.
        
        Args:
            enrollment: Enrollment instance
            
        Returns:
            Pricing instance or None
        """
        cohort = enrollment.cohort
        course = cohort.course
        program = course.program
        organization = enrollment.organization
        
        today = timezone.now().date()
        
        # Check pricing in order: Cohort -> Course -> Program
        for obj in [cohort, course, program]:
            content_type = ContentType.objects.get_for_model(obj)
            
            # Find active pricing for this object
            pricing = Pricing.objects.filter(
                organization=organization,
                content_type=content_type,
                object_id=obj.id,
                is_active=True,
                effective_from__lte=today
            ).exclude(
                effective_to__lt=today
            ).order_by('-effective_from').first()
            
            if pricing:
                return pricing
        
        return None
    
    @staticmethod
    def get_pricing_amount(enrollment):
        """
        Get pricing amount for an enrollment.
        
        Args:
            enrollment: Enrollment instance
            
        Returns:
            Decimal amount or None
        """
        pricing = PricingService.get_pricing_for_enrollment(enrollment)
        return pricing.amount if pricing else None

