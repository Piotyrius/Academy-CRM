"""
Management command to assign a subscription plan to an organization.
"""
from django.core.management.base import BaseCommand, CommandError
from subscriptions.models import Organization, SubscriptionPlan, Subscription
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Assign a subscription plan to an organization'

    def add_arguments(self, parser):
        parser.add_argument('org_id', type=str, help='Organization UUID')
        parser.add_argument('plan_id', type=str, help='Subscription plan UUID')
        parser.add_argument(
            '--trial-days',
            type=int,
            help='Trial period in days (if creating new subscription)'
        )

    def handle(self, *args, **options):
        org_id = options['org_id']
        plan_id = options['plan_id']
        trial_days = options.get('trial_days')

        # Get organization
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            raise CommandError(f'Organization with ID "{org_id}" not found')

        # Get plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            raise CommandError(f'Plan with ID "{plan_id}" not found')

        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(
            organization=organization,
            defaults={
                'plan': plan,
                'status': 'TRIAL' if trial_days else 'ACTIVE',
                'trial_ends_at': timezone.now() + timedelta(days=trial_days) if trial_days else None
            }
        )

        if not created:
            # Update existing subscription
            subscription.plan = plan
            if trial_days:
                subscription.status = 'TRIAL'
                subscription.trial_ends_at = timezone.now() + timedelta(days=trial_days)
            else:
                subscription.status = 'ACTIVE'
            subscription.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} subscription for organization "{organization.name}":'
            )
        )
        self.stdout.write(f'  Plan: {plan.name}')
        self.stdout.write(f'  Status: {subscription.status}')
        if subscription.trial_ends_at:
            self.stdout.write(f'  Trial Ends: {subscription.trial_ends_at}')

