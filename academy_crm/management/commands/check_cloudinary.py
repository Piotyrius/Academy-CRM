"""
Management command to test Cloudinary integration and functionality.

Usage:
    python manage.py check_cloudinary
"""

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from academy_crm.cloudinary_service import get_cloudinary_service_or_none, is_cloudinary_enabled
from io import BytesIO
import cloudinary.uploader


class Command(BaseCommand):
    help = 'Test Cloudinary integration and functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Delete test files after testing',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Cloudinary Integration Test'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Test 1: Configuration Check
        self.stdout.write(self.style.WARNING('Test 1: Configuration Check'))
        self.stdout.write('-' * 60)
        
        if not is_cloudinary_enabled():
            self.stdout.write(self.style.ERROR('❌ Cloudinary is not enabled'))
            self.stdout.write('')
            self.stdout.write('Please set the following environment variables:')
            self.stdout.write('  - CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name')
            self.stdout.write('  OR')
            self.stdout.write('  - CLOUDINARY_CLOUD_NAME=your_cloud_name')
            self.stdout.write('  - CLOUDINARY_API_KEY=your_api_key')
            self.stdout.write('  - CLOUDINARY_API_SECRET=your_api_secret')
            return
        
        self.stdout.write(self.style.SUCCESS('✅ Cloudinary is enabled'))
        
        # Check which configuration method is used
        from django.conf import settings
        if getattr(settings, 'CLOUDINARY_URL', None):
            self.stdout.write('   Using: CLOUDINARY_URL (single variable)')
        else:
            self.stdout.write('   Using: Individual variables (CLOUDINARY_CLOUD_NAME, etc.)')
        self.stdout.write('')

        # Test 2: Service Initialization
        self.stdout.write(self.style.WARNING('Test 2: Service Initialization'))
        self.stdout.write('-' * 60)
        
        try:
            cloudinary_service = get_cloudinary_service_or_none()
            if not cloudinary_service:
                self.stdout.write(self.style.ERROR('❌ Failed to initialize CloudinaryService'))
                return
            self.stdout.write(self.style.SUCCESS('✅ CloudinaryService initialized successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error initializing service: {e}'))
            return
        self.stdout.write('')

        # Test 3: Upload Test
        self.stdout.write(self.style.WARNING('Test 3: File Upload'))
        self.stdout.write('-' * 60)
        
        test_file_content = b'This is a test file for Cloudinary integration.'
        test_file = SimpleUploadedFile(
            "test_file.txt",
            test_file_content,
            content_type="text/plain"
        )
        
        try:
            uploaded = cloudinary_service.upload_file(
                file_content=test_file,
                folder="test",
                public_id="test_upload",
                resource_type="raw"
            )
            
            self.stdout.write(self.style.SUCCESS('✅ File uploaded successfully'))
            self.stdout.write(f'   Public ID: {uploaded.public_id}')
            self.stdout.write(f'   URL: {uploaded.url}')
            self.stdout.write(f'   Secure URL: {uploaded.secure_url}')
            self.stdout.write(f'   Size: {uploaded.bytes} bytes')
            self.stdout.write(f'   Folder: {uploaded.folder}')
            
            test_public_id = uploaded.public_id
            test_folder = uploaded.folder
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Upload failed: {e}'))
            return
        self.stdout.write('')

        # Test 4: URL Generation
        self.stdout.write(self.style.WARNING('Test 4: URL Generation'))
        self.stdout.write('-' * 60)
        
        try:
            # Test without transformation
            url = cloudinary_service.get_file_url(test_public_id, resource_type="raw")
            self.stdout.write(self.style.SUCCESS('✅ URL generated (no transformation)'))
            self.stdout.write(f'   URL: {url}')
            
            # Test with transformation (for images) - try PIL, but don't fail if not available
            try:
                from PIL import Image
                img = Image.new('RGB', (100, 100), color='red')
                img_buffer = BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                uploaded_img = cloudinary_service.upload_file(
                    file_content=img_buffer,
                    folder="test",
                    public_id="test_image",
                    resource_type="image"
                )
                
                transformed_url = cloudinary_service.get_file_url(
                    uploaded_img.public_id,
                    transformation="w_50,h_50,c_fill",
                    resource_type="image"
                )
                self.stdout.write(self.style.SUCCESS('✅ URL generated (with transformation)'))
                self.stdout.write(f'   Transformed URL: {transformed_url}')
                
                test_image_id = uploaded_img.public_id
            except ImportError:
                self.stdout.write(self.style.WARNING('⚠️  PIL/Pillow not installed, skipping image test'))
                test_image_id = None
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Image test failed: {e}'))
                test_image_id = None
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ URL generation failed: {e}'))
            test_image_id = None
        self.stdout.write('')

        # Test 5: File Info Retrieval
        self.stdout.write(self.style.WARNING('Test 5: File Info Retrieval'))
        self.stdout.write('-' * 60)
        
        try:
            file_info = cloudinary_service.get_file_info(test_public_id, resource_type="raw")
            if file_info:
                self.stdout.write(self.style.SUCCESS('✅ File info retrieved'))
                self.stdout.write(f'   Public ID: {file_info.get("public_id")}')
                self.stdout.write(f'   Format: {file_info.get("format")}')
                self.stdout.write(f'   Size: {file_info.get("bytes")} bytes')
                self.stdout.write(f'   Created: {file_info.get("created_at")}')
            else:
                self.stdout.write(self.style.ERROR('❌ File info is None'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ File info retrieval failed: {e}'))
        self.stdout.write('')

        # Test 6: Move File (Archive simulation)
        self.stdout.write(self.style.WARNING('Test 6: Move File (Archive Test)'))
        self.stdout.write('-' * 60)
        
        try:
            # Pass the full public_id - move_file will extract folder and filename
            # Important: Use resource_type="raw" since we uploaded as raw
            # Try to call Cloudinary API directly to get detailed error
            
            # Extract folder and filename for display
            file_name = test_public_id.split('/')[-1]
            old_public_id = test_public_id
            new_public_id = f"test/archive/{file_name}"
            
            self.stdout.write(f'   Attempting to move: {old_public_id} -> {new_public_id}')
            
            try:
                result = cloudinary.uploader.rename(
                    old_public_id,
                    new_public_id,
                    resource_type="raw",
                    overwrite=True,
                    invalidate=True
                )
                
                if result.get("result") == "ok":
                    self.stdout.write(self.style.SUCCESS('✅ File moved successfully'))
                    self.stdout.write(f'   From: {old_public_id}')
                    self.stdout.write(f'   To: {new_public_id}')
                    # Update public_id for cleanup
                    test_public_id = new_public_id
                else:
                    self.stdout.write(self.style.ERROR(f'❌ File move failed: {result}'))
            except Exception as api_error:
                error_msg = str(api_error)
                error_type = type(api_error).__name__
                self.stdout.write(self.style.ERROR(f'❌ File move failed'))
                self.stdout.write(self.style.ERROR(f'   Error Type: {error_type}'))
                self.stdout.write(self.style.ERROR(f'   Error Message: {error_msg}'))
                
                # Check if it's a permission/authorization error
                if 'not found' in error_msg.lower() or '404' in error_msg.lower():
                    self.stdout.write(self.style.WARNING('   💡 Hint: File might not exist or resource_type mismatch'))
                elif 'unauthorized' in error_msg.lower() or '403' in error_msg.lower() or 'permission' in error_msg.lower():
                    self.stdout.write(self.style.WARNING('   💡 Hint: Cloudinary account might not allow renaming/moving files'))
                    self.stdout.write(self.style.WARNING('   💡 Check your Cloudinary account settings and API permissions'))
                elif 'invalid' in error_msg.lower():
                    self.stdout.write(self.style.WARNING('   💡 Hint: Check if the public_id format is correct'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Move test failed: {e}'))
        self.stdout.write('')

        # Test 7: Cleanup (if requested)
        if options['cleanup']:
            self.stdout.write(self.style.WARNING('Test 7: Cleanup'))
            self.stdout.write('-' * 60)
            
            try:
                # Delete test file
                deleted = cloudinary_service.delete_file(test_public_id, resource_type="raw")
                if deleted:
                    self.stdout.write(self.style.SUCCESS(f'✅ Deleted: {test_public_id}'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  Could not delete: {test_public_id}'))
                
                # Delete test image if it was created
                if test_image_id:
                    deleted_img = cloudinary_service.delete_file(test_image_id, resource_type="image")
                    if deleted_img:
                        self.stdout.write(self.style.SUCCESS(f'✅ Deleted: {test_image_id}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'⚠️  Could not delete: {test_image_id}'))
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Cleanup failed: {e}'))
            self.stdout.write('')
        else:
            self.stdout.write(self.style.WARNING('Test files not cleaned up (use --cleanup to delete)'))
            self.stdout.write(f'   Test file: {test_public_id}')
            if test_image_id:
                self.stdout.write(f'   Test image: {test_image_id}')
            self.stdout.write('')

        # Summary
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ All tests completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

