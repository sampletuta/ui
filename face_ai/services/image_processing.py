import logging
import os
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
from django.conf import settings

from .face_detection import FaceDetectionService
from .milvus_service import MilvusService

logger = logging.getLogger(__name__)

class ImageProcessingService:
    """Service for processing images through the complete face detection pipeline"""
    
    def __init__(self):
        self.face_detection = FaceDetectionService()
        self.milvus_service = MilvusService()
        self._ensure_milvus_collection()
    
    def _ensure_milvus_collection(self):
        """Ensure Milvus collection exists"""
        try:
            self.milvus_service.create_collection_if_not_exists()
            logger.info("Milvus collection ready")
        except Exception as e:
            logger.error(f"Failed to ensure Milvus collection: {e}")
            raise
    
    def process_single_image(self, image_path: str, target_id: str) -> Dict:
        """
        Process a single image for face detection and embedding
        
        Args:
            image_path: Path to the image file
            target_id: ID of the target from Targets_watchlist
            
        Returns:
            Processing results dictionary
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Process image with face detection
            processing_result = self.face_detection.process_image(image_path, crop_faces=False)
            
            if not processing_result['processing_successful']:
                return processing_result
            
            # Store embeddings in Milvus if faces detected
            stored_embeddings = []
            if processing_result['faces']:
                stored_embeddings = self._store_face_embeddings(
                    target_id, processing_result['faces']
                )
            
            result = {
                'processing_successful': True,
                'target_id': target_id,
                'image_path': image_path,
                'total_faces_detected': processing_result['total_faces_detected'],
                'embeddings_stored': len(stored_embeddings),
                'faces': processing_result['faces'],
                'milvus_vector_ids': stored_embeddings
            }
            
            logger.info(f"Successfully processed image {image_path}: {result['total_faces_detected']} faces, {result['embeddings_stored']} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {e}")
            return {
                'processing_successful': False,
                'target_id': target_id,
                'image_path': image_path,
                'error': str(e)
            }
    
    def process_multiple_images(self, image_data: List[Dict]) -> Dict:
        """
        Process multiple images for face detection and embedding
        
        Args:
            image_data: List of dicts with 'image_path' and 'target_id'
            
        Returns:
            Processing results dictionary
        """
        try:
            if not image_data:
                return {
                    'processing_successful': False,
                    'error': 'No image data provided'
                }
            
            total_faces = 0
            total_embeddings = 0
            processed_images = []
            failed_images = []
            
            # Process each image
            for img_data in image_data:
                try:
                    result = self.process_single_image(
                        img_data['image_path'], 
                        img_data['target_id']
                    )
                    if result['processing_successful']:
                        total_faces += result['total_faces_detected']
                        total_embeddings += result['embeddings_stored']
                        processed_images.append(result)
                    else:
                        failed_images.append({
                            'target_id': img_data['target_id'],
                            'image_path': img_data['image_path'],
                            'error': result.get('error', 'Unknown error')
                        })
                except Exception as e:
                    failed_images.append({
                        'target_id': img_data['target_id'],
                        'image_path': img_data['image_path'],
                        'error': str(e)
                    })
            
            return {
                'processing_successful': True,
                'total_images_processed': len(processed_images),
                'total_images_failed': len(failed_images),
                'total_faces_detected': total_faces,
                'total_embeddings_stored': total_embeddings,
                'processed_images': processed_images,
                'failed_images': failed_images
            }
            
        except Exception as e:
            logger.error(f"Failed to process multiple images: {e}")
            return {
                'processing_successful': False,
                'error': str(e)
            }
    
    def _store_face_embeddings(self, target_id: str, faces_data: List[Dict]) -> List[int]:
        """
        Store face embeddings in Milvus
        
        Args:
            target_id: ID of the target from Targets_watchlist
            faces_data: List of detected faces data
            
        Returns:
            List of Milvus vector IDs
        """
        try:
            # Prepare data for Milvus insertion
            embeddings_data = []
            for face in faces_data:
                embeddings_data.append({
                    'embedding': face['embedding'],
                    'target_id': target_id,
                    'confidence_score': face['confidence_score'],
                    'created_at': datetime.now().isoformat()
                })
            
            # Insert into Milvus
            milvus_vector_ids = self.milvus_service.insert_face_embeddings(embeddings_data)
            
            logger.info(f"Stored {len(embeddings_data)} face embeddings for target {target_id}")
            return milvus_vector_ids
            
        except Exception as e:
            logger.error(f"Failed to store face embeddings: {e}")
            raise
    
    def search_similar_faces(self, query_embedding: np.ndarray, top_k: int = 10, 
                           threshold: float = 0.6) -> List[Dict]:
        """
        Search for similar faces in Milvus
        
        Args:
            query_embedding: Query face embedding vector
            top_k: Number of top results to return
            threshold: Similarity threshold
            
        Returns:
            List of similar face results from Milvus
        """
        try:
            # Search in Milvus
            similar_faces = self.milvus_service.search_similar_faces(
                query_embedding, top_k, threshold
            )
            
            logger.info(f"Found {len(similar_faces)} similar faces")
            return similar_faces
            
        except Exception as e:
            logger.error(f"Failed to search similar faces: {e}")
            return []
    
    def delete_face_embeddings(self, vector_ids: List[int]) -> int:
        """Delete face embeddings from Milvus by vector IDs"""
        try:
            deleted_count = 0
            for vector_id in vector_ids:
                if self.milvus_service.delete_face_embedding(vector_id):
                    deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} face embeddings from Milvus")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete face embeddings: {e}")
            return 0
    
    def get_milvus_stats(self) -> Dict:
        """Get Milvus collection statistics"""
        try:
            return self.milvus_service.get_collection_stats()
        except Exception as e:
            logger.error(f"Failed to get Milvus stats: {e}")
            return {}
