"""
Admin configuration for payments app.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    Pricing, PaymentPlan, Discount, Invoice, Payment,
    PaymentSchedule, PaymentMethod
)


@admin.register(Pricing)
class PricingAdmin(admin.ModelAdmin):
    """Admin for Pricing model."""
    list_display = ['pricing_object', 'amount', 'currency', 'effective_from', 'effective_to', 'is_active']
    list_filter = ['is_active', 'currency', 'effective_from']
    search_fields = ['amount']
    ordering = ['-effective_from']
    raw_id_fields = ['organization']


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    """Admin for PaymentPlan model."""
    list_display = ['name', 'type', 'installment_count', 'discount_percentage', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']
    raw_id_fields = ['organization']


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    """Admin for Discount model."""
    list_display = ['name', 'type', 'value', 'applicable_to', 'is_active', 'valid_from', 'valid_to']
    list_filter = ['type', 'applicable_to', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['name']
    raw_id_fields = ['organization']


class PaymentScheduleInline(admin.TabularInline):
    """Inline admin for PaymentSchedule."""
    model = PaymentSchedule
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class PaymentInline(admin.TabularInline):
    """Inline admin for Payment."""
    model = Payment
    extra = 0
    readonly_fields = ['payment_number', 'receipt_number', 'created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(SimpleHistoryAdmin):
    """Admin for Invoice model."""
    list_display = ['invoice_number', 'enrollment', 'total_amount', 'paid_amount', 'outstanding_amount', 'status', 'due_date']
    list_filter = ['status', 'due_date', 'created_at']
    search_fields = ['invoice_number', 'enrollment__student__email']
    ordering = ['-created_at']
    raw_id_fields = ['organization', 'enrollment', 'pricing', 'payment_plan']
    inlines = [PaymentScheduleInline, PaymentInline]
    
    readonly_fields = ['outstanding_amount']
    
    actions = ['mark_as_paid', 'apply_late_fees']
    
    def outstanding_amount(self, obj):
        """Display outstanding amount."""
        return obj.outstanding_amount
    outstanding_amount.short_description = 'Outstanding Amount'
    
    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid."""
        for invoice in queryset:
            invoice.status = 'PAID'
            invoice.paid_amount = invoice.total_amount
            invoice.save()
        self.message_user(request, f"{queryset.count()} invoice(s) marked as paid.")
    mark_as_paid.short_description = "Mark selected invoices as paid"
    
    def apply_late_fees(self, request, queryset):
        """Apply late fees to overdue invoices."""
        from .services.schedule_service import PaymentScheduleService
        count = 0
        for invoice in queryset:
            if invoice.status == 'OVERDUE':
                schedules = invoice.payment_schedules.filter(status='OVERDUE')
                for schedule in schedules:
                    PaymentScheduleService.apply_late_fees(schedule, late_fee_percentage=5)  # 5% late fee
                    count += 1
        self.message_user(request, f"Late fees applied to {count} schedule item(s).")
    apply_late_fees.short_description = "Apply late fees to overdue invoices"


@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin):
    """Admin for Payment model."""
    list_display = ['payment_number', 'invoice', 'student', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['payment_number', 'receipt_number', 'student__email', 'invoice__invoice_number']
    ordering = ['-payment_date']
    raw_id_fields = ['organization', 'invoice', 'student', 'recorded_by']
    readonly_fields = ['payment_number', 'receipt_number', 'created_at', 'updated_at']


@admin.register(PaymentSchedule)
class PaymentScheduleAdmin(admin.ModelAdmin):
    """Admin for PaymentSchedule model."""
    list_display = ['invoice', 'scheduled_date', 'amount', 'status', 'late_fee']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['invoice__invoice_number']
    ordering = ['scheduled_date']
    raw_id_fields = ['invoice', 'paid_payment']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin for PaymentMethod model."""
    list_display = ['name', 'code', 'is_active', 'requires_receipt']
    list_filter = ['is_active', 'requires_receipt']
    search_fields = ['name', 'code']
    ordering = ['name']
    raw_id_fields = ['organization']

