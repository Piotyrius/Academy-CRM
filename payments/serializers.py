"""
Serializers for payments app.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Pricing, PaymentPlan, Discount, Invoice, Payment,
    PaymentSchedule, PaymentMethod
)


class PricingSerializer(serializers.ModelSerializer):
    """Serializer for Pricing model."""
    pricing_object_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Pricing
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_pricing_object_name(self, obj):
        """Get name of the pricing object."""
        return str(obj.pricing_object) if obj.pricing_object else None


class PaymentPlanSerializer(serializers.ModelSerializer):
    """Serializer for PaymentPlan model."""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = PaymentPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DiscountSerializer(serializers.ModelSerializer):
    """Serializer for Discount model."""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    applicable_to_display = serializers.CharField(source='get_applicable_to_display', read_only=True)
    
    class Meta:
        model = Discount
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model."""
    outstanding_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='enrollment.student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='enrollment.student.email', read_only=True)
    cohort_name = serializers.CharField(source='enrollment.cohort.name', read_only=True)
    payment_plan_name = serializers.CharField(source='payment_plan.name', read_only=True)
    
    def get_payment_status_display(self, obj):
        """Get payment status display."""
        from django.utils import timezone
        if obj.outstanding_amount <= 0:
            return 'PAID'
        elif obj.paid_amount > 0:
            return 'PARTIAL'
        elif timezone.now().date() > obj.due_date:
            return 'OVERDUE'
        else:
            return 'UNPAID'
    
    def get_days_until_due(self, obj):
        """Calculate days until due date."""
        from django.utils import timezone
        delta = obj.due_date - timezone.now().date()
        return delta.days
    
    def get_is_overdue(self, obj):
        """Check if invoice is overdue."""
        from django.utils import timezone
        return timezone.now().date() > obj.due_date and obj.outstanding_amount > 0
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['id', 'invoice_number', 'outstanding_amount', 'created_at', 'updated_at', 'payment_status_display', 'days_until_due', 'is_overdue']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['id', 'payment_number', 'receipt_number', 'created_at', 'updated_at']


class PaymentScheduleSerializer(serializers.ModelSerializer):
    """Serializer for PaymentSchedule model."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    
    class Meta:
        model = PaymentSchedule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod model."""
    
    class Meta:
        model = PaymentMethod
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

