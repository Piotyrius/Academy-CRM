"""
Management command to add missing Cloudinary columns to storage_files table.
This fixes the issue where migration 0002 hasn't been applied but columns are needed.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Add missing Cloudinary columns to storage_files table if they don\'t exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Checking Storage Cloudinary Columns'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')
        
        columns_to_add = [
            {
                'name': 'cloudinary_public_id',
                'type': 'VARCHAR(512)',
                'index': True,
            },
            {
                'name': 'cloudinary_folder',
                'type': 'VARCHAR(512)',
                'index': False,
            },
            {
                'name': 'cloudinary_url',
                'type': 'VARCHAR(1024)',
                'index': False,
            },
            {
                'name': 'cloudinary_resource_type',
                'type': 'VARCHAR(20) DEFAULT \'image\'',
                'index': False,
            },
        ]
        
        with connection.cursor() as cursor:
            # Check which columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'storage_files'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            
            columns_added = []
            indexes_created = []
            
            for col_def in columns_to_add:
                col_name = col_def['name']
                
                if col_name in existing_columns:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Column {col_name} already exists')
                    )
                else:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Would add column: {col_name} ({col_def["type"]})')
                        )
                    else:
                        try:
                            # Add column
                            sql = f'ALTER TABLE storage_files ADD COLUMN {col_name} {col_def["type"]}'
                            cursor.execute(sql)
                            columns_added.append(col_name)
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Added column: {col_name}')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'❌ Failed to add column {col_name}: {e}')
                            )
                            continue
                
                # Create index if needed
                if col_def.get('index') and col_name not in existing_columns:
                    index_name = f'storage_files_{col_name}_idx'
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Would create index: {index_name}')
                        )
                    else:
                        try:
                            cursor.execute(
                                f'CREATE INDEX IF NOT EXISTS {index_name} ON storage_files({col_name})'
                            )
                            indexes_created.append(index_name)
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Created index: {index_name}')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'❌ Failed to create index {index_name}: {e}')
                            )
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN COMPLETE - No changes made'))
            elif columns_added or indexes_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully added {len(columns_added)} columns and '
                        f'{len(indexes_created)} indexes'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ All Cloudinary columns already exist!')
                )
            
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            # Verify
            self.stdout.write('')
            self.stdout.write('Verifying columns...')
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'storage_files'
                AND column_name LIKE 'cloudinary%'
                ORDER BY column_name
            """)
            cloudinary_columns = [row[0] for row in cursor.fetchall()]
            
            if cloudinary_columns:
                self.stdout.write('Cloudinary columns found:')
                for col in cloudinary_columns:
                    self.stdout.write(f'  ✅ {col}')
            else:
                self.stdout.write(
                    self.style.ERROR('❌ No Cloudinary columns found!')
                )
            
            # Fix drive_file_id and drive_folder_id to allow NULL
            self.stdout.write('')
            self.stdout.write('Checking drive_file_id and drive_folder_id constraints...')
            
            try:
                # Check if drive_file_id allows NULL
                cursor.execute("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'storage_files' 
                    AND column_name = 'drive_file_id'
                """)
                result = cursor.fetchone()
                if result and result[0] == 'NO':
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING('⚠️  Would make drive_file_id nullable')
                        )
                    else:
                        cursor.execute(
                            'ALTER TABLE storage_files ALTER COLUMN drive_file_id DROP NOT NULL'
                        )
                        self.stdout.write(
                            self.style.SUCCESS('✅ Made drive_file_id nullable')
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('✅ drive_file_id already allows NULL')
                    )
                
                # Check if drive_folder_id allows NULL
                cursor.execute("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'storage_files' 
                    AND column_name = 'drive_folder_id'
                """)
                result = cursor.fetchone()
                if result and result[0] == 'NO':
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING('⚠️  Would make drive_folder_id nullable')
                        )
                    else:
                        cursor.execute(
                            'ALTER TABLE storage_files ALTER COLUMN drive_folder_id DROP NOT NULL'
                        )
                        self.stdout.write(
                            self.style.SUCCESS('✅ Made drive_folder_id nullable')
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('✅ drive_folder_id already allows NULL')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error checking/fixing drive columns: {e}')
                )

