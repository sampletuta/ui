from django.core.management.base import BaseCommand
from source_management.models import FileSource
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Test video processing functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file-path',
            type=str,
            help='Path to a test video file',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        
        if not file_path or not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR('Please provide a valid file path to a video file')
            )
            return
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        
        # Create a test file source
        file_source = FileSource.objects.create(
            source_id='test_file_001',
            name='Test Video File',
            description='Test video for processing',
            created_by=user,
            video_file=file_path,
            status='uploading'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created test file source: {file_source.name}')
        )
        
        # Test video processing
        self.stdout.write('Starting video processing...')
        success = file_source.process_video()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('Video processing completed successfully!')
            )
            self.stdout.write(f'Duration: {file_source.get_duration_display()}')
            self.stdout.write(f'Resolution: {file_source.get_resolution_display()}')
            self.stdout.write(f'File Size: {file_source.get_file_size_display()}')
            self.stdout.write(f'Access Token: {file_source.access_token}')
            self.stdout.write(f'API Endpoint: {file_source.api_endpoint}')
        else:
            self.stdout.write(
                self.style.ERROR('Video processing failed!')
            )
            if file_source.processing_error:
                self.stdout.write(f'Error: {file_source.processing_error}') 