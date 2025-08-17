from django.core.management.base import BaseCommand
from django.db import transaction
from face_ai.services.face_detection import FaceDetectionService
from face_ai.services.milvus_service import MilvusService
from backendapp.models import Targets_watchlist, TargetPhoto
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create normalized embeddings for all targets based on their photos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all normalized embeddings',
        )
        parser.add_argument(
            '--target-id',
            type=str,
            help='Process only a specific target ID',
        )

    def handle(self, *args, **options):
        force = options['force']
        target_id = options['target_id']
        
        self.stdout.write(self.style.SUCCESS('Starting normalized embedding creation...'))
        
        # Initialize services
        try:
            face_service = FaceDetectionService()
            milvus_service = MilvusService()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize services: {e}'))
            return
        
        # Check Milvus collection status
        collection_status = milvus_service.check_collection_status()
        if collection_status['status'] == 'error':
            self.stdout.write(self.style.ERROR(f'Milvus collection error: {collection_status["message"]}'))
            return
        elif collection_status['status'] == 'warning':
            self.stdout.write(self.style.WARNING(f'Milvus collection warning: {collection_status["message"]}'))
        
        # Get targets to process
        if target_id:
            targets = Targets_watchlist.objects.filter(id=target_id)
            if not targets.exists():
                self.stdout.write(self.style.ERROR(f'Target with ID {target_id} not found'))
                return
        else:
            targets = Targets_watchlist.objects.all()
        
        total_targets = targets.count()
        self.stdout.write(f'Processing {total_targets} targets...')
        
        processed_count = 0
        error_count = 0
        
        for target in targets:
            try:
                self.stdout.write(f'Processing target: {target.target_name} (ID: {target.id})')
                
                # Get all photos for this target
                photos = TargetPhoto.objects.filter(person=target)
                if not photos.exists():
                    self.stdout.write(self.style.WARNING(f'  No photos found for target {target.target_name}'))
                    continue
                
                self.stdout.write(f'  Found {photos.count()} photos')
                
                # Extract embeddings from all photos
                embeddings = []
                confidence_scores = []
                
                for photo in photos:
                    try:
                        # Convert photo to base64
                        photo_base64 = face_service.image_to_base64(photo.image)
                        
                        # Detect faces and get embedding
                        face_validation = face_service.detect_faces_in_image_base64(photo_base64)
                        if face_validation['success'] and face_validation['faces_detected'] > 0:
                            # Get the first face embedding
                            face = face_validation['faces'][0]
                            embedding = face_service.app.get(face_service._base64_to_image(photo_base64))[0].normed_embedding
                            
                            embeddings.append(embedding)
                            confidence_scores.append(face['confidence'])
                            
                            self.stdout.write(f'    Photo {photo.id}: extracted embedding with confidence {face["confidence"]:.3f}')
                        else:
                            self.stdout.write(self.style.WARNING(f'    Photo {photo.id}: no faces detected'))
                            
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    Photo {photo.id}: error extracting embedding - {e}'))
                        continue
                
                if not embeddings:
                    self.stdout.write(self.style.WARNING(f'  No valid embeddings extracted for target {target.target_name}'))
                    continue
                
                # Create normalized embedding
                try:
                    milvus_id = milvus_service.insert_normalized_target_embedding(
                        str(target.id), 
                        embeddings, 
                        confidence_scores
                    )
                    
                    if milvus_id:
                        self.stdout.write(self.style.SUCCESS(f'  Created normalized embedding (Milvus ID: {milvus_id})'))
                        processed_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f'  Failed to create normalized embedding'))
                        error_count += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating normalized embedding: {e}'))
                    error_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing target {target.target_name}: {e}'))
                error_count += 1
                continue
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nNormalized embedding creation completed!'))
        self.stdout.write(f'Total targets: {total_targets}')
        self.stdout.write(f'Successfully processed: {processed_count}')
        self.stdout.write(f'Errors: {error_count}')
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING('Some targets had errors. Check the logs for details.'))
