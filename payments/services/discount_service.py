"""
Discount service for managing discounts.
"""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
from ..models import Discount, Invoice, DiscountType, DiscountApplicableTo
from admissions.models import Enrollment


class DiscountService:
    """Service for discount operations."""
    
    @staticmethod
    def get_applicable_discounts(invoice, student, enrollment):
        """
        Find applicable discounts for an invoice.
        
        Checks:
        - Sibling discounts (other enrollments by family)
        - Full payment discounts
        - Custom discounts
        
        Args:
            invoice: Invoice instance
            student: User instance (student)
            enrollment: Enrollment instance
            
        Returns:
            List of applicable Discount instances
        """
        organization = invoice.organization
        now = timezone.now()
        applicable_discounts = []
        
        # Get all active discounts for organization
        discounts = Discount.objects.filter(
            organization=organization,
            is_active=True,
            valid_from__lte=now
        ).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=now)
        )
        
        for discount in discounts:
            is_applicable = False
            
            # Check full payment discount
            if discount.applicable_to == DiscountApplicableTo.FULL_PAYMENT:
                if invoice.payment_plan.type == 'FULL':
                    is_applicable = True
            
            # Check sibling discount
            elif discount.applicable_to == DiscountApplicableTo.SIBLING:
                # Check if student has siblings enrolled
                # This is a simplified check - you may need to enhance based on your family relationship model
                sibling_enrollments = Enrollment.objects.filter(
                    organization=organization,
                    status='ACTIVE'
                ).exclude(id=enrollment.id)
                
                # For now, we'll check if there are other active enrollments
                # You may want to add a family/relationship field to User model
                if sibling_enrollments.exists():
                    is_applicable = True
            
            # Check custom discount
            elif discount.applicable_to == DiscountApplicableTo.CUSTOM:
                # Custom logic - check minimum amount
                if discount.min_amount:
                    if invoice.subtotal >= discount.min_amount:
                        is_applicable = True
                else:
                    is_applicable = True
            
            if is_applicable:
                applicable_discounts.append(discount)
        
        return applicable_discounts
    
    @staticmethod
    def calculate_discount_amount(discount, invoice):
        """
        Calculate discount amount for an invoice.
        
        Args:
            discount: Discount instance
            invoice: Invoice instance
            
        Returns:
            Decimal discount amount
        """
        if discount.type == DiscountType.PERCENTAGE:
            discount_amount = invoice.subtotal * (discount.value / Decimal('100'))
        else:  # FIXED_AMOUNT
            discount_amount = discount.value
        
        # Apply maximum discount cap if set
        if discount.max_discount:
            discount_amount = min(discount_amount, discount.max_discount)
        
        # Ensure discount doesn't exceed subtotal
        discount_amount = min(discount_amount, invoice.subtotal)
        
        return discount_amount
    
    @staticmethod
    def apply_discounts_to_invoice(invoice, discounts):
        """
        Apply multiple discounts to an invoice and calculate total.
        
        Args:
            invoice: Invoice instance
            discounts: List of Discount instances
            
        Returns:
            Total discount amount applied
        """
        total_discount = Decimal('0.00')
        remaining_subtotal = invoice.subtotal
        
        for discount in discounts:
            discount_amount = DiscountService.calculate_discount_amount(discount, invoice)
            
            # Ensure we don't exceed the subtotal
            if discount_amount > remaining_subtotal:
                discount_amount = remaining_subtotal
            
            total_discount += discount_amount
            remaining_subtotal -= discount_amount
            
            if remaining_subtotal <= 0:
                break
        
        invoice.discount_amount = total_discount
        invoice.total_amount = invoice.subtotal - total_discount
        
        return total_discount

