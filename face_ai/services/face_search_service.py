"""
Face Search Service
Integrates face detection and Milvus search to provide face similarity search functionality
"""

import logging
import os
import tempfile
from typing import List, Dict, Optional, Tuple
import numpy as np
from PIL import Image
import io

from .face_detection import FaceDetectionService
from .milvus_service import MilvusService
from backendapp.models import Targets_watchlist, TargetPhoto

logger = logging.getLogger(__name__)

class FaceSearchService:
    """Service for face search using face detection and Milvus vector search"""
    
    def __init__(self):
        """Initialize face detection and Milvus services"""
        try:
            self.face_detection = FaceDetectionService()
            self.milvus_service = MilvusService()
            logger.info("FaceSearchService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FaceSearchService: {e}")
            raise
    
    def search_faces_in_image(self, image_file, top_k: int = 5, confidence_threshold: float = 0.6) -> Dict:
        """
        Main method to search for similar faces in uploaded image
        
        Args:
            image_file: Uploaded image file
            top_k: Maximum number of results to return
            confidence_threshold: Minimum similarity score threshold
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in image_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            try:
                # Detect faces in the uploaded image
                detection_result = self.face_detection.detect_faces_in_image(temp_path)
                
                if not detection_result['success']:
                    return {
                        'success': False,
                        'error': detection_result['error'],
                        'results': []
                    }
                
                if detection_result['faces_detected'] == 0:
                    return {
                        'success': False,
                        'error': 'No faces detected in the uploaded image',
                        'results': []
                    }
                
                if detection_result['faces_detected'] > 1:
                    logger.warning(f"Multiple faces detected ({detection_result['faces_detected']}), using the first one")
                
                # Get the first detected face
                first_face = detection_result['faces'][0]
                
                # Generate embedding for the detected face
                embedding_result = self.face_detection.generate_face_embeddings([temp_path])
                
                if not embedding_result['success'] or not embedding_result['embeddings']:
                    return {
                        'success': False,
                        'error': 'Failed to generate face embedding',
                        'results': []
                    }
                
                # Get the embedding vector
                face_embedding = np.array(embedding_result['embeddings'][0]['embedding'])
                
                # Search for similar faces in Milvus
                similar_faces = self.milvus_service.search_similar_faces(
                    face_embedding, 
                    top_k=top_k, 
                    threshold=confidence_threshold
                )
                
                # Enrich results with target information
                enriched_results = self._enrich_search_results(similar_faces)
                
                return {
                    'success': True,
                    'query_face_info': {
                        'bbox': first_face['bbox'],
                        'confidence': first_face['confidence'],
                        'face_area': first_face['face_area']
                    },
                    'results': enriched_results,
                    'total_results': len(enriched_results),
                    'search_metadata': {
                        'top_k': top_k,
                        'confidence_threshold': confidence_threshold,
                        'embedding_dimension': face_embedding.shape[0]
                    }
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Face search failed: {e}")
            return {
                'success': False,
                'error': f'Face search failed: {str(e)}',
                'results': []
            }
    
    def _enrich_search_results(self, milvus_results: List[Dict]) -> List[Dict]:
        """
        Enrich Milvus search results with target and photo information
        
        Args:
            milvus_results: Raw results from Milvus search
            
        Returns:
            Enriched results with target details
        """
        enriched_results = []
        
        for result in milvus_results:
            try:
                target_id = result.get('target_id')
                photo_id = result.get('photo_id')
                
                if not target_id or not photo_id:
                    continue
                
                # Get target information
                try:
                    target = Targets_watchlist.objects.get(id=target_id)
                    target_info = {
                        'id': str(target.id),
                        'name': target.target_name,
                        'gender': target.gender,
                        'age': target.age,
                        'case': target.case.case_name if target.case else None,
                        'created_at': target.created_at.isoformat() if target.created_at else None
                    }
                except Targets_watchlist.DoesNotExist:
                    target_info = {
                        'id': target_id,
                        'name': 'Unknown Target',
                        'gender': None,
                        'age': None,
                        'case': None,
                        'created_at': None
                    }
                
                # Get photo information
                try:
                    photo = TargetPhoto.objects.get(id=photo_id)
                    photo_info = {
                        'id': str(photo.id),
                        'image_url': photo.image.url if photo.image else None,
                        'uploaded_at': photo.uploaded_at.isoformat() if photo.uploaded_at else None
                    }
                except TargetPhoto.DoesNotExist:
                    photo_info = {
                        'id': photo_id,
                        'image_url': None,
                        'uploaded_at': None
                    }
                
                # Create enriched result
                enriched_result = {
                    'milvus_id': result.get('id'),
                    'similarity_score': result.get('similarity', 0.0),
                    'confidence_score': result.get('confidence', 0.0),
                    'target': target_info,
                    'photo': photo_info,
                    'created_at': result.get('created_at')
                }
                
                enriched_results.append(enriched_result)
                
            except Exception as e:
                logger.warning(f"Failed to enrich result {result}: {e}")
                continue
        
        # Sort by similarity score (highest first)
        enriched_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return enriched_results
    
    def get_search_statistics(self) -> Dict:
        """Get statistics about the face search database"""
        try:
            # Get collection statistics from Milvus
            collection = self.milvus_service.collection
            # Use num_entities instead of get_statistics
            total_vectors = collection.num_entities
            
            # Get target counts from Django models
            total_targets = Targets_watchlist.objects.count()
            total_photos = TargetPhoto.objects.count()
            
            return {
                'success': True,
                'milvus_stats': {
                    'total_vectors': total_vectors,
                    'collection_name': self.milvus_service.collection_name,
                    'dimension': self.milvus_service.dimension
                },
                'django_stats': {
                    'total_targets': total_targets,
                    'total_photos': total_photos
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
