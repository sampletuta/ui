from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Check database schema for source_management tables'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check FileSource table schema
            cursor.execute("PRAGMA table_info(source_management_filesource)")
            file_source_columns = cursor.fetchall()
            
            self.stdout.write("FileSource table columns:")
            for col in file_source_columns:
                self.stdout.write(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3]}")
            
            # Check CameraSource table schema
            cursor.execute("PRAGMA table_info(source_management_camerasource)")
            camera_source_columns = cursor.fetchall()
            
            self.stdout.write("\nCameraSource table columns:")
            for col in camera_source_columns:
                self.stdout.write(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3]}")
            
            # Check StreamSource table schema
            cursor.execute("PRAGMA table_info(source_management_streamsource)")
            stream_source_columns = cursor.fetchall()
            
            self.stdout.write("\nStreamSource table columns:")
            for col in stream_source_columns:
                self.stdout.write(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3]}") 