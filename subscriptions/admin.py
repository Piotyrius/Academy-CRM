"""
Admin interface for subscriptions app.
"""
from django.contrib import admin
from .models import (
    Organization, SubscriptionPlan, Subscription, PlanFeature, Billing
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin for Organization model."""
    list_display = ['name', 'domain', 'status', 'created_at', 'trial_ends_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'domain']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'domain', 'status')
        }),
        ('Trial Information', {
            'fields': ('trial_ends_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class PlanFeatureInline(admin.TabularInline):
    """Inline admin for PlanFeature."""
    model = PlanFeature
    extra = 1
    fields = ['module_name', 'enabled']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """Admin for SubscriptionPlan model."""
    list_display = ['name', 'price', 'billing_cycle', 'is_active', 'created_at']
    list_filter = ['is_active', 'billing_cycle', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PlanFeatureInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price', 'billing_cycle')
        }),
        ('Limits', {
            'fields': ('max_users', 'max_students')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for Subscription model."""
    list_display = [
        'organization', 'plan', 'status', 'start_date', 'end_date', 'is_active'
    ]
    list_filter = ['status', 'plan', 'auto_renew', 'created_at']
    search_fields = ['organization__name', 'plan__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'is_active', 'is_trial']
    
    fieldsets = (
        ('Subscription Information', {
            'fields': ('id', 'organization', 'plan', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'trial_ends_at', 'cancelled_at')
        }),
        ('Settings', {
            'fields': ('auto_renew',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_trial')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    """Admin for Billing model."""
    list_display = [
        'organization', 'subscription', 'amount', 'status',
        'due_date', 'payment_date'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['organization__name', 'invoice_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Billing Information', {
            'fields': ('id', 'organization', 'subscription', 'amount', 'status')
        }),
        ('Payment Details', {
            'fields': ('payment_date', 'due_date', 'payment_method', 'invoice_number')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

