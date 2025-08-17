from django.core.management.base import BaseCommand
from django.db import transaction
from backendapp.models import TargetPhoto, Targets_watchlist
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process all existing target photos for face detection and embedding storage in Milvus'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--target-id',
            type=str,
            help='Process photos for a specific target ID only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing of already processed photos'
        )
    
    def handle(self, *args, **options):
        try:
            from face_ai.services.target_integration_wrapper import TargetIntegrationWrapper
            
            # Initialize face AI service with async support
            face_service = TargetIntegrationWrapper(use_async=True, max_workers=4)
            
            # Get photos to process
            if options['target_id']:
                try:
                    target = Targets_watchlist.objects.get(id=options['target_id'])
                    photos = target.images.all()
                    self.stdout.write(f"Processing photos for target: {target.target_name}")
                except Targets_watchlist.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Target with ID {options["target_id"]} not found')
                    )
                    return
            else:
                photos = TargetPhoto.objects.all()
                self.stdout.write("Processing all target photos")
            
            total_photos = photos.count()
            if total_photos == 0:
                self.stdout.write("No photos found to process")
                return
            
            self.stdout.write(f"Found {total_photos} photos to process")
            
            if options['dry_run']:
                self.stdout.write("DRY RUN MODE - No actual processing will occur")
                for photo in photos:
                    self.stdout.write(f"  - Photo {photo.id}: {photo.image.name} for target {photo.person.target_name}")
                return
            
            # Process photos
            processed_count = 0
            total_embeddings = 0
            failed_photos = []
            
            with transaction.atomic():
                for photo in photos:
                    try:
                        self.stdout.write(f"Processing photo {photo.id} for target {photo.person.target_name}...")
                        
                        # Process the photo
                        result = face_service.process_target_photo(photo, str(photo.person.id))
                        
                        if result['success']:
                            processed_count += 1
                            embeddings_stored = result.get('embeddings_stored', 0)
                            total_embeddings += embeddings_stored
                            
                            if embeddings_stored > 0:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"  ✅ Success: {embeddings_stored} embeddings stored"
                                    )
                                )
                            else:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  ⚠️ No faces detected"
                                    )
                                )
                        else:
                            failed_photos.append({
                                'photo_id': photo.id,
                                'error': result.get('error', 'Unknown error')
                            })
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ❌ Failed: {result.get('error')}"
                                )
                            )
                            
                    except Exception as e:
                        failed_photos.append({
                            'photo_id': photo.id,
                            'error': str(e)
                        })
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ Exception: {e}")
                        )
                        logger.error(f"Failed to process photo {photo.id}: {e}")
            
            # Summary
            self.stdout.write("\n" + "="*50)
            self.stdout.write("PROCESSING SUMMARY")
            self.stdout.write("="*50)
            self.stdout.write(f"Total photos: {total_photos}")
            self.stdout.write(f"Successfully processed: {processed_count}")
            self.stdout.write(f"Failed: {len(failed_photos)}")
            self.stdout.write(f"Total embeddings stored: {total_embeddings}")
            
            if failed_photos:
                self.stdout.write("\nFailed photos:")
                for failed in failed_photos:
                    self.stdout.write(f"  - Photo {failed['photo_id']}: {failed['error']}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🎉 Processing completed! {total_embeddings} face embeddings stored in Milvus."
                )
            )
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "Face AI service not available. Please ensure all dependencies are installed."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Command failed: {e}")
            )
            logger.error(f"Process existing photos command failed: {e}")
