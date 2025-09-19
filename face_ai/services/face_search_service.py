"""
Face Search Service
Integrates face detection (OpenCV Yunet) and embedding generation (Facenet) with Milvus search
to provide face similarity search functionality
"""

import logging
import os
import tempfile
from typing import List, Dict, Optional, Tuple
import numpy as np
from PIL import Image
import io

from .face_detection import FaceDetectionService
from .face_embedding_service import FaceEmbeddingService
# from .milvus_service import MilvusService  # Commented out for standalone testing
# from backendapp.models import Targets_watchlist, TargetPhoto  # Commented out for standalone testing

logger = logging.getLogger(__name__)

class MockMilvusService:
    """Mock Milvus service for testing without Django dependencies"""
    
    def __init__(self):
        logger.info("Initialized Mock Milvus Service for testing")
    
    def search_similar_faces(self, face_embedding, top_k=5, threshold=0.6):
        """Mock search that returns synthetic results for testing"""
        logger.info(f"Mock search: looking for {top_k} similar faces with threshold {threshold}")
        
        # Return mock results for testing
        mock_results = []
        for i in range(min(top_k, 3)):  # Return up to 3 mock results
            mock_results.append({
                'target_id': f'mock_target_{i+1}',
                'photo_id': f'mock_photo_{i+1}',
                'similarity_score': round(0.8 - (i * 0.1), 2),  # Decreasing similarity
                'distance': round(0.2 + (i * 0.1), 3)
            })
        
        logger.info(f"Mock search returned {len(mock_results)} results")
        return mock_results
    
    def get_collection_info(self):
        """Mock collection info"""
        return {
            'collection_name': 'mock_watchlist',
            'status': 'mock_available',
            'total_vectors': 1000
        }

class FaceSearchService:
    """Service for face search using OpenCV Yunet detection and Facenet embeddings with Milvus vector search"""
    
    def __init__(self):
        """Initialize face detection, embedding, and Milvus services"""
        try:
            self.face_detection = FaceDetectionService()
            self.face_embedding = FaceEmbeddingService()
            
            # Use mock Milvus service for testing
            try:
                from .milvus_service import MilvusService
                self.milvus_service = MilvusService()
                logger.info("FaceSearchService initialized with real Milvus service")
            except Exception as e:
                logger.warning(f"Failed to initialize real Milvus service: {e}")
                logger.info("Falling back to Mock Milvus service for testing")
                self.milvus_service = MockMilvusService()
            
            logger.info("FaceSearchService initialized successfully with Yunet + Facenet")
        except Exception as e:
            logger.error(f"Failed to initialize FaceSearchService: {e}")
            raise
    
    def search_faces_in_image(self, image_file, top_k: int = 5, confidence_threshold: float = 0.6, apply_rerank: bool = True) -> Dict:
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
                # Detect faces in the uploaded image using Yunet
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
                        # Generate embedding for this specific face using Facenet
                        face_embedding = self._generate_embedding_for_face(temp_path, face)
                        
                        if face_embedding is None:
                            logger.warning(f"Could not generate embedding for face {i} (bbox: {face.get('bbox', 'unknown')})")
                            continue
                        
                        logger.info(f"Generated Facenet embedding for face {i}: shape={face_embedding.shape}, bbox={face.get('bbox', 'unknown')}")
                        
                        # Search for similar faces in Milvus
                        similar_faces = self.milvus_service.search_similar_faces(
                            face_embedding,
                            top_k=top_k,
                            threshold=confidence_threshold
                        )

                        # Apply query-time re-ranking if requested and available
                        if apply_rerank:
                            try:
                                from .re_ranking import ReRanker
                                reranker = ReRanker()
                                query_meta = {'source': 'uploaded_image'}
                                similar_faces = reranker.rerank(face_embedding, similar_faces, query_meta=query_meta)
                            except Exception as e:
                                logger.debug(f"Re-ranking not applied: {e}")
                        
                        logger.info(f"Face {i}: Found {len(similar_faces)} similar faces in Milvus (threshold: {confidence_threshold})")
                        
                        # Enrich results with target information
                        enriched_results = self._enrich_search_results(similar_faces)

                        # Ensure each enriched result contains final_score/embed_score for template display
                        for r in enriched_results:
                            if 'final_score' not in r:
                                r['final_score'] = r.get('similarity_score', 0.0)
                            if 'embed_score' not in r:
                                r['embed_score'] = r.get('similarity_score', 0.0)
                            if 'metadata_score' not in r:
                                r['metadata_score'] = 0.0
                        
                        # Store results for this face
                        face_results = {
                            'face_index': i,
                            'face_bbox': face.get('bbox', []),
                            'face_confidence': face.get('confidence', 0.0),
                            'similar_faces': enriched_results,
                            'total_similar': len(enriched_results)
                        }
                        
                        all_search_results.append(face_results)
                        all_query_faces.append({
                            'index': i,
                            'bbox': face.get('bbox', []),
                            'confidence': face.get('confidence', 0.0)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing face {i}: {e}")
                        continue
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                if not all_search_results:
                    return {
                        'success': False,
                        'error': 'Failed to process any detected faces',
                        'results': []
                    }
                
                return {
                    'success': True,
                    'total_faces_detected': detection_result['faces_detected'],
                    'query_faces': all_query_faces,
                    'search_results': all_search_results,
                    'total_similar_faces': sum(result['total_similar'] for result in all_search_results),
                    'message': f"Successfully processed {len(all_search_results)} faces and found {sum(result['total_similar'] for result in all_search_results)} similar faces"
                }
                
            except Exception as e:
                # Clean up temporary file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e
                
        except Exception as e:
            logger.error(f"Face search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def _generate_embedding_for_face(self, image_path: str, face: Dict) -> Optional[np.ndarray]:
        """
        Generate Facenet embedding for a specific face in an image
        
        Args:
            image_path: Path to the image file
            face: Face detection data with bbox
            
        Returns:
            Face embedding as numpy array or None if failed
        """
        try:
            bbox = face.get('bbox')
            if not bbox or len(bbox) != 4:
                logger.error(f"Invalid bbox for face: {bbox}")
                return None
            
            # Generate embedding using Facenet service
            embedding = self.face_embedding.generate_embedding_from_image(image_path, bbox)
            
            if embedding is not None:
                logger.info(f"Generated Facenet embedding: shape={embedding.shape}, norm={np.linalg.norm(embedding):.4f}")
                return embedding
            else:
                logger.error(f"Failed to generate Facenet embedding for face with bbox: {bbox}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating Facenet embedding: {e}")
            return None
    
    def _enrich_search_results(self, similar_faces: List[Dict]) -> List[Dict]:
        """
        Enrich Milvus search results with target information
        
        Args:
            similar_faces: List of similar faces from Milvus
            
        Returns:
            List of enriched results with target details
        """
        try:
            enriched_results = []
            
            for face_result in similar_faces:
                try:
                    # Extract target ID from the result
                    target_id = face_result.get('target_id')
                    if not target_id:
                        continue
                    
                    # Get target information from database
                    target_info = self._get_target_info(target_id)
                    
                    if target_info:
                        enriched_result = {
                            'target_id': target_id,
                            'similarity_score': face_result.get('similarity_score', 0.0),
                            'target_name': target_info.get('name', 'Unknown'),
                            'target_photo_id': face_result.get('photo_id'),
                            'target_category': target_info.get('category', 'Unknown'),
                            'target_status': target_info.get('status', 'Unknown'),
                            'embedding_distance': face_result.get('distance', 0.0)
                        }
                        enriched_results.append(enriched_result)
                    
                except Exception as e:
                    logger.error(f"Error enriching result for target {face_result.get('target_id')}: {e}")
                    continue
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error enriching search results: {e}")
            return []
    
    def _get_target_info(self, target_id: str) -> Optional[Dict]:
        """
        Get target information from database
        
        Args:
            target_id: Target identifier
            
        Returns:
            Dictionary with target information or None if not found
        """
        try:
            # Try to get target from watchlist first
            # target = Targets_watchlist.objects.filter(id=target_id).first()  # Commented out for standalone testing
            
            # For standalone testing, return mock data
            return {
                'name': f'Target_{target_id}',
                'category': 'Test',
                'status': 'Active',
                'source': 'mock_data'
            }
            
            # If not in watchlist, try other target models
            # Add additional target model queries here as needed
            
            # return None
            
        except Exception as e:
            logger.error(f"Error getting target info for {target_id}: {e}")
            return None
    
    def search_faces_by_embedding(self, face_embedding: np.ndarray, top_k: int = 5, 
                                confidence_threshold: float = 0.6) -> Dict:
        """
        Search for similar faces using a pre-computed embedding
        
        Args:
            face_embedding: Pre-computed face embedding
            top_k: Maximum number of results to return
            confidence_threshold: Minimum similarity score threshold
            
        Returns:
            Dictionary with search results
        """
        try:
            if face_embedding is None:
                return {
                    'success': False,
                    'error': 'No face embedding provided',
                    'results': []
                }
            
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
                'total_similar_faces': len(enriched_results),
                'search_results': enriched_results,
                'message': f"Found {len(enriched_results)} similar faces"
            }
            
        except Exception as e:
            logger.error(f"Face search by embedding failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def verify_faces(self, image1_file, image2_file, confidence_threshold: float = 0.6) -> Dict:
        """
        Verify if two images contain the same person
        
        Args:
            image1_file: First image file
            image2_file: Second image file
            confidence_threshold: Similarity threshold for verification
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Save both files temporarily
            temp_paths = []
            try:
                # Save first image
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    for chunk in image1_file.chunks():
                        temp_file.write(chunk)
                    temp_path1 = temp_file.name
                    temp_paths.append(temp_path1)
                
                # Save second image
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    for chunk in image2_file.chunks():
                        temp_file.write(chunk)
                    temp_path2 = temp_file.name
                    temp_paths.append(temp_path2)
                
                # Detect faces in both images
                faces1_result = self.face_detection.detect_faces_in_image(temp_path1)
                faces2_result = self.face_detection.detect_faces_in_image(temp_path2)
                
                if not faces1_result['success'] or not faces2_result['success']:
                    return {
                        'success': False,
                        'error': f"Face detection failed: {faces1_result.get('error', '')} {faces2_result.get('error', '')}"
                    }
                
                if faces1_result['faces_detected'] == 0 or faces2_result['faces_detected'] == 0:
                    return {
                        'success': False,
                        'error': 'No faces detected in one or both images'
                    }
                
                # Get the first detected face from each image
                face1 = faces1_result['faces'][0]
                face2 = faces2_result['faces'][0]
                
                # Generate embeddings for both faces
                embedding1 = self._generate_embedding_for_face(temp_path1, face1)
                embedding2 = self._generate_embedding_for_face(temp_path2, face2)
                
                if embedding1 is None or embedding2 is None:
                    return {
                        'success': False,
                        'error': 'Failed to generate embeddings for one or both faces'
                    }
                
                # Verify faces using embeddings
                verification_result = self.face_embedding.verify_faces_with_embeddings(
                    embedding1, embedding2, confidence_threshold
                )
                
                # Clean up temporary files
                for temp_path in temp_paths:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
                return {
                    'success': True,
                    'verification_result': verification_result,
                    'face1_info': {
                        'bbox': face1.get('bbox', []),
                        'confidence': face1.get('confidence', 0.0)
                    },
                    'face2_info': {
                        'bbox': face2.get('bbox', []),
                        'confidence': face2.get('confidence', 0.0)
                    }
                }
                
            except Exception as e:
                # Clean up temporary files on error
                for temp_path in temp_paths:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                raise e
                
        except Exception as e:
            logger.error(f"Face verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_service_info(self) -> Dict:
        """Get information about the face search service"""
        try:
            detection_info = self.face_detection.get_model_info()
            embedding_info = self.face_embedding.get_model_info()
            milvus_info = self.milvus_service.get_collection_info() if hasattr(self.milvus_service, 'get_collection_info') else {}
            
            return {
                'service_name': 'FaceSearchService',
                'detection_model': detection_info,
                'embedding_model': embedding_info,
                'vector_database': milvus_info,
                'status': 'operational'
            }
            
        except Exception as e:
            logger.error(f"Error getting service info: {e}")
            return {
                'service_name': 'FaceSearchService',
                'status': 'error',
                'error': str(e)
            }
