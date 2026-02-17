"""
Serializers for subscriptions app.
"""
from rest_framework import serializers
from .models import (
    Organization, SubscriptionPlan, Subscription, PlanFeature, Billing
)
from .utils import get_subscription_status, AVAILABLE_MODULES


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""
    subscription_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'domain', 'status', 'created_at', 'updated_at',
            'trial_ends_at', 'subscription_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_subscription_status(self, obj):
        """Get subscription status for this organization."""
        return get_subscription_status(obj)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for SubscriptionPlan model."""
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price', 'billing_cycle',
            'is_active', 'max_users', 'max_students', 'features',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_features(self, obj):
        """Get enabled features for this plan."""
        features = PlanFeature.objects.filter(plan=obj, enabled=True)
        return [
            {
                'module_name': f.module_name,
                'enabled': f.enabled
            }
            for f in features
        ]


class PlanFeatureSerializer(serializers.ModelSerializer):
    """Serializer for PlanFeature model."""
    
    class Meta:
        model = PlanFeature
        fields = ['id', 'plan', 'module_name', 'enabled', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model."""
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_trial = serializers.BooleanField(read_only=True)
    enabled_modules = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'organization', 'plan', 'plan_details', 'status',
            'start_date', 'end_date', 'trial_ends_at', 'auto_renew',
            'cancelled_at', 'is_active', 'is_trial', 'enabled_modules',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'start_date', 'created_at', 'updated_at',
            'is_active', 'is_trial'
        ]
    
    def get_enabled_modules(self, obj):
        """Get enabled modules for this subscription."""
        from .utils import get_enabled_modules
        return get_enabled_modules(obj.organization)


class BillingSerializer(serializers.ModelSerializer):
    """Serializer for Billing model."""
    
    class Meta:
        model = Billing
        fields = [
            'id', 'organization', 'subscription', 'amount', 'status',
            'payment_date', 'due_date', 'invoice_number', 'payment_method',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeatureStatusSerializer(serializers.Serializer):
    """Serializer for feature status endpoint."""
    organization_id = serializers.UUIDField()
    has_subscription = serializers.BooleanField()
    is_active = serializers.BooleanField()
    status = serializers.CharField()
    plan_name = serializers.CharField(allow_null=True)
    enabled_modules = serializers.ListField(child=serializers.CharField())
    all_modules = serializers.ListField(child=serializers.CharField())


class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer for creating a subscription."""
    plan_id = serializers.UUIDField()
    organization_id = serializers.UUIDField(required=False)

