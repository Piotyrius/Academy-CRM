"""
Management command to fix admin accounts after permission system update.

This command ensures that:
1. Users with is_superuser=True have role=ADMIN
2. Users with role=ADMIN have is_staff=True (for Django admin access)
3. Users with role=ADMIN have is_superuser=True (for backward compatibility)
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix admin accounts to ensure proper role and permission assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Fix 1: Users with is_superuser=True should have role=ADMIN
        superusers = User.objects.filter(is_superuser=True).exclude(role=Role.ADMIN)
        count1 = superusers.count()
        
        if count1 > 0:
            self.stdout.write(f'\nFound {count1} superuser(s) without ADMIN role:')
            for user in superusers:
                self.stdout.write(f'  - {user.email} (current role: {user.role})')
                if not dry_run:
                    user.role = Role.ADMIN
                    user.save(update_fields=['role'])
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Updated role to ADMIN'))
                else:
                    self.stdout.write(self.style.WARNING(f'    [DRY RUN] Would update role to ADMIN'))
        
        # Fix 2: Users with role=ADMIN should have is_staff=True
        admin_users = User.objects.filter(role=Role.ADMIN).exclude(is_staff=True)
        count2 = admin_users.count()
        
        if count2 > 0:
            self.stdout.write(f'\nFound {count2} admin user(s) without is_staff=True:')
            for user in admin_users:
                self.stdout.write(f'  - {user.email}')
                if not dry_run:
                    user.is_staff = True
                    user.save(update_fields=['is_staff'])
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Set is_staff=True'))
                else:
                    self.stdout.write(self.style.WARNING(f'    [DRY RUN] Would set is_staff=True'))
        
        # Fix 3: Users with role=ADMIN should have is_superuser=True (for backward compatibility)
        admin_users_no_super = User.objects.filter(role=Role.ADMIN).exclude(is_superuser=True)
        count3 = admin_users_no_super.count()
        
        if count3 > 0:
            self.stdout.write(f'\nFound {count3} admin user(s) without is_superuser=True:')
            for user in admin_users_no_super:
                self.stdout.write(f'  - {user.email}')
                if not dry_run:
                    user.is_superuser = True
                    user.save(update_fields=['is_superuser'])
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Set is_superuser=True'))
                else:
                    self.stdout.write(self.style.WARNING(f'    [DRY RUN] Would set is_superuser=True'))
        
        # Summary
        total_fixed = count1 + count2 + count3
        if total_fixed == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ All admin accounts are properly configured!'))
        else:
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\n[DRY RUN] Would fix {total_fixed} issue(s)'))
                self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
            else:
                self.stdout.write(self.style.SUCCESS(f'\n✓ Fixed {total_fixed} issue(s)'))

