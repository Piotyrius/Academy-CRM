"""
Email service for sending invoice emails.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from ..models import Invoice


class InvoiceEmailService:
    """Service for sending invoice-related emails."""
    
    @staticmethod
    def send_invoice_email(invoice):
        """
        Send invoice email to student.
        
        Args:
            invoice: Invoice instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        enrollment = invoice.enrollment
        student = enrollment.student
        organization = invoice.organization
        
        # Get frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://your-academy.com')
        student_portal_url = f"{frontend_url}/student-portal"
        
        # Format currency
        currency_symbol = '$' if invoice.currency == 'USD' else invoice.currency
        
        # Build email content
        subject = f"Invoice {invoice.invoice_number} - Payment Due"
        
        message = f"""Dear {student.get_full_name()},

Your invoice has been generated for your enrollment in {enrollment.cohort.course.title}.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Total Amount: {currency_symbol}{invoice.total_amount:,.2f}
- Due Date: {invoice.due_date.strftime('%B %d, %Y')}
- Payment Plan: {invoice.payment_plan.name}

Payment Status: {invoice.get_status_display()}

Please make payment by the due date to avoid any late fees.

You can view your invoice and payment history at:
{student_portal_url}

If you have any questions, please contact us.

Best regards,
{organization.name if organization else 'Academy Team'}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=False,
            )
            
            # Mark invoice as email sent
            invoice.email_sent = True
            invoice.email_sent_at = timezone.now()
            invoice.save()
            
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send invoice email to {student.email}: {e}")
            return False
    
    @staticmethod
    def send_invoice_reminder(invoice):
        """
        Send payment reminder email to student.
        
        Args:
            invoice: Invoice instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        enrollment = invoice.enrollment
        student = enrollment.student
        organization = invoice.organization
        
        # Get frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://your-academy.com')
        student_portal_url = f"{frontend_url}/student-portal"
        
        # Format currency
        currency_symbol = '$' if invoice.currency == 'USD' else invoice.currency
        
        # Calculate days until due
        days_until_due = (invoice.due_date - timezone.now().date()).days
        
        subject = f"Payment Reminder - Invoice {invoice.invoice_number}"
        
        message = f"""Dear {student.get_full_name()},

This is a reminder that your invoice payment is due soon.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Total Amount: {currency_symbol}{invoice.total_amount:,.2f}
- Amount Paid: {currency_symbol}{invoice.paid_amount:,.2f}
- Outstanding Amount: {currency_symbol}{invoice.outstanding_amount:,.2f}
- Due Date: {invoice.due_date.strftime('%B %d, %Y')}
- Days Until Due: {days_until_due} days

Please make payment by the due date to avoid any late fees.

You can view your invoice and make payment at:
{student_portal_url}

If you have any questions, please contact us.

Best regards,
{organization.name if organization else 'Academy Team'}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send invoice reminder to {student.email}: {e}")
            return False




