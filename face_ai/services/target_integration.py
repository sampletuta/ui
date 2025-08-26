import logging
import os
from typing import List, Dict, Optional
from django.conf import settings
from django.core.files.storage import default_storage

from .face_detection import FaceDetectionService
from .milvus_service import MilvusService

logger = logging.getLogger(__name__)

class TargetIntegrationService:
    """Service for integrating face AI with target creation process"""
    
    def __init__(self):
        self.face_detection_service = FaceDetectionService()
        self.milvus_service = MilvusService()
        self._ensure_milvus_collection()
    
    def _ensure_milvus_collection(self):
        """Ensure Milvus collection exists"""
        try:
            self.milvus_service.create_collection_if_not_exists()
            logger.info("Milvus collection ready for target integration")
        except Exception as e:
            logger.error(f"Failed to ensure Milvus collection: {e}")
            raise
    
    def process_target_photo(self, target_photo, target_id: str) -> Dict:
        """
        Process a single target photo and update the target's normalized embedding
        
        Args:
            target_photo: TargetPhoto instance
            target_id: ID of the target from Targets_watchlist
            
        Returns:
            Processing results dictionary
        """
        try:
            # Get the image path
            if not target_photo.image:
                return {
                    'success': False,
                    'error': 'No image file found',
                    'target_photo_id': target_photo.id
                }
            
            # Get the full file path
            image_path = target_photo.image.path if hasattr(target_photo.image, 'path') else None
            
            if not image_path or not os.path.exists(image_path):
                # Try to get path from storage
                try:
                    image_path = default_storage.path(target_photo.image.name)
                except Exception:
                    return {
                        'success': False,
                        'error': 'Could not locate image file',
                        'target_photo_id': target_photo.id
                    }
            
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': 'Image file not found on disk',
                    'target_photo_id': target_photo.id
                }
            
            logger.info(f"Processing target photo {target_photo.id} for target {target_id}")
            
            # Step 1: Detect faces in the image
            detection_result = self.face_detection_service.detect_faces_in_image(image_path)
            
            if not detection_result['success']:
                return {
                    'success': False,
                    'error': f"Face detection failed: {detection_result.get('error')}",
                    'target_photo_id': target_photo.id
                }
            
            if detection_result['faces_detected'] == 0:
                return {
                    'success': True,
                    'message': 'No faces detected in image',
                    'target_photo_id': target_photo.id,
                    'faces_detected': 0,
                    'embeddings_stored': 0
                }
            
            # Step 2: Generate embeddings for detected faces
            embedding_result = self.face_detection_service.generate_face_embeddings([image_path])
            
            if not embedding_result['success']:
                return {
                    'success': False,
                    'error': f"Embedding generation failed: {embedding_result.get('error')}",
                    'target_photo_id': target_photo.id
                }
            
            # Step 3: Update target's normalized embedding with new photo
            # Instead of storing individual embeddings, we'll update the target's normalized embedding
            try:
                # Get all photos for this target to compute normalized embedding
                from backendapp.models import TargetPhoto
                target_photos = TargetPhoto.objects.filter(person_id=target_id)
                
                # Collect all embeddings from all photos for this target
                all_embeddings = []
                all_confidence_scores = []
                
                for photo in target_photos:
                    if photo.image and hasattr(photo.image, 'path') and os.path.exists(photo.image.path):
                        try:
                            # Generate embedding for this photo
                            photo_embedding_result = self.face_detection_service.generate_face_embeddings([photo.image.path])
                            if photo_embedding_result['success'] and photo_embedding_result['embeddings']:
                                # Take the first face embedding from each photo
                                embedding_data = photo_embedding_result['embeddings'][0]
                                all_embeddings.append(embedding_data['embedding'])
                                all_confidence_scores.append(embedding_data['confidence_score'])
                        except Exception as e:
                            logger.warning(f"Failed to process photo {photo.id} for normalization: {e}")
                            continue
                
                if all_embeddings:
                    # Update the target's embedding in Milvus
                    # Strategy: 1 image = direct embedding, 2+ images = averaged normalized
                    embedding_strategy = "single" if len(all_embeddings) == 1 else "averaged_normalized"
                    logger.info(f"Target {target_id} has {len(all_embeddings)} photos - using {embedding_strategy} strategy")
                    
                    milvus_id = self.milvus_service.insert_normalized_target_embedding(
                        target_id=target_id,
                        embeddings=all_embeddings,
                        confidence_scores=all_confidence_scores
                    )
                    
                    if milvus_id:
                        logger.info(f"Updated embedding for target {target_id} with {len(all_embeddings)} photos using {embedding_strategy} strategy")
                        return {
                            'success': True,
                            'message': f"Successfully updated target's embedding with {len(all_embeddings)} photos using {embedding_strategy} strategy",
                            'target_photo_id': target_photo.id,
                            'faces_detected': detection_result['faces_detected'],
                            'embeddings_stored': 1,  # One embedding per target
                            'normalized_embedding_id': milvus_id,
                            'total_photos_processed': len(all_embeddings),
                            'embedding_strategy': embedding_strategy
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to update normalized embedding in Milvus',
                            'target_photo_id': target_photo.id
                        }
                else:
                    return {
                        'success': False,
                        'error': 'No valid embeddings could be generated from any photos',
                        'target_photo_id': target_photo.id
                    }
                    
            except Exception as e:
                logger.error(f"Failed to update normalized embedding: {e}")
                return {
                    'success': False,
                    'error': f"Failed to update normalized embedding: {str(e)}",
                    'target_photo_id': target_photo.id
                }
            
        except Exception as e:
            logger.error(f"Failed to process target photo {target_photo.id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_photo_id': target_photo.id
            }
    
    def process_target_photos_batch(self, target_photos: List, target_id: str) -> Dict:
        """
        Process multiple target photos and create/update the target's normalized embedding
        
        Args:
            target_photos: List of TargetPhoto instances
            target_id: ID of the target from Targets_watchlist
            
        Returns:
            Batch processing results dictionary
        """
        try:
            if not target_photos:
                return {
                    'success': True,
                    'message': 'No photos to process',
                    'total_photos': 0,
                    'processed_photos': 0,
                    'total_embeddings': 0
                }
            
            logger.info(f"Processing {len(target_photos)} photos for target {target_id}")
            
            # Check if target already has a normalized embedding to prevent duplicate processing
            existing_embedding = self.milvus_service.get_target_normalized_embedding(target_id)
            if existing_embedding is not None:
                logger.info(f"Target {target_id} already has normalized embedding, skipping batch processing to prevent duplicates")
                return {
                    'success': True,
                    'message': 'Target already has normalized embedding, skipping duplicate processing',
                    'total_photos': len(target_photos),
                    'processed_photos': 0,
                    'total_embeddings': 1,
                    'normalized_embedding_id': 'existing',
                    'embedding_strategy': 'existing',
                    'skipped_duplicate': True
                }
            
            # Instead of processing each photo individually, we'll process all photos
            # and create one normalized embedding for the target
            all_embeddings = []
            all_confidence_scores = []
            processed_photos = 0
            failed_photos = []
            
            for target_photo in target_photos:
                try:
                    # Get the image path
                    if not target_photo.image:
                        failed_photos.append({
                            'photo_id': target_photo.id,
                            'error': 'No image file found'
                        })
                        continue
                    
                    image_path = target_photo.image.path if hasattr(target_photo.image, 'path') else None
                    
                    if not image_path or not os.path.exists(image_path):
                        # Try to get path from storage
                        try:
                            image_path = default_storage.path(target_photo.image.name)
                        except Exception:
                            failed_photos.append({
                                'photo_id': target_photo.id,
                                'error': 'Could not locate image file'
                            })
                            continue
                    
                    if not os.path.exists(image_path):
                        failed_photos.append({
                            'photo_id': target_photo.id,
                            'error': 'Image file not found on disk'
                        })
                        continue
                    
                    # Detect faces and generate embeddings
                    detection_result = self.face_detection_service.detect_faces_in_image(image_path)
                    
                    if not detection_result['success']:
                        failed_photos.append({
                            'photo_id': target_photo.id,
                            'error': f"Face detection failed: {detection_result.get('error')}"
                        })
                        continue
                    
                    if detection_result['faces_detected'] == 0:
                        logger.info(f"Photo {target_photo.id}: No faces detected")
                        processed_photos += 1
                        continue
                    
                    # Generate embeddings for detected faces
                    embedding_result = self.face_detection_service.generate_face_embeddings([image_path])
                    
                    if not embedding_result['success']:
                        failed_photos.append({
                            'photo_id': target_photo.id,
                            'error': f"Embedding generation failed: {embedding_result.get('error')}"
                        })
                        continue
                    
                    # Take the first face embedding from this photo
                    if embedding_result['embeddings']:
                        embedding_data = embedding_result['embeddings'][0]
                        # Convert Python list to numpy array for Milvus service
                        import numpy as np
                        embedding_array = np.array(embedding_data['embedding'], dtype=np.float32)
                        all_embeddings.append(embedding_array)
                        all_confidence_scores.append(embedding_data['confidence_score'])
                        processed_photos += 1
                        logger.info(f"Successfully processed photo {target_photo.id}")
                    else:
                        failed_photos.append({
                            'photo_id': target_photo.id,
                            'error': 'No embeddings generated'
                        })
                        
                except Exception as e:
                    failed_photos.append({
                        'photo_id': target_photo.id,
                        'error': str(e)
                    })
                    logger.error(f"Exception processing photo {target_photo.id}: {e}")
            
            # Create/update the target's embedding
            if all_embeddings:
                try:
                    # Strategy: 1 image = direct embedding, 2+ images = averaged normalized
                    embedding_strategy = "single" if len(all_embeddings) == 1 else "averaged_normalized"
                    logger.info(f"Target {target_id} has {len(all_embeddings)} photos - using {embedding_strategy} strategy")
                    
                    milvus_id = self.milvus_service.insert_normalized_target_embedding(
                        target_id=target_id,
                        embeddings=all_embeddings,
                        confidence_scores=all_confidence_scores
                    )
                    
                    if milvus_id:
                        logger.info(f"Created/updated embedding for target {target_id} with {len(all_embeddings)} photos using {embedding_strategy} strategy")
                        return {
                            'success': True,
                            'message': f"Successfully processed {processed_photos}/{len(target_photos)} photos and created embedding using {embedding_strategy} strategy",
                            'total_photos': len(target_photos),
                            'processed_photos': processed_photos,
                            'total_embeddings': 1,  # One embedding per target
                            'normalized_embedding_id': milvus_id,
                            'embedding_strategy': embedding_strategy,
                            'failed_photos': failed_photos
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to create normalized embedding in Milvus',
                            'total_photos': len(target_photos),
                            'processed_photos': processed_photos,
                            'total_embeddings': 0,
                            'failed_photos': failed_photos
                        }
                        
                except Exception as e:
                    logger.error(f"Failed to create normalized embedding: {e}")
                    return {
                        'success': False,
                        'error': f"Failed to create normalized embedding: {str(e)}",
                        'total_photos': len(target_photos),
                        'processed_photos': processed_photos,
                        'total_embeddings': 0,
                        'failed_photos': failed_photos
                    }
            else:
                return {
                    'success': False,
                    'error': 'No valid embeddings could be generated from any photos',
                    'total_photos': len(target_photos),
                    'processed_photos': processed_photos,
                    'total_embeddings': 0,
                    'failed_photos': failed_photos
                }
            
        except Exception as e:
            logger.error(f"Failed to process target photos batch: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_photos': len(target_photos),
                'processed_photos': 0,
                'total_embeddings': 0
            }
    
    def get_target_face_summary(self, target_id: str) -> Dict:
        """
        Get a summary of face processing for a specific target
        
        Args:
            target_id: ID of the target
            
        Returns:
            Summary of face processing results
        """
        try:
            # Get Milvus collection stats
            milvus_stats = self.milvus_service.get_collection_stats()
            
            return {
                'success': True,
                'target_id': target_id,
                'milvus_stats': milvus_stats,
                'message': f"Face processing summary for target {target_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to get target face summary: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_id': target_id
            }
    
    def update_target_normalized_embedding(self, target_id: str) -> Dict:
        """
        Update a target's normalized embedding after photos are added/removed
        
        Args:
            target_id: ID of the target
            
        Returns:
            Update results dictionary
        """
        try:
            from backendapp.models import TargetPhoto
            
            # Get all photos for this target
            target_photos = TargetPhoto.objects.filter(person_id=target_id)
            
            if not target_photos.exists():
                # No photos left, remove the target's embedding from Milvus
                deleted_count = self.milvus_service.delete_embeddings_by_target_id(target_id)
                logger.info(f"Removed {deleted_count} embeddings for target {target_id} (no photos left)")
                
                return {
                    'success': True,
                    'message': 'Target has no photos, removed all embeddings',
                    'target_id': target_id,
                    'embeddings_removed': deleted_count,
                    'total_photos': 0
                }
            
            # Check if target already has a valid normalized embedding
            existing_embedding = self.milvus_service.get_target_normalized_embedding(target_id)
            if existing_embedding is not None:
                logger.info(f"Target {target_id} already has normalized embedding, skipping update to prevent duplicates")
                return {
                    'success': True,
                    'message': 'Target already has normalized embedding, no update needed',
                    'target_id': target_id,
                    'normalized_embedding_id': 'existing',
                    'total_photos': target_photos.count(),
                    'photos_processed': 0,
                    'embedding_strategy': 'existing',
                    'skipped_duplicate': True
                }
            
            # Collect all embeddings from all photos for this target
            all_embeddings = []
            all_confidence_scores = []
            
            for photo in target_photos:
                if photo.image and hasattr(photo.image, 'path') and os.path.exists(photo.image.path):
                    try:
                        # Generate embedding for this photo
                        photo_embedding_result = self.face_detection_service.generate_face_embeddings([photo.image.path])
                        if photo_embedding_result['success'] and photo_embedding_result['embeddings']:
                            # Take the first face embedding from each photo
                            embedding_data = photo_embedding_result['embeddings'][0]
                            # Convert Python list to numpy array for Milvus service
                            import numpy as np
                            embedding_array = np.array(embedding_data['embedding'], dtype=np.float32)
                            all_embeddings.append(embedding_array)
                            all_confidence_scores.append(embedding_data['confidence_score'])
                    except Exception as e:
                        logger.warning(f"Failed to process photo {photo.id} for normalization: {e}")
                        continue
            
            if all_embeddings:
                # Update the target's embedding in Milvus
                # Strategy: 1 image = direct embedding, 2+ images = averaged normalized
                embedding_strategy = "single" if len(all_embeddings) == 1 else "averaged_normalized"
                logger.info(f"Target {target_id} has {len(all_embeddings)} photos - using {embedding_strategy} strategy")
                
                milvus_id = self.milvus_service.insert_normalized_target_embedding(
                    target_id=target_id,
                    embeddings=all_embeddings,
                    confidence_scores=all_confidence_scores
                )
                
                if milvus_id:
                    logger.info(f"Updated embedding for target {target_id} with {len(all_embeddings)} photos using {embedding_strategy} strategy")
                    return {
                        'success': True,
                        'message': f'Successfully updated embedding with {len(all_embeddings)} photos using {embedding_strategy} strategy',
                        'target_id': target_id,
                        'normalized_embedding_id': milvus_id,
                        'total_photos': len(all_embeddings),
                        'photos_processed': len(all_embeddings),
                        'embedding_strategy': embedding_strategy
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to update normalized embedding in Milvus',
                        'target_id': target_id,
                        'total_photos': len(all_embeddings)
                    }
            else:
                return {
                    'success': False,
                    'error': 'No valid embeddings could be generated from any photos',
                    'target_id': target_id,
                    'total_photos': target_photos.count()
                }
                
        except Exception as e:
            logger.error(f"Failed to update normalized embedding for target {target_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_id': target_id
            }
    
    def remove_target_photo_embedding(self, target_id: str, photo_id: str) -> Dict:
        """
        Remove a photo's contribution from the target's normalized embedding
        
        Args:
            target_id: ID of the target
            photo_id: ID of the photo being removed
            
        Returns:
            Removal results dictionary
        """
        try:
            logger.info(f"Removing photo {photo_id} contribution from target {target_id} normalized embedding")
            
            # Update the target's normalized embedding without the removed photo
            result = self.update_target_normalized_embedding(target_id)
            
            if result['success']:
                logger.info(f"Successfully updated normalized embedding after removing photo {photo_id}")
                return {
                    'success': True,
                    'message': f'Successfully updated normalized embedding after removing photo {photo_id}',
                    'target_id': target_id,
                    'photo_id': photo_id,
                    'normalized_embedding_updated': True
                }
            else:
                logger.error(f"Failed to update normalized embedding after removing photo {photo_id}: {result.get('error')}")
                return {
                    'success': False,
                    'error': f'Failed to update normalized embedding: {result.get("error")}',
                    'target_id': target_id,
                    'photo_id': photo_id
                }
                
        except Exception as e:
            logger.error(f"Failed to remove photo {photo_id} contribution from target {target_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_id': target_id,
                'photo_id': photo_id
            }
