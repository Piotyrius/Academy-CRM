"""
Safe migration command that handles Guardian signal issues.
Runs migrations in the correct order to avoid Guardian querying User before organization field exists.
Also disconnects guardian signal to prevent fernet_fields encoding errors.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models.signals import post_migrate


class Command(BaseCommand):
    help = 'Run migrations safely, handling Guardian signal issues and fernet_fields encoding errors'

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

        # Disconnect guardian's signal as backup (AppConfig.ready() should handle this, but this ensures it)
        try:
            from guardian import management
            
            try:
                post_migrate.disconnect(
                    management.create_anonymous_user,
                    dispatch_uid='guardian.management.create_anonymous_user'
                )
                self.stdout.write(self.style.WARNING('⚠️  Guardian post_migrate signal disconnected'))
            except (ValueError, TypeError):
                # Signal not connected yet, that's fine
                # AppConfig.ready() might have already disconnected it, or it's not connected
                pass
        except ImportError:
            # Guardian not available
            pass

        # Step 1: Run subscriptions migrations first (creates Organization table)
        self.stdout.write(self.style.WARNING('Step 1: Running subscriptions migrations...'))
        try:
            call_command('migrate', 'subscriptions', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Subscriptions migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Subscriptions migrations failed: {e}'))
            raise

        # Step 2: Run accounts migrations (adds organization to User and converts mfa_secret)
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

