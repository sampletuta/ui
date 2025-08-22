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
                        'error': 'No faces detected in the uploaded image. Please ensure the image contains clear, visible faces.',
                        'results': []
                    }
                
                # Handle multiple faces - search for each detected face
                all_search_results = []
                all_query_faces = []
                
                # Process each detected face individually for better accuracy
                for i, face in enumerate(detection_result['faces']):
                    try:
                        # Generate embedding for this specific face
                        face_embedding = self._generate_embedding_for_face(temp_path, face)
                        
                        if face_embedding is None:
                            logger.warning(f"Could not generate embedding for face {i} (bbox: {face.get('bbox', 'unknown')})")
                            continue
                        
                        logger.info(f"Generated embedding for face {i}: shape={face_embedding.shape}, bbox={face.get('bbox', 'unknown')}")
                        
                        # Search for similar faces in Milvus
                        similar_faces = self.milvus_service.search_similar_faces(
                            face_embedding, 
                            top_k=top_k, 
                            threshold=confidence_threshold
                        )
                        
                        logger.info(f"Face {i}: Found {len(similar_faces)} similar faces in Milvus (threshold: {confidence_threshold})")
                        
                        # Enrich results with target information
                        enriched_results = self._enrich_search_results(similar_faces)
                        
                        # Store results for this face
                        face_results = {
                            'face_index': i,
                            'face_info': {
                                'bbox': face['bbox'],
                                'confidence': face['confidence'],
                                'face_area': face['face_area'],
                                'age': face.get('age'),
                                'gender': face.get('gender')
                            },
                            'results': enriched_results,
                            'total_results': len(enriched_results),
                            'search_metadata': {
                                'top_k': top_k,
                                'confidence_threshold': confidence_threshold,
                                'embedding_dimension': face_embedding.shape[0]
                            }
                        }
                        
                        all_search_results.append(face_results)
                        all_query_faces.append(face)
                        
                    except Exception as e:
                        logger.warning(f"Failed to process face {i}: {e}")
                        continue
                
                if not all_search_results:
                    return {
                        'success': False,
                        'error': 'Failed to process any of the detected faces',
                        'results': []
                    }
                
                return {
                    'success': True,
                    'multiple_faces': len(all_search_results) > 1,
                    'faces_processed': len(all_search_results),
                    'total_faces_detected': detection_result['faces_detected'],
                    'query_faces': all_query_faces,
                    'search_results': all_search_results,
                    'combined_results': self._combine_search_results(all_search_results),
                    'search_metadata': {
                        'top_k': top_k,
                        'confidence_threshold': confidence_threshold,
                        'embedding_dimension': face_embedding.shape[0] if face_embedding is not None else 0
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
    
    def _generate_embedding_for_face(self, image_path: str, face_data: Dict) -> Optional[np.ndarray]:
        """
        Generate embedding for a specific detected face
        
        Args:
            image_path: Path to the image file
            face_data: Face detection data with bbox information
            
        Returns:
            Face embedding as numpy array or None if failed
        """
        try:
            # Use the face detection service to generate embedding for this specific face
            # We'll use the InsightFace app directly for better control
            import cv2
            from insightface.app import FaceAnalysis
            
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Failed to load image: {image_path}")
                return None
            
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Get face analysis app from the face detection service
            app = self.face_detection.app
            
            # Detect faces in the image
            faces = app.get(img_rgb)
            
            if not faces:
                logger.warning("No faces detected during embedding generation")
                return None
            
            # Find the face that matches our detected face by comparing bounding boxes
            target_bbox = face_data['bbox']
            best_match = None
            min_distance = float('inf')
            
            logger.debug(f"Looking for face with bbox: {target_bbox}")
            logger.debug(f"Found {len(faces)} faces in image during embedding generation")
            
            for face_idx, face in enumerate(faces):
                if face.det_score >= self.face_detection.confidence_threshold:
                    face_bbox = face.bbox.astype(int)
                    
                    # Calculate distance between bounding box centers
                    face_center = [(face_bbox[0] + face_bbox[2]) / 2, (face_bbox[1] + face_bbox[3]) / 2]
                    target_center = [(target_bbox[0] + target_bbox[2]) / 2, (target_bbox[1] + target_bbox[3]) / 2]
                    
                    distance = ((face_center[0] - target_center[0]) ** 2 + (face_center[1] - target_center[1]) ** 2) ** 0.5
                    
                    logger.debug(f"Face {face_idx}: bbox={face_bbox.tolist()}, center={face_center}, distance={distance:.2f}")
                    
                    if distance < min_distance:
                        min_distance = distance
                        best_match = face
                        logger.debug(f"New best match: face {face_idx} with distance {distance:.2f}")
            
            if best_match is None:
                logger.warning("Could not find matching face for embedding generation")
                return None
            
            # Check if the match is close enough (within reasonable distance)
            if min_distance > 50:  # 50 pixels tolerance
                logger.warning(f"Best face match too far from detected face: {min_distance} pixels")
                return None
            
            # Generate embedding for the matched face
            embedding = best_match.normed_embedding
            
            if embedding is None:
                logger.warning("Failed to generate embedding for matched face")
                return None
            
            return np.array(embedding)
            
        except Exception as e:
            logger.error(f"Error generating embedding for face: {e}")
            return None
    
    def _combine_search_results(self, all_search_results: List[Dict]) -> List[Dict]:
        """
        Combine search results from multiple faces, removing duplicates and ranking by similarity
        
        Args:
            all_search_results: List of search results for each face
            
        Returns:
            Combined and deduplicated results
        """
        try:
            combined_results = {}
            
            for face_result in all_search_results:
                for result in face_result['results']:
                    # Use target_id + photo_id as unique key
                    key = f"{result['target']['id']}_{result['photo']['id']}"
                    
                    if key not in combined_results:
                        combined_results[key] = result
                    else:
                        # If we already have this result, keep the one with higher similarity
                        if result['similarity_score'] > combined_results[key]['similarity_score']:
                            combined_results[key] = result
                            # Add face index information
                            combined_results[key]['matched_faces'] = [face_result['face_index']]
                        else:
                            # Add this face index to the existing result
                            if 'matched_faces' not in combined_results[key]:
                                combined_results[key]['matched_faces'] = []
                            if face_result['face_index'] not in combined_results[key]['matched_faces']:
                                combined_results[key]['matched_faces'].append(face_result['face_index'])
            
            # Convert back to list and sort by similarity score
            combined_list = list(combined_results.values())
            combined_list.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return combined_list
            
        except Exception as e:
            logger.error(f"Error combining search results: {e}")
            return []
    
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
