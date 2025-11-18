"""
Views for subscriptions app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.http import Http404
from .models import (
    Organization, SubscriptionPlan, Subscription, PlanFeature, Billing
)
from .serializers import (
    OrganizationSerializer, SubscriptionPlanSerializer,
    SubscriptionSerializer, PlanFeatureSerializer, BillingSerializer,
    FeatureStatusSerializer
)
from .utils import get_subscription_status, AVAILABLE_MODULES


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for Organization model."""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'domain']
    
    def get_permissions(self):
        """Restrict list and write operations to admins only."""
        if self.action in ['list', 'create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        # retrieve and subscription_status are accessible to authenticated users (filtered by organization)
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter organizations based on user permissions."""
        user = self.request.user
        
        # Superusers can see all organizations
        if user.is_superuser:
            return Organization.objects.all()
        
        # Regular users can only see their own organization
        if hasattr(user, 'organization') and user.organization:
            return Organization.objects.filter(id=user.organization.id)
        
        return Organization.objects.none()
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    @action(detail=True, methods=['get'])
    def subscription_status(self, request, pk=None):
        """Get subscription status for an organization."""
        organization = self.get_object()
        status_data = get_subscription_status(organization)
        serializer = FeatureStatusSerializer({
            'organization_id': organization.id,
            **status_data,
            'all_modules': AVAILABLE_MODULES
        })
        return Response(serializer.data)


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SubscriptionPlan model (read-only for customers)."""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Restrict access to admins only."""
        if self.action in ['list', 'retrieve', 'available']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available subscription plans."""
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for Subscription model."""
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'plan']
    
    def get_permissions(self):
        """Restrict list and write operations to admins only."""
        if self.action in ['list', 'create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        # retrieve and my_subscription are accessible to authenticated users (filtered by organization)
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter subscriptions based on user permissions."""
        user = self.request.user
        
        # Superusers can see all subscriptions
        if user.is_superuser:
            return Subscription.objects.all()
        
        # Regular users can only see their organization's subscription
        if hasattr(user, 'organization') and user.organization:
            return Subscription.objects.filter(organization=user.organization)
        
        return Subscription.objects.none()
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    @action(detail=False, methods=['get'])
    def my_subscription(self, request):
        """Get current user's organization subscription."""
        user = request.user
        
        if not hasattr(user, 'organization') or not user.organization:
            return Response(
                {'error': 'User has no organization'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            subscription = user.organization.subscription
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'No subscription found for this organization'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        """Create a new subscription for an organization."""
        plan_id = request.data.get('plan_id')
        organization_id = request.data.get('organization_id')
        
        # Get organization (from request or user)
        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id)
            except Organization.DoesNotExist:
                return Response(
                    {'error': 'Organization not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif hasattr(request.user, 'organization') and request.user.organization:
            organization = request.user.organization
        else:
            return Response(
                {'error': 'Organization required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions
        if not request.user.is_superuser and organization != request.user.organization:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Plan not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(
            organization=organization,
            defaults={
                'plan': plan,
                'status': 'TRIAL' if organization.status == 'TRIAL' else 'ACTIVE'
            }
        )
        
        if not created:
            # Update existing subscription
            subscription.plan = plan
            subscription.status = 'ACTIVE'
            subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class FeatureStatusViewSet(viewsets.ViewSet):
    """ViewSet for checking feature status."""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get feature status for current organization."""
        user = request.user
        
        # Get organization from request or user
        organization = getattr(request, 'organization', None)
        if not organization and hasattr(user, 'organization'):
            organization = user.organization
        
        if not organization:
            return Response(
                {
                    'error': 'No organization found',
                    'has_subscription': False,
                    'is_active': False,
                    'status': 'NO_ORGANIZATION',
                    'plan_name': None,
                    'enabled_modules': ['accounts'],
                    'all_modules': AVAILABLE_MODULES
                },
                status=status.HTTP_200_OK
            )
        
        status_data = get_subscription_status(organization)
        serializer = FeatureStatusSerializer({
            'organization_id': organization.id,
            **status_data,
            'all_modules': AVAILABLE_MODULES
        })
        return Response(serializer.data)

