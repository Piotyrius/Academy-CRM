"""
Safe migration command that handles Guardian signal issues.
Runs migrations in the correct order to avoid Guardian querying User before organization field exists.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = 'Run migrations safely, handling Guardian signal issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )

    def handle(self, *args, **options):
        noinput = options.get('noinput', False)
        noinput_flag = ['--noinput'] if noinput else []

        self.stdout.write(self.style.SUCCESS('Starting safe migration process...'))

        # Step 1: Run subscriptions migrations first (creates Organization table)
        self.stdout.write(self.style.WARNING('Step 1: Running subscriptions migrations...'))
        try:
            call_command('migrate', 'subscriptions', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Subscriptions migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Subscriptions migrations failed: {e}'))
            raise

        # Step 2: Run accounts migrations (adds organization to User before Guardian queries it)
        self.stdout.write(self.style.WARNING('Step 2: Running accounts migrations...'))
        try:
            call_command('migrate', 'accounts', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Accounts migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Accounts migrations failed: {e}'))
            raise

        # Step 3: Run all other migrations
        self.stdout.write(self.style.WARNING('Step 3: Running all other migrations...'))
        try:
            call_command('migrate', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ All migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Migrations failed: {e}'))
            raise

        self.stdout.write(self.style.SUCCESS('\n✓ All migrations completed successfully!'))

