"""
Safe migration command that disables guardian signal before running migrations.
This prevents fernet_fields encoding errors when guardian queries User model.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models.signals import post_migrate


class Command(BaseCommand):
    help = 'Run migrations safely, disabling guardian signal to prevent fernet_fields errors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            'app_label',
            nargs='?',
            help='App label to migrate (optional)',
        )

    def handle(self, *args, **options):
        noinput = options.get('noinput', False)
        noinput_flag = ['--noinput'] if noinput else []
        app_label = options.get('app_label')
        
        # Disconnect guardian's signal before migrations
        try:
            from guardian import management
            
            # Disconnect the signal
            try:
                post_migrate.disconnect(
                    management.create_anonymous_user,
                    dispatch_uid='guardian.management.create_anonymous_user'
                )
                self.stdout.write(self.style.WARNING('Guardian post_migrate signal disconnected'))
            except (ValueError, TypeError):
                # Signal not connected yet, that's fine
                self.stdout.write(self.style.WARNING('Guardian signal not connected (OK)'))
        except ImportError:
            # Guardian not available
            pass
        
        # Run migrations
        if app_label:
            call_command('migrate', app_label, *noinput_flag, verbosity=1)
        else:
            call_command('migrate', *noinput_flag, verbosity=1)
        
        self.stdout.write(self.style.SUCCESS('Migrations completed successfully'))
