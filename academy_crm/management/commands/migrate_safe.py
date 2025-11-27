"""
Safe migration command that handles Guardian signal issues.
Runs migrations in the correct order to avoid Guardian querying User before organization field exists.
Also disconnects guardian signal to prevent fernet_fields encoding errors.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models.signals import post_migrate
from django.apps import apps


class Command(BaseCommand):
    help = 'Run migrations safely, handling Guardian signal issues and fernet_fields encoding errors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )

    def _disconnect_guardian_signal(self):
        """
        Disconnect guardian's post_migrate signal.
        
        This must be called before each migrate call because guardian may reconnect
        its signal when Django reloads apps during migrations.
        
        Uses the correct sender (auth app) to match how guardian connects the signal.
        """
        try:
            from guardian import management
            
            # Get the auth app config - this is the sender guardian uses
            auth_app = apps.get_app_config('auth')
            
            try:
                # Disconnect with the correct sender and dispatch_uid
                post_migrate.disconnect(
                    management.create_anonymous_user,
                    sender=auth_app,
                    dispatch_uid='guardian.management.create_anonymous_user'
                )
                self.stdout.write(self.style.WARNING('⚠️  Guardian post_migrate signal disconnected'))
                return True
            except (ValueError, TypeError) as e:
                # Signal not connected yet, that's fine
                # It might have been disconnected already or not connected yet
                self.stdout.write(self.style.WARNING(f'Guardian signal not connected (OK): {e}'))
                return False
        except ImportError:
            # Guardian not available
            return False
        except Exception as e:
            # Any other error - log but don't fail
            self.stdout.write(self.style.WARNING(f'Could not disconnect guardian signal: {e}'))
            return False

    def handle(self, *args, **options):
        noinput = options.get('noinput', False)
        noinput_flag = ['--noinput'] if noinput else []

        self.stdout.write(self.style.SUCCESS('Starting safe migration process...'))

        # Step 1: Run subscriptions migrations first (creates Organization table)
        # Disconnect guardian signal before each migrate call to prevent reconnection
        self._disconnect_guardian_signal()
        self.stdout.write(self.style.WARNING('Step 1: Running subscriptions migrations...'))
        try:
            call_command('migrate', 'subscriptions', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Subscriptions migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Subscriptions migrations failed: {e}'))
            raise

        # Step 2: Run accounts migrations (adds organization to User and converts mfa_secret)
        # Disconnect again before accounts migrations (guardian may have reconnected)
        self._disconnect_guardian_signal()
        self.stdout.write(self.style.WARNING('Step 2: Running accounts migrations...'))
        try:
            call_command('migrate', 'accounts', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Accounts migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Accounts migrations failed: {e}'))
            raise

        # Step 3: Run all other migrations
        # Disconnect again before final migrations (guardian may have reconnected)
        self._disconnect_guardian_signal()
        self.stdout.write(self.style.WARNING('Step 3: Running all other migrations...'))
        try:
            call_command('migrate', *noinput_flag, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ All migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Migrations failed: {e}'))
            raise

        self.stdout.write(self.style.SUCCESS('\n✓ All migrations completed successfully!'))

