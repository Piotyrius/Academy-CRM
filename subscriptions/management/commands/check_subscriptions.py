"""
Management command to check and update subscription statuses.
"""
from django.core.management.base import BaseCommand
from subscriptions.models import Subscription, SubscriptionStatus
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check and update subscription statuses (expired, trial ended, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Actually update expired subscriptions (default: dry run)'
        )

    def handle(self, *args, **options):
        update = options['update']
        now = timezone.now()

        # Find expired subscriptions
        expired = Subscription.objects.filter(
            status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL],
            end_date__lt=now
        )

        # Find trial subscriptions that ended
        trial_ended = Subscription.objects.filter(
            status=SubscriptionStatus.TRIAL,
            trial_ends_at__lt=now
        )

        self.stdout.write('Subscription Status Check:')
        self.stdout.write('=' * 50)

        if expired.exists():
            self.stdout.write(f'\nFound {expired.count()} expired subscriptions:')
            for sub in expired:
                self.stdout.write(f'  - {sub.organization.name}: {sub.plan.name} (ended: {sub.end_date})')
                if update:
                    sub.status = SubscriptionStatus.EXPIRED
                    sub.save()
                    self.stdout.write(self.style.SUCCESS(f'    -> Updated to EXPIRED'))
        else:
            self.stdout.write('\nNo expired subscriptions found.')

        if trial_ended.exists():
            self.stdout.write(f'\nFound {trial_ended.count()} trial subscriptions that ended:')
            for sub in trial_ended:
                self.stdout.write(f'  - {sub.organization.name}: {sub.plan.name} (trial ended: {sub.trial_ends_at})')
                if update:
                    sub.status = SubscriptionStatus.EXPIRED
                    sub.save()
                    self.stdout.write(self.style.SUCCESS(f'    -> Updated to EXPIRED'))
        else:
            self.stdout.write('\nNo trial subscriptions that ended found.')

        if not update:
            self.stdout.write('\n' + self.style.WARNING('DRY RUN - No changes made. Use --update to apply changes.'))

