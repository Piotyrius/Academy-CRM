"""
Management command to check Google Drive storage and show how to access files.

This command shows:
- Service account email
- Root folder ID and link
- Storage quota information
- How to access the service account's Drive
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from academy_crm.google_drive import get_drive_service_or_none, is_drive_enabled


class Command(BaseCommand):
    help = 'Check Google Drive storage configuration and show how to access files'

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Google Drive Storage Information'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        if not is_drive_enabled():
            self.stdout.write(self.style.ERROR('❌ Google Drive is not enabled'))
            self.stdout.write('')
            self.stdout.write('To enable Google Drive, set these environment variables:')
            self.stdout.write('  - USE_GOOGLE_DRIVE_STORAGE=true')
            self.stdout.write('  - GOOGLE_DRIVE_CLIENT_EMAIL=your-service-account@project.iam.gserviceaccount.com')
            self.stdout.write('  - GOOGLE_DRIVE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----...')
            self.stdout.write('  - GOOGLE_DRIVE_PROJECT_ID=your-project-id')
            self.stdout.write('  - GOOGLE_DRIVE_ROOT_FOLDER_ID=your-folder-id')
            return

        # Show service account email
        service_account_email = getattr(settings, 'GOOGLE_DRIVE_CLIENT_EMAIL', '')
        self.stdout.write(f'📧 Service Account Email:')
        self.stdout.write(f'   {service_account_email}')
        self.stdout.write('')

        # Show root folder
        root_folder_id = getattr(settings, 'GOOGLE_DRIVE_ROOT_FOLDER_ID', '')
        root_folder_link = f'https://drive.google.com/drive/folders/{root_folder_id}'
        self.stdout.write(f'📁 Root Folder ID:')
        self.stdout.write(f'   {root_folder_id}')
        self.stdout.write(f'   Link: {root_folder_link}')
        self.stdout.write('')

        # Try to get storage quota
        drive = get_drive_service_or_none()
        if drive:
            self.stdout.write('📊 Storage Quota:')
            try:
                quota = drive.get_storage_quota()
                if quota:
                    limit = quota.get('limit')
                    usage = quota.get('usage', 0)
                    usage_in_drive = quota.get('usageInDrive', 0)
                    usage_in_trash = quota.get('usageInDriveTrash', 0)

                    if limit:
                        limit_gb = limit / (1024 ** 3)
                        usage_gb = usage / (1024 ** 3)
                        usage_drive_gb = usage_in_drive / (1024 ** 3)
                        usage_trash_gb = usage_in_trash / (1024 ** 3)
                        percent = (usage / limit * 100) if limit > 0 else 0

                        self.stdout.write(f'   Total Limit: {limit_gb:.2f} GB')
                        self.stdout.write(f'   Total Used: {usage_gb:.2f} GB ({percent:.1f}%)')
                        self.stdout.write(f'   Used in Drive: {usage_drive_gb:.2f} GB')
                        if usage_trash_gb > 0:
                            self.stdout.write(f'   Used in Trash: {usage_trash_gb:.2f} GB')
                        
                        if usage >= limit:
                            self.stdout.write(self.style.ERROR('   ⚠️  STORAGE QUOTA EXCEEDED!'))
                        elif percent > 90:
                            self.stdout.write(self.style.WARNING('   ⚠️  Storage almost full!'))
                    else:
                        self.stdout.write('   Unlimited (Shared Drive)')
                        if usage_in_drive > 0:
                            usage_drive_gb = usage_in_drive / (1024 ** 3)
                            self.stdout.write(f'   Used in Drive: {usage_drive_gb:.2f} GB')
                else:
                    self.stdout.write('   Could not retrieve quota information')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'   Could not get quota: {e}'))
        else:
            self.stdout.write(self.style.ERROR('   Could not connect to Google Drive'))

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('How to Access Service Account Files'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write('The files are stored in the SERVICE ACCOUNT\'s Google Drive,')
        self.stdout.write('NOT in your personal Google Drive account.')
        self.stdout.write('')
        self.stdout.write('Method 1: Share Root Folder with Your Personal Account')
        self.stdout.write('  1. Go to Google Cloud Console: https://console.cloud.google.com')
        self.stdout.write('  2. Navigate to: IAM & Admin → Service Accounts')
        self.stdout.write(f'  3. Find service account: {service_account_email}')
        self.stdout.write('  4. Click on it to see details')
        self.stdout.write('  5. You need to share the root folder with your personal account:')
        self.stdout.write('     - Go to: https://drive.google.com')
        self.stdout.write(f'     - Open folder: {root_folder_link}')
        self.stdout.write('     - Click "Share" and add your personal Google account')
        self.stdout.write('     - Give yourself "Editor" or "Viewer" permissions')
        self.stdout.write('')
        self.stdout.write('Method 2: Use Google Cloud Console (Limited)')
        self.stdout.write('  1. Go to: https://console.cloud.google.com')
        self.stdout.write('  2. Navigate to: IAM & Admin → Service Accounts')
        self.stdout.write(f'  3. Find: {service_account_email}')
        self.stdout.write('  4. Click "Actions" → "Manage Keys" (but this won\'t show Drive files)')
        self.stdout.write('')
        self.stdout.write('Method 3: Use Google Drive API (Recommended for Admins)')
        self.stdout.write('  - Use the root folder link above if you have access')
        self.stdout.write('  - Or create a script to list files using the service account')
        self.stdout.write('')
        self.stdout.write('Method 4: Share Root Folder via Service Account')
        self.stdout.write('  1. Create a folder in YOUR personal Google Drive')
        self.stdout.write('  2. Share it with the service account email (above)')
        self.stdout.write('  3. Give the service account "Editor" permissions')
        self.stdout.write('  4. Update GOOGLE_DRIVE_ROOT_FOLDER_ID to the new folder ID')
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write('💡 TIP: The easiest way is Method 1 - share the root folder')
        self.stdout.write('        with your personal account so you can access it directly.')
        self.stdout.write('')
