"""
Payment service for managing payments.
"""
import uuid
from decimal import Decimal
from django.utils import timezone
from ..models import Payment, PaymentStatus, PaymentMethodCode
from .invoice_service import InvoiceService


class PaymentService:
    """Service for payment operations."""
    
    @staticmethod
    def generate_payment_number(organization):
        """
        Generate unique payment number.
        
        Format: PAY-{ORG_IDENTIFIER}-{YYYYMMDD}-{RANDOM}
        
        Args:
            organization: Organization instance
            
        Returns:
            str: Unique payment number
        """
        # Use domain or first 4 chars of name as identifier
        org_identifier = organization.domain[:4].upper() if organization.domain else organization.name[:4].upper().replace(' ', '')
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:8].upper()
        return f"PAY-{org_identifier}-{date_str}-{random_str}"
    
    @staticmethod
    def generate_receipt_number(organization):
        """
        Generate unique receipt number.
        
        Format: RCP-{ORG_IDENTIFIER}-{YYYYMMDD}-{RANDOM}
        
        Args:
            organization: Organization instance
            
        Returns:
            str: Unique receipt number
        """
        # Use domain or first 4 chars of name as identifier
        org_identifier = organization.domain[:4].upper() if organization.domain else organization.name[:4].upper().replace(' ', '')
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:8].upper()
        return f"RCP-{org_identifier}-{date_str}-{random_str}"
    
    @staticmethod
    def record_payment(invoice, amount, payment_method, recorded_by, **kwargs):
        """
        Record a manual payment.
        
        Args:
            invoice: Invoice instance
            amount: Decimal payment amount
            payment_method: Payment method code
            recorded_by: User instance (admin)
            **kwargs: Additional fields (notes, gateway_transaction_id, etc.)
            
        Returns:
            Payment instance
        """
        # Validate amount
        outstanding = InvoiceService.calculate_outstanding_amount(invoice)
        if amount > outstanding:
            raise ValueError(f"Payment amount ({amount}) exceeds outstanding amount ({outstanding})")
        
        # Generate payment number
        payment_number = PaymentService.generate_payment_number(invoice.organization)
        
        # Generate receipt number if needed
        receipt_number = None
        if kwargs.get('requires_receipt', False):
            receipt_number = PaymentService.generate_receipt_number(invoice.organization)
        
        # Create payment
        payment = Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            student=invoice.enrollment.student,
            payment_number=payment_number,
            amount=amount,
            currency=invoice.pricing.currency,
            payment_method=payment_method,
            payment_gateway=kwargs.get('payment_gateway', 'MANUAL'),
            gateway_transaction_id=kwargs.get('gateway_transaction_id'),
            gateway_response=kwargs.get('gateway_response'),
            status=PaymentStatus.COMPLETED,  # Manual payments are immediately completed
            payment_date=kwargs.get('payment_date', timezone.now()),
            recorded_by=recorded_by,
            receipt_number=receipt_number,
            notes=kwargs.get('notes', ''),
        )
        
        # Update invoice
        InvoiceService.calculate_outstanding_amount(invoice)
        InvoiceService.update_invoice_status(invoice)
        
        return payment
    
    @staticmethod
    def process_refund(payment, amount, reason, recorded_by):
        """
        Process a refund for a payment.
        
        Args:
            payment: Payment instance
            amount: Decimal refund amount
            reason: str refund reason
            recorded_by: User instance (admin)
            
        Returns:
            Payment instance (updated)
        """
        if amount > payment.amount:
            raise ValueError("Refund amount cannot exceed payment amount")
        
        if amount > (payment.amount - payment.refund_amount):
            raise ValueError("Refund amount exceeds remaining refundable amount")
        
        payment.refund_amount = amount
        payment.refund_reason = reason
        payment.status = PaymentStatus.REFUNDED
        payment.save()
        
        # Update invoice
        InvoiceService.calculate_outstanding_amount(payment.invoice)
        InvoiceService.update_invoice_status(payment.invoice)
        
        return payment
    
    @staticmethod
    def apply_payment_to_schedule(payment, schedule_item):
        """
        Link a payment to a payment schedule item.
        
        Args:
            payment: Payment instance
            schedule_item: PaymentSchedule instance
        """
        schedule_item.paid_payment = payment
        schedule_item.status = 'PAID'
        schedule_item.save()

