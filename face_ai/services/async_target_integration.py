"""
Async Target Integration Service for parallel processing.

This service provides async-compatible methods for integrating face AI with target creation process,
using the new async services for improved performance and parallel processing.
"""

import logging
import os
import asyncio
from typing import List, Dict, Optional
from django.conf import settings
from django.core.files.storage import default_storage
from asgiref.sync import sync_to_async

from .async_face_detection import AsyncFaceDetectionService
from .async_milvus_service import AsyncMilvusService

logger = logging.getLogger(__name__)

class AsyncTargetIntegrationService:
    """Async service for integrating face AI with target creation process"""
    
    def __init__(self, max_workers: int = 4):
        self.face_detection_service = AsyncFaceDetectionService(max_workers=max_workers)
        self.milvus_service = AsyncMilvusService(max_workers=max_workers)
        self.max_workers = max_workers
        self._ensure_milvus_collection()
    
    def _ensure_milvus_collection(self):
        """Ensure Milvus collection exists"""
        try:
            # Use the sync method for initialization
            self.milvus_service._create_collection_if_not_exists_sync()
            logger.info("Milvus collection ready for async target integration")
        except Exception as e:
            logger.error(f"Failed to ensure Milvus collection: {e}")
            raise

    @sync_to_async
    def _get_target_photos_sync(self, target_id: str):
        """Get target photos synchronously (wrapped for async context)"""
        from backendapp.models import TargetPhoto
        return list(TargetPhoto.objects.filter(person_id=target_id))

    async def process_target_photo_async(self, target_photo, target_id: str) -> Dict:
        """
        Process a single target photo asynchronously and update the target's normalized embedding
        
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
            
            logger.info(f"Processing target photo {target_photo.id} for target {target_id} asynchronously")
            
            # Step 1: Detect faces in the image asynchronously
            detection_result = await self.face_detection_service.detect_faces_in_image_async(image_path)
            
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
            
            # Step 2: Generate embeddings for detected faces asynchronously
            embedding_result = await self.face_detection_service.generate_face_embeddings_parallel([image_path])
            
            if not embedding_result['success']:
                return {
                    'success': False,
                    'error': f"Embedding generation failed: {embedding_result.get('error')}",
                    'target_photo_id': target_photo.id
                }
            
            # Step 3: Store embeddings in Milvus
            embeddings = embedding_result.get('embeddings', [])
            if not embeddings:
                return {
                    'success': False,
                    'error': 'No embeddings generated',
                    'target_photo_id': target_photo.id
                }
            
            # Store individual photo embeddings
            photo_embeddings_data = []
            for i, embedding in enumerate(embeddings):
                photo_embeddings_data.append({
                    'embedding': embedding,
                    'target_id': target_id,
                    'photo_id': str(target_photo.id),
                    'confidence_score': 0.8,  # Default confidence
                    'created_at': '2024-01-01 00:00:00'  # Placeholder
                })
            
            # Insert photo embeddings asynchronously
            milvus_ids = await self.milvus_service.insert_face_embeddings_parallel(photo_embeddings_data)
            
            if not milvus_ids:
                return {
                    'success': False,
                    'error': 'Failed to store photo embeddings in Milvus',
                    'target_photo_id': target_photo.id
                }
            
            # Step 4: Update target's normalized embedding
            normalized_result = await self.update_target_normalized_embedding_async(target_id)
            
            if not normalized_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to update normalized embedding: {normalized_result.get('error')}",
                    'target_photo_id': target_photo.id,
                    'embeddings_stored': len(milvus_ids)
                }
            
            return {
                'success': True,
                'message': f"Successfully processed photo with {detection_result['faces_detected']} faces",
                'target_photo_id': target_photo.id,
                'faces_detected': detection_result['faces_detected'],
                'embeddings_stored': len(milvus_ids),
                'normalized_embedding_updated': True,
                'milvus_ids': milvus_ids
            }
            
        except Exception as e:
            logger.error(f"Failed to process target photo asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_photo_id': target_photo.id
            }
    
    async def process_target_photos_batch_async(self, target_photos: List, target_id: str) -> Dict:
        """
        Process multiple target photos asynchronously and create/update the target's normalized embedding
        
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
            
            logger.info(f"Processing {len(target_photos)} photos for target {target_id} asynchronously")
            
            # Check if target already has a normalized embedding to prevent duplicate processing
            existing_embedding = await self.milvus_service.get_target_normalized_embedding_async(target_id)
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
            
            # Process photos in parallel batches
            batch_size = 5  # Process 5 photos at a time
            batches = [target_photos[i:i + batch_size] for i in range(0, len(target_photos), batch_size)]
            
            # Process batches in parallel
            batch_tasks = []
            for batch in batches:
                task = self._process_photo_batch_async(batch, target_id)
                batch_tasks.append(task)
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            all_embeddings = []
            all_confidence_scores = []
            processed_photos = 0
            failed_photos = []
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing failed: {result}")
                    continue
                
                if result['success']:
                    if result.get('embeddings'):
                        all_embeddings.extend(result['embeddings'])
                        all_confidence_scores.extend(result.get('confidence_scores', []))
                    processed_photos += result.get('processed_photos', 0)
                    failed_photos.extend(result.get('failed_photos', []))
                else:
                    failed_photos.extend(result.get('failed_photos', []))
            
            # Create/update the target's normalized embedding
            if all_embeddings:
                try:
                    # Strategy: 1 image = direct embedding, 2+ images = averaged normalized
                    embedding_strategy = "single" if len(all_embeddings) == 1 else "averaged_normalized"
                    logger.info(f"Target {target_id} has {len(all_embeddings)} photos - using {embedding_strategy} strategy")
                    
                    milvus_id = await self.milvus_service.insert_normalized_target_embedding_async(
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
            logger.error(f"Failed to process target photos batch asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_photos': len(target_photos),
                'processed_photos': 0,
                'total_embeddings': 0
            }
    
    async def _process_photo_batch_async(self, target_photos: List, target_id: str) -> Dict:
        """
        Process a batch of target photos asynchronously
        
        Args:
            target_photos: List of TargetPhoto instances in the batch
            target_id: ID of the target
            
        Returns:
            Batch processing results dictionary
        """
        try:
            batch_embeddings = []
            batch_confidence_scores = []
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
                            from django.core.files.storage import default_storage
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
                    detection_result = await self.face_detection_service.detect_faces_in_image_async(image_path)
                    
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
                    embedding_result = await self.face_detection_service.generate_face_embeddings_async([image_path])
                    
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
                        batch_embeddings.append(embedding_array)
                        batch_confidence_scores.append(embedding_data['confidence_score'])
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
            
            return {
                'success': True,
                'embeddings': batch_embeddings,
                'confidence_scores': batch_confidence_scores,
                'processed_photos': processed_photos,
                'failed_photos': failed_photos
            }
            
        except Exception as e:
            logger.error(f"Failed to process photo batch: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': [],
                'confidence_scores': [],
                'processed_photos': 0,
                'failed_photos': []
            }
    
    def _average_embeddings(self, embeddings: List) -> List:
        """Average multiple embeddings and normalize"""
        import numpy as np
        
        if not embeddings:
            return []
        
        if len(embeddings) == 1:
            return embeddings[0]
        
        # Convert to numpy arrays if they aren't already
        np_embeddings = [np.array(emb) if not isinstance(emb, np.ndarray) else emb for emb in embeddings]
        
        # Average the embeddings
        avg_embedding = np.mean(np_embeddings, axis=0)
        
        # Normalize
        normalized_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        return normalized_embedding.tolist()
    
    async def update_target_normalized_embedding_async(self, target_id: str) -> Dict:
        """
        Update a target's normalized embedding asynchronously after photos are added/removed
        
        Args:
            target_id: ID of the target
            
        Returns:
            Update results dictionary
        """
        try:
            # Get all photos for this target using sync_to_async wrapper
            target_photos = await self._get_target_photos_sync(target_id)
            
            if not target_photos:
                # No photos left, remove the target's embedding from Milvus
                deleted_count = await self.milvus_service.delete_face_embeddings_parallel([target_id])
                logger.info(f"Removed {deleted_count} embeddings for target {target_id} (no photos left)")
                
                return {
                    'success': True,
                    'message': f"Removed embeddings for target {target_id} (no photos left)",
                    'deleted_count': deleted_count
                }
            
            # Process all photos to create updated normalized embedding
            return await self.process_target_photos_batch_async(target_photos, target_id)
            
        except Exception as e:
            logger.error(f"Failed to update target normalized embedding asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_id': target_id
            }
    
    async def get_target_face_summary_async(self, target_id: str) -> Dict:
        """
        Get a summary of face processing for a specific target asynchronously
        
        Args:
            target_id: ID of the target
            
        Returns:
            Summary of face processing results
        """
        try:
            # Get Milvus collection stats asynchronously
            milvus_stats = await self.milvus_service.get_collection_stats_async()
            
            return {
                'success': True,
                'target_id': target_id,
                'milvus_stats': milvus_stats,
                'message': f"Face processing summary for target {target_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to get target face summary asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_id': target_id
            }
    
    async def cleanup_target_embeddings_async(self, target_id: str) -> Dict:
        """
        Clean up all embeddings for a target asynchronously
        
        Args:
            target_id: ID of the target
            
        Returns:
            Cleanup results dictionary
        """
        try:
            # Delete all embeddings for this target
            deleted_count = await self.milvus_service.delete_face_embeddings_parallel([target_id])
            
            logger.info(f"Cleaned up {deleted_count} embeddings for target {target_id}")
            
            return {
                'success': True,
                'message': f"Cleaned up {deleted_count} embeddings for target {target_id}",
                'deleted_count': deleted_count
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup target embeddings asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_id': target_id
            }
