from django.core.management.base import BaseCommand
from django.db import connection
import uuid

class Command(BaseCommand):
    help = 'Fix UUID data issues in source management models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('Checking for UUID data issues...')
        
        with connection.cursor() as cursor:
            # Check and fix FileSource records
            cursor.execute("SELECT source_id, name FROM source_management_filesource")
            file_sources = cursor.fetchall()
            
            for source_id, name in file_sources:
                try:
                    # Try to validate UUID
                    uuid.UUID(str(source_id))
                    self.stdout.write(f'✓ FileSource {name}: UUID is valid')
                except (ValueError, TypeError):
                    self.stdout.write(f'✗ FileSource {name}: Invalid UUID - {source_id}')
                    if not dry_run:
                        new_uuid = str(uuid.uuid4())
                        cursor.execute(
                            "UPDATE source_management_filesource SET source_id = %s WHERE source_id = %s",
                            [new_uuid, source_id]
                        )
                        self.stdout.write(f'  → Fixed: {source_id} → {new_uuid}')
            
            # Check and fix CameraSource records
            cursor.execute("SELECT source_id, name FROM source_management_camerasource")
            camera_sources = cursor.fetchall()
            
            for source_id, name in camera_sources:
                try:
                    uuid.UUID(str(source_id))
                    self.stdout.write(f'✓ CameraSource {name}: UUID is valid')
                except (ValueError, TypeError):
                    self.stdout.write(f'✗ CameraSource {name}: Invalid UUID - {source_id}')
                    if not dry_run:
                        new_uuid = str(uuid.uuid4())
                        cursor.execute(
                            "UPDATE source_management_camerasource SET source_id = %s WHERE source_id = %s",
                            [new_uuid, source_id]
                        )
                        self.stdout.write(f'  → Fixed: {source_id} → {new_uuid}')
            
            # Check and fix StreamSource records
            cursor.execute("SELECT source_id, name FROM source_management_streamsource")
            stream_sources = cursor.fetchall()
            
            for source_id, name in stream_sources:
                try:
                    uuid.UUID(str(source_id))
                    self.stdout.write(f'✓ StreamSource {name}: UUID is valid')
                except (ValueError, TypeError):
                    self.stdout.write(f'✗ StreamSource {name}: Invalid UUID - {source_id}')
                    if not dry_run:
                        new_uuid = str(uuid.uuid4())
                        cursor.execute(
                            "UPDATE source_management_streamsource SET source_id = %s WHERE source_id = %s",
                            [new_uuid, source_id]
                        )
                        self.stdout.write(f'  → Fixed: {source_id} → {new_uuid}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('UUID data fix completed!')) 