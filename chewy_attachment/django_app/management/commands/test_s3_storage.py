"""
Django management command to test S3 storage configuration.

Usage:
    python manage.py test_s3_storage
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Test S3 storage configuration for ChewyAttachment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-file',
            type=str,
            default='test.txt',
            help='Test file name to upload (default: test.txt)'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up test file after testing'
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing S3 storage configuration...")
        
        # Check if S3 dependencies are available
        try:
            import boto3
            from storages.backends.s3boto3 import S3Boto3Storage
        except ImportError as e:
            raise CommandError(
                f"Missing dependencies for S3 storage: {e}\n"
                "Install with: pip install 'chewy-attachment[django-s3]'"
            )
        
        # Validate configuration
        from chewy_attachment.django_app.storage import validate_s3_configuration
        if not validate_s3_configuration():
            raise CommandError(
                "S3 configuration is invalid. Please check your settings:\n"
                "- AWS_STORAGE_BUCKET_NAME\n"
                "- AWS_ACCESS_KEY_ID\n"
                "- AWS_SECRET_ACCESS_KEY\n"
                "- AWS_S3_REGION_NAME"
            )
        
        self.stdout.write(
            self.style.SUCCESS("✓ S3 configuration is valid")
        )
        
        # Test storage engine
        try:
            from chewy_attachment.django_app.storage import get_storage_engine
            storage = get_storage_engine()
            
            # Test file operations
            test_content = b"This is a test file for ChewyAttachment S3 storage."
            test_filename = options['test_file']
            
            self.stdout.write(f"Testing file upload: {test_filename}")
            
            # Upload test file
            result = storage.save_file(test_content, test_filename)
            self.stdout.write(
                self.style.SUCCESS(f"✓ File uploaded: {result.storage_path}")
            )
            
            # Test file existence
            if storage.file_exists(result.storage_path):
                self.stdout.write(
                    self.style.SUCCESS("✓ File exists check passed")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ File exists check failed")
                )
            
            # Test file download
            downloaded_content = storage.get_file(result.storage_path)
            if downloaded_content == test_content:
                self.stdout.write(
                    self.style.SUCCESS("✓ File download and content verification passed")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ File content verification failed")
                )
            
            # Test URL generation
            try:
                file_url = storage.get_file_url(result.storage_path)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ File URL generated: {file_url}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠ File URL generation failed: {e}")
                )
            
            # Cleanup if requested
            if options['cleanup']:
                if storage.delete_file(result.storage_path):
                    self.stdout.write(
                        self.style.SUCCESS("✓ Test file cleaned up")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("⚠ Test file cleanup failed")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ Test file left in storage: {result.storage_path}\n"
                        "Use --cleanup flag to remove it automatically"
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS("\n🎉 S3 storage test completed successfully!")
            )
            
        except Exception as e:
            raise CommandError(f"S3 storage test failed: {e}")
        
        # Display configuration summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("Configuration Summary:")
        self.stdout.write("="*50)
        
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'Not set')
        region = getattr(settings, 'AWS_S3_REGION_NAME', 'Not set')
        default_acl = getattr(settings, 'AWS_DEFAULT_ACL', 'Not set')
        
        self.stdout.write(f"Bucket: {bucket_name}")
        self.stdout.write(f"Region: {region}")
        self.stdout.write(f"Default ACL: {default_acl}")
        
        chewy_settings = getattr(settings, 'CHEWY_ATTACHMENT', {})
        storage_engine = chewy_settings.get('STORAGE_ENGINE', 'file')
        self.stdout.write(f"Storage Engine: {storage_engine}")
        
        if hasattr(settings, 'DEFAULT_FILE_STORAGE'):
            self.stdout.write(f"Django Storage Backend: {settings.DEFAULT_FILE_STORAGE}")