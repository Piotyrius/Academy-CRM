"""
Management command to create a new organization/tenant.
"""
from django.core.management.base import BaseCommand, CommandError
from subscriptions.models import Organization, SubscriptionPlan, Subscription
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Create a new organization/tenant'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Organization name')
        parser.add_argument(
            '--domain',
            type=str,
            help='Subdomain for this organization (optional)'
        )
        parser.add_argument(
            '--plan',
            type=str,
            help='UUID of subscription plan to assign (optional)'
        )
        parser.add_argument(
            '--trial-days',
            type=int,
            default=30,
            help='Trial period in days (default: 30)'
        )

    def handle(self, *args, **options):
        name = options['name']
        domain = options.get('domain')
        plan_id = options.get('plan')
        trial_days = options['trial_days']

        # Check if domain is already taken
        if domain:
            if Organization.objects.filter(domain=domain).exists():
                raise CommandError(f'Organization with domain "{domain}" already exists')

        # Create organization
        organization = Organization.objects.create(
            name=name,
            domain=domain,
            status='TRIAL',
            trial_ends_at=timezone.now() + timedelta(days=trial_days)
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created organization: {organization.name} (ID: {organization.id})')
        )

        # Assign plan if provided
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id)
                subscription = Subscription.objects.create(
                    organization=organization,
                    plan=plan,
                    status='TRIAL',
                    trial_ends_at=organization.trial_ends_at
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Assigned plan: {plan.name} to organization')
                )
            except SubscriptionPlan.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Plan with ID {plan_id} not found. Organization created without plan.')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nOrganization Details:')
        )
        self.stdout.write(f'  ID: {organization.id}')
        self.stdout.write(f'  Name: {organization.name}')
        if domain:
            self.stdout.write(f'  Domain: {domain}')
        self.stdout.write(f'  Status: {organization.status}')
        self.stdout.write(f'  Trial Ends: {organization.trial_ends_at}')

