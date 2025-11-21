"""
Payment schedule service for managing payment schedules.
"""
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from calendar import monthrange
from ..models import PaymentSchedule, PaymentScheduleStatus, Invoice
from .invoice_service import InvoiceService


class PaymentScheduleService:
    """Service for payment schedule operations."""
    
    @staticmethod
    def create_payment_schedule(invoice, payment_plan):
        """
        Generate payment schedule for an invoice based on payment plan.
        
        Args:
            invoice: Invoice instance
            payment_plan: PaymentPlan instance
            
        Returns:
            List of PaymentSchedule instances
        """
        # Delete existing schedules if any
        invoice.payment_schedules.all().delete()
        
        schedules = []
        today = timezone.now().date()
        
        if payment_plan.type == 'FULL':
            # Single payment for full amount
            schedule = PaymentSchedule.objects.create(
                invoice=invoice,
                scheduled_date=invoice.due_date,
                amount=invoice.total_amount,
                status=PaymentScheduleStatus.PENDING,
            )
            schedules.append(schedule)
        
        elif payment_plan.type == 'MONTHLY':
            # Monthly installments
            installment_count = payment_plan.installment_count
            amount_per_installment = invoice.total_amount / Decimal(str(installment_count))
            
            # Round to 2 decimal places
            amount_per_installment = amount_per_installment.quantize(Decimal('0.01'))
            
            # Calculate remainder for last payment
            total_scheduled = amount_per_installment * Decimal(str(installment_count - 1))
            last_payment_amount = invoice.total_amount - total_scheduled
            
            # Create schedule items
            current_date = invoice.due_date
            for i in range(installment_count):
                if i == installment_count - 1:
                    # Last payment gets the remainder
                    amount = last_payment_amount
                else:
                    amount = amount_per_installment
                
                schedule = PaymentSchedule.objects.create(
                    invoice=invoice,
                    scheduled_date=current_date,
                    amount=amount,
                    status=PaymentScheduleStatus.PENDING,
                )
                schedules.append(schedule)
                
                # Move to next month
                # Calculate next month manually
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    # Get last day of next month to handle edge cases
                    next_month = current_date.month + 1
                    last_day = monthrange(current_date.year, next_month)[1]
                    day = min(current_date.day, last_day)
                    current_date = current_date.replace(month=next_month, day=day)
        
        else:  # CUSTOM
            # For custom plans, create a single schedule item
            # Admin can manually adjust as needed
            schedule = PaymentSchedule.objects.create(
                invoice=invoice,
                scheduled_date=invoice.due_date,
                amount=invoice.total_amount,
                status=PaymentScheduleStatus.PENDING,
            )
            schedules.append(schedule)
        
        return schedules
    
    @staticmethod
    def check_overdue_payments():
        """
        Check and mark overdue payment schedules.
        
        Returns:
            int: Number of schedules marked as overdue
        """
        today = timezone.now().date()
        overdue_schedules = PaymentSchedule.objects.filter(
            status=PaymentScheduleStatus.PENDING,
            scheduled_date__lt=today
        )
        
        count = 0
        for schedule in overdue_schedules:
            schedule.status = PaymentScheduleStatus.OVERDUE
            schedule.save()
            count += 1
            
            # Update invoice status
            InvoiceService.update_invoice_status(schedule.invoice)
        
        return count
    
    @staticmethod
    def apply_late_fees(schedule_item, late_fee_amount=None, late_fee_percentage=None):
        """
        Apply late fees to a payment schedule item.
        
        Args:
            schedule_item: PaymentSchedule instance
            late_fee_amount: Decimal fixed late fee amount (optional)
            late_fee_percentage: Decimal late fee percentage (optional)
            
        Returns:
            Decimal: Late fee amount applied
        """
        if late_fee_amount:
            late_fee = late_fee_amount
        elif late_fee_percentage:
            late_fee = schedule_item.amount * (late_fee_percentage / Decimal('100'))
        else:
            return Decimal('0.00')
        
        schedule_item.late_fee = late_fee
        schedule_item.save()
        
        # Update invoice total (add late fee to total amount)
        invoice = schedule_item.invoice
        invoice.total_amount += late_fee
        invoice.save()
        
        return late_fee

