"""
Invoice service for managing invoices.
"""
import uuid
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from ..models import Invoice, InvoiceStatus
from .pricing_service import PricingService
from .discount_service import DiscountService


class InvoiceService:
    """Service for invoice operations."""
    
    @staticmethod
    def generate_invoice_number(organization):
        """
        Generate unique invoice number.
        
        Format: INV-{ORG_IDENTIFIER}-{YYYYMMDD}-{RANDOM}
        
        Args:
            organization: Organization instance
            
        Returns:
            str: Unique invoice number
        """
        # Use domain or first 4 chars of name as identifier
        org_identifier = organization.domain[:4].upper() if organization.domain else organization.name[:4].upper().replace(' ', '')
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:8].upper()
        return f"INV-{org_identifier}-{date_str}-{random_str}"
    
    @staticmethod
    def create_invoice_for_enrollment(enrollment, payment_plan, discounts=None):
        """
        Create invoice for an enrollment.
        
        Args:
            enrollment: Enrollment instance
            payment_plan: PaymentPlan instance
            discounts: List of Discount instances (optional)
            
        Returns:
            Invoice instance
        """
        if discounts is None:
            discounts = []
        
        # Get pricing
        pricing = PricingService.get_pricing_for_enrollment(enrollment)
        if not pricing:
            raise ValueError("No pricing found for this enrollment")
        
        # Calculate subtotal (apply payment plan discount if applicable)
        subtotal = pricing.amount
        if payment_plan.discount_percentage > 0:
            plan_discount = subtotal * (payment_plan.discount_percentage / Decimal('100'))
            subtotal = subtotal - plan_discount
        
        # Create invoice
        invoice = Invoice.objects.create(
            organization=enrollment.organization,
            enrollment=enrollment,
            invoice_number=InvoiceService.generate_invoice_number(enrollment.organization),
            pricing=pricing,
            payment_plan=payment_plan,
            subtotal=subtotal,
            discount_amount=Decimal('0.00'),
            total_amount=subtotal,
            paid_amount=Decimal('0.00'),
            status=InvoiceStatus.DRAFT,
            due_date=timezone.now().date(),  # Will be updated based on payment plan
            issued_at=None,
        )
        
        # Apply discounts
        if discounts:
            student = enrollment.student
            applicable_discounts = DiscountService.get_applicable_discounts(
                invoice, student, enrollment
            )
            DiscountService.apply_discounts_to_invoice(invoice, applicable_discounts)
            invoice.save()
        
        return invoice
    
    @staticmethod
    def calculate_outstanding_amount(invoice):
        """
        Calculate outstanding amount for an invoice.
        
        Args:
            invoice: Invoice instance
            
        Returns:
            Decimal: Outstanding amount
        """
        # Recalculate paid amount from payments
        total_paid = invoice.payments.filter(
            status='COMPLETED'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Subtract refunds
        total_refunded = invoice.payments.filter(
            status='REFUNDED'
        ).aggregate(
            total=Sum('refund_amount')
        )['total'] or Decimal('0.00')
        
        net_paid = total_paid - total_refunded
        invoice.paid_amount = net_paid
        invoice.save()
        
        return invoice.outstanding_amount
    
    @staticmethod
    def update_invoice_status(invoice):
        """
        Auto-update invoice status based on payments.
        
        Args:
            invoice: Invoice instance
        """
        outstanding = InvoiceService.calculate_outstanding_amount(invoice)
        
        if outstanding <= 0:
            invoice.status = InvoiceStatus.PAID
        elif invoice.paid_amount > 0:
            invoice.status = InvoiceStatus.PARTIAL
        elif timezone.now().date() > invoice.due_date and outstanding > 0:
            invoice.status = InvoiceStatus.OVERDUE
        elif invoice.status == InvoiceStatus.DRAFT:
            invoice.status = InvoiceStatus.ISSUED
        
        invoice.save()
    
    @staticmethod
    def issue_invoice(invoice):
        """
        Issue an invoice (change status from DRAFT to ISSUED).
        
        Args:
            invoice: Invoice instance
        """
        if invoice.status == InvoiceStatus.DRAFT:
            invoice.status = InvoiceStatus.ISSUED
            invoice.issued_at = timezone.now()
            invoice.save()

