"""
Management command to check migration status.
Useful for verifying if all migrations have been applied on Render or other deployments.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.apps import apps
from django.db.migrations.recorder import MigrationRecorder
from io import StringIO


class Command(BaseCommand):
    help = 'Check migration status for all apps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Check migrations for a specific app only',
        )
        parser.add_argument(
            '--show-pending',
            action='store_true',
            help='Show only pending migrations',
        )

    def handle(self, *args, **options):
        app_label = options.get('app')
        show_pending_only = options.get('show_pending', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Migration Status Check'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Get all installed apps
        if app_label:
            apps_to_check = [apps.get_app_config(app_label)]
        else:
            apps_to_check = apps.get_app_configs()
        
        # Filter out apps without migrations
        apps_with_migrations = []
        for app_config in apps_to_check:
            if hasattr(app_config, 'models_module') and app_config.models_module:
                try:
                    # Check if app has migrations directory
                    import os
                    migrations_path = os.path.join(
                        os.path.dirname(app_config.path),
                        'migrations'
                    )
                    if os.path.exists(migrations_path):
                        apps_with_migrations.append(app_config)
                except Exception:
                    pass
        
        total_pending = 0
        total_applied = 0
        
        for app_config in apps_with_migrations:
            app_name = app_config.label
            self.stdout.write(f'\n📦 App: {self.style.WARNING(app_name)}')
            
            # Use showmigrations to get status
            try:
                output = StringIO()
                call_command('showmigrations', app_name, stdout=output, stderr=output, no_color=True, verbosity=0)
                output.seek(0)
                content = output.getvalue()
                lines = content.split('\n')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error checking migrations: {e}')
                )
                continue
            
            pending = []
            applied = []
            
            # Parse showmigrations output
            # Format can be:
            # gallery
            #  [X] 0001_initial
            #  [X] 0002_work_file_object
            #  [ ] 0003_alter_work_file_object
            # Or just:
            #  [X] 0001_initial
            #  [X] 0002_work_file_object
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip the app name line (if present)
                if line == app_name or line.startswith(app_name + '.'):
                    continue
                
                # Parse migration status lines
                # Look for [X], [x], [ ], or other bracket patterns
                if '[' in line and ']' in line:
                    bracket_start = line.index('[')
                    bracket_end = line.index(']')
                    status = line[bracket_start + 1:bracket_end].strip()
                    migration_name = line[bracket_end + 1:].strip()
                    
                    # Remove app prefix if present (e.g., "gallery.0001_initial" -> "0001_initial")
                    if '.' in migration_name:
                        migration_name = migration_name.split('.', 1)[1]
                    
                    if migration_name:  # Only process if we have a migration name
                        if status.upper() == 'X':
                            applied.append(migration_name)
                            total_applied += 1
                        else:
                            pending.append(migration_name)
                            total_pending += 1
            
            # If showmigrations didn't find anything, try direct database check
            if not applied and not pending:
                try:
                    # Check database directly for applied migrations
                    recorder = MigrationRecorder(connection)
                    applied_migrations = recorder.applied_migrations()
                    app_migrations = [
                        name for app, name in applied_migrations 
                        if app == app_name
                    ]
                    if app_migrations:
                        applied = sorted(app_migrations)
                        total_applied += len(applied)
                        # Also check what migrations exist in the filesystem
                        import os
                        migrations_path = os.path.join(
                            os.path.dirname(app_config.path),
                            'migrations'
                        )
                        if os.path.exists(migrations_path):
                            migration_files = [
                                f.replace('.py', '') 
                                for f in os.listdir(migrations_path)
                                if f.endswith('.py') and f != '__init__.py'
                            ]
                            for mig_file in sorted(migration_files):
                                if mig_file not in applied:
                                    pending.append(mig_file)
                                    total_pending += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠️  Could not check database: {e}')
                    )
            
            if not show_pending_only or pending:
                if applied:
                    self.stdout.write(f'  ✅ Applied ({len(applied)}): {", ".join(applied)}')
                if pending:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Pending ({len(pending)}): {", ".join(pending)}')
                    )
                elif not applied and not pending:
                    self.stdout.write('  ℹ️  No migrations found')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(
            self.style.SUCCESS(f'Summary: {total_applied} applied, {total_pending} pending')
        )
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if total_pending > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR('⚠️  WARNING: There are pending migrations!')
            )
            self.stdout.write('   Run: python manage.py migrate')
            return 1
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ All migrations are applied!'))
            return 0

