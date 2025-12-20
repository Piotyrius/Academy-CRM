"""
Management command to send invoice emails.
Runs daily to send invoices created in the last week that haven't been sent yet.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from payments.models import Invoice, InvoiceStatus
from payments.services.email_service import InvoiceEmailService


class Command(BaseCommand):
    help = 'Send invoice emails for invoices created in the last week that haven\'t been sent yet'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for unsent invoices (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Find invoices created in the last N days that haven't been sent
        cutoff_date = timezone.now() - timedelta(days=days)
        
        invoices = Invoice.objects.filter(
            created_at__gte=cutoff_date,
            email_sent=False,
            status__in=[InvoiceStatus.ISSUED, InvoiceStatus.PARTIAL]  # Only send issued invoices
        ).select_related('enrollment', 'enrollment__student', 'organization')
        
        count = invoices.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would send {count} invoice emails'
                )
            )
            for invoice in invoices[:10]:  # Show first 10
                self.stdout.write(
                    f'  - Invoice {invoice.invoice_number} to {invoice.enrollment.student.email}'
                )
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
            return
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No invoices to send'))
            return
        
        self.stdout.write(f'Sending {count} invoice emails...')
        
        sent_count = 0
        failed_count = 0
        
        for invoice in invoices:
            if InvoiceEmailService.send_invoice_email(invoice):
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Sent invoice {invoice.invoice_number} to {invoice.enrollment.student.email}'
                    )
                )
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to send invoice {invoice.invoice_number} to {invoice.enrollment.student.email}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted: {sent_count} sent, {failed_count} failed'
            )
        )




