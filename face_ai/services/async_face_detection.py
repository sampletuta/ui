"""
Async Face Detection Service for parallel processing.

This service provides async-compatible methods for face detection, embedding generation,
and verification with support for parallel processing and batch operations.
"""

import logging
import asyncio
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import insightface
from insightface.app import FaceAnalysis
from PIL import Image
import os
import base64
import io
from concurrent.futures import ThreadPoolExecutor
from asgiref.sync import sync_to_async
import time

logger = logging.getLogger(__name__)

class AsyncFaceDetectionService:
    """Async service for face detection, embedding generation, and verification using InsightFace"""
    
    def __init__(self, model_name='buffalo_l', providers=['CPUExecutionProvider'], max_workers=4):
        """
        Initialize Async InsightFace model
        
        Args:
            model_name: InsightFace model name (buffalo_l, buffalo_m, buffalo_s)
            providers: Execution providers (CPUExecutionProvider, CUDAExecutionProvider)
            max_workers: Maximum number of parallel workers
        """
        try:
            self.app = FaceAnalysis(name=model_name, providers=providers)
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            self.max_workers = max_workers
            logger.info(f"Initialized Async InsightFace model: {model_name} with {max_workers} workers")
            
            # Configuration
            self.min_face_size = 20
            self.confidence_threshold = 0.5
            self.embedding_dim = 512
            
            # Thread pool for CPU-bound operations
            self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
            
        except Exception as e:
            logger.error(f"Failed to initialize Async InsightFace: {e}")
            raise
    
    async def detect_faces_in_image_async(self, image_path: str) -> Dict:
        """
        Async API 1: Detect faces in an image with parallel processing
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with face detection results
        """
        try:
            # Run face detection in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._detect_faces_sync,
                image_path
            )
            return result
            
        except Exception as e:
            logger.error(f"Error in async face detection: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }
    
    async def detect_faces_in_image_sync(self, image_path: str) -> Dict:
        """
        Async API 1: Detect faces in an image (sequential mode)
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with face detection results
        """
        try:
            # Run face detection in thread pool (sequential)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._detect_faces_sync,
                image_path
            )
            return result
            
        except Exception as e:
            logger.error(f"Error in sync face detection: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }
    
    def _detect_faces_sync(self, image_path: str) -> Dict:
        """Synchronous face detection method for thread pool execution"""
        try:
            # Load image
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': 'Image file not found',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Read image with OpenCV
            img = cv2.imread(image_path)
            if img is None:
                return {
                    'success': False,
                    'error': 'Failed to load image',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            faces = self.app.get(img_rgb)
            
            detected_faces = []
            for face in faces:
                if face.det_score >= self.confidence_threshold:
                    # Get bounding box
                    bbox = face.bbox.astype(int)
                    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
                    
                    # Validate face size
                    face_width = x2 - x1
                    face_height = y2 - y1
                    if face_width < self.min_face_size or face_height < self.min_face_size:
                        continue
                    
                    face_data = {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(face.det_score),
                        'landmarks': face.kps.tolist() if hasattr(face, 'kps') else [],
                        'face_area': face_width * face_height
                    }
                    
                    # Add age and gender if available
                    if hasattr(face, 'age') and face.age is not None:
                        face_data['age'] = int(face.age)
                    if hasattr(face, 'gender') and face.gender is not None:
                        face_data['gender'] = 'male' if face.gender == 1 else 'female'
                    
                    detected_faces.append(face_data)
            
            return {
                'success': True,
                'faces_detected': len(detected_faces),
                'faces': detected_faces,
                'image_path': image_path,
                'processing_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error in synchronous face detection: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }
    
    async def generate_face_embeddings_parallel(self, image_paths: List[str], batch_size: int = 10) -> Dict:
        """
        Async API 2: Generate face embeddings for multiple images with parallel processing
        
        Args:
            image_paths: List of image paths
            batch_size: Size of batches for parallel processing
            
        Returns:
            Dictionary with embedding results
        """
        try:
            start_time = time.time()
            
            # Process images in parallel batches
            all_embeddings = []
            all_faces = []
            
            # Create batches
            batches = [image_paths[i:i + batch_size] for i in range(0, len(image_paths), batch_size)]
            
            # Process batches in parallel
            batch_tasks = []
            for batch in batches:
                task = self._process_batch_embeddings(batch)
                batch_tasks.append(task)
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch {i} failed: {result}")
                    continue
                
                if result['success']:
                    all_embeddings.extend(result.get('embeddings', []))
                    all_faces.extend(result.get('faces', []))
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'total_images': len(image_paths),
                'total_faces': len(all_faces),
                'total_embeddings': len(all_embeddings),
                'embeddings': all_embeddings,
                'faces': all_faces,
                'processing_time': processing_time,
                'batch_size': batch_size,
                'parallel_workers': self.max_workers
            }
            
        except Exception as e:
            logger.error(f"Error in parallel embedding generation: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_images': len(image_paths),
                'total_faces': 0,
                'total_embeddings': 0
            }
    
    async def generate_face_embeddings_sequential(self, image_paths: List[str]) -> Dict:
        """
        Async API 2: Generate face embeddings for multiple images (sequential mode)
        
        Args:
            image_paths: List of image paths
            
        Returns:
            Dictionary with embedding results
        """
        try:
            start_time = time.time()
            
            # Process images sequentially
            all_embeddings = []
            all_faces = []
            
            for image_path in image_paths:
                result = await self._generate_single_embedding(image_path)
                if result['success']:
                    all_embeddings.extend(result.get('embeddings', []))
                    all_faces.extend(result.get('faces', []))
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'total_images': len(image_paths),
                'total_faces': len(all_faces),
                'total_embeddings': len(all_embeddings),
                'embeddings': all_embeddings,
                'faces': all_faces,
                'processing_time': processing_time,
                'parallel_workers': 1
            }
            
        except Exception as e:
            logger.error(f"Error in sequential embedding generation: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_images': len(image_paths),
                'total_faces': 0,
                'total_embeddings': 0
            }
    
    async def _process_batch_embeddings(self, batch_paths: List[str]) -> Dict:
        """Process a batch of images for embeddings"""
        try:
            batch_embeddings = []
            batch_faces = []
            
            # Process batch in parallel using thread pool
            loop = asyncio.get_event_loop()
            tasks = []
            
            for image_path in batch_paths:
                task = loop.run_in_executor(
                    self.thread_pool,
                    self._generate_single_embedding_sync,
                    image_path
                )
                tasks.append(task)
            
            # Wait for all tasks in batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Single embedding generation failed: {result}")
                    continue
                
                if result['success']:
                    batch_embeddings.extend(result.get('embeddings', []))
                    batch_faces.extend(result.get('faces', []))
            
            return {
                'success': True,
                'embeddings': batch_embeddings,
                'faces': batch_faces,
                'batch_size': len(batch_paths)
            }
            
        except Exception as e:
            logger.error(f"Error processing batch embeddings: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': [],
                'faces': []
            }
    
    async def _generate_single_embedding(self, image_path: str) -> Dict:
        """Generate embeddings for a single image asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._generate_single_embedding_sync,
                image_path
            )
            return result
            
        except Exception as e:
            logger.error(f"Error generating single embedding: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': [],
                'faces': []
            }
    
    def _generate_single_embedding_sync(self, image_path: str) -> Dict:
        """Synchronous method for generating embeddings from a single image"""
        try:
            # First detect faces
            detection_result = self._detect_faces_sync(image_path)
            if not detection_result['success']:
                return detection_result
            
            if detection_result['faces_detected'] == 0:
                return {
                    'success': True,
                    'embeddings': [],
                    'faces': [],
                    'message': 'No faces detected in image'
                }
            
            # Load image for embedding generation
            img = cv2.imread(image_path)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Get faces and generate embeddings
            faces = self.app.get(img_rgb)
            embeddings = []
            face_data = []
            
            for face in faces:
                if face.det_score >= self.confidence_threshold:
                    # Get embedding
                    embedding = face.embedding
                    
                    # Get bounding box
                    bbox = face.bbox.astype(int)
                    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
                    
                    face_info = {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(face.det_score),
                        'embedding_dim': len(embedding)
                    }
                    
                    embeddings.append(embedding.tolist())
                    face_data.append(face_info)
            
            return {
                'success': True,
                'embeddings': embeddings,
                'faces': face_data,
                'image_path': image_path
            }
            
        except Exception as e:
            logger.error(f"Error in synchronous embedding generation: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': [],
                'faces': []
            }
    
    async def verify_faces_parallel(self, image1_base64: str, image2_base64: str, confidence_threshold: float) -> Dict:
        """
        Async API 3: Face verification with parallel processing
        
        Args:
            image1_base64: Base64 encoded first image
            image2_base64: Base64 encoded second image
            confidence_threshold: Confidence threshold for verification
            
        Returns:
            Dictionary with verification results
        """
        try:
            start_time = time.time()
            
            # Process both images in parallel
            loop = asyncio.get_event_loop()
            task1 = loop.run_in_executor(
                self.thread_pool,
                self._process_image_for_verification,
                image1_base64
            )
            task2 = loop.run_in_executor(
                self.thread_pool,
                self._process_image_for_verification,
                image2_base64
            )
            
            # Wait for both images to be processed
            result1, result2 = await asyncio.gather(task1, task2)
            
            if not result1['success'] or not result2['success']:
                return {
                    'success': False,
                    'error': f"Image processing failed: {result1.get('error', '')} {result2.get('error', '')}"
                }
            
            # Verify faces
            verification_result = await self._verify_faces_sync(
                result1['embedding'],
                result2['embedding'],
                confidence_threshold
            )
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'verification_result': verification_result,
                'image1_info': result1['face_info'],
                'image2_info': result2['face_info'],
                'processing_time': processing_time,
                'parallel_workers': 2
            }
            
        except Exception as e:
            logger.error(f"Error in parallel face verification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def verify_faces_sequential(self, image1_base64: str, image2_base64: str, confidence_threshold: float) -> Dict:
        """
        Async API 3: Face verification (sequential mode)
        
        Args:
            image1_base64: Base64 encoded first image
            image2_base64: Base64 encoded second image
            confidence_threshold: Confidence threshold for verification
            
        Returns:
            Dictionary with verification results
        """
        try:
            start_time = time.time()
            
            # Process images sequentially
            result1 = await self._process_image_for_verification_async(image1_base64)
            if not result1['success']:
                return result1
            
            result2 = await self._process_image_for_verification_async(image2_base64)
            if not result2['success']:
                return result2
            
            # Verify faces
            verification_result = await self._verify_faces_sync(
                result1['embedding'],
                result2['embedding'],
                confidence_threshold
            )
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'verification_result': verification_result,
                'image1_info': result1['face_info'],
                'image2_info': result2['face_info'],
                'processing_time': processing_time,
                'parallel_workers': 1
            }
            
        except Exception as e:
            logger.error(f"Error in sequential face verification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_image_for_verification_async(self, image_base64: str) -> Dict:
        """Process base64 image for verification asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._process_image_for_verification,
                image_base64
            )
            return result
            
        except Exception as e:
            logger.error(f"Error processing image for verification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_image_for_verification(self, image_base64: str) -> Dict:
        """Process base64 image for verification (synchronous)"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to numpy array
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Detect faces and get embeddings
            faces = self.app.get(img_array)
            
            if not faces:
                return {
                    'success': False,
                    'error': 'No faces detected in image'
                }
            
            # Get the first face with highest confidence
            best_face = max(faces, key=lambda x: x.det_score)
            
            if best_face.det_score < self.confidence_threshold:
                return {
                    'success': False,
                    'error': f'Face confidence too low: {best_face.det_score}'
                }
            
            face_info = {
                'confidence': float(best_face.det_score),
                'bbox': best_face.bbox.tolist() if hasattr(best_face, 'bbox') else []
            }
            
            return {
                'success': True,
                'embedding': best_face.embedding,
                'face_info': face_info
            }
            
        except Exception as e:
            logger.error(f"Error processing image for verification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _verify_faces_sync(self, embedding1: np.ndarray, embedding2: np.ndarray, confidence_threshold: float) -> Dict:
        """Verify two face embeddings (synchronous)"""
        try:
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
            
            # Convert to percentage
            similarity_percentage = similarity * 100
            
            # Determine match
            is_match = similarity_percentage >= confidence_threshold
            
            return {
                'similarity_score': float(similarity),
                'similarity_percentage': float(similarity_percentage),
                'is_match': bool(is_match),
                'confidence_threshold': float(confidence_threshold)
            }
            
        except Exception as e:
            logger.error(f"Error in face verification: {e}")
            return {
                'similarity_score': 0.0,
                'similarity_percentage': 0.0,
                'is_match': False,
                'confidence_threshold': float(confidence_threshold),
                'error': str(e)
            }
    
    async def batch_detect_faces(self, image_paths: List[str], max_workers: int = None) -> Dict:
        """Batch process multiple images for face detection"""
        if max_workers is None:
            max_workers = self.max_workers
        
        try:
            start_time = time.time()
            
            # Process images in parallel
            loop = asyncio.get_event_loop()
            tasks = []
            
            for image_path in image_paths:
                task = loop.run_in_executor(
                    self.thread_pool,
                    self._detect_faces_sync,
                    image_path
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Image {image_paths[i]} failed: {result}")
                    failed_count += 1
                    continue
                
                if result['success']:
                    successful_results.append(result)
            
            processing_time = time.time() - start_time
            
            total_faces = sum(result.get('faces_detected', 0) for result in successful_results)
            
            return {
                'success': True,
                'total_images': len(image_paths),
                'successful_images': len(successful_results),
                'failed_images': failed_count,
                'total_faces_detected': total_faces,
                'results': successful_results,
                'processing_time': processing_time,
                'max_workers': max_workers
            }
            
        except Exception as e:
            logger.error(f"Error in batch face detection: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_images': len(image_paths)
            }
    
    async def batch_generate_embeddings(self, image_paths: List[str], max_workers: int = None, batch_size: int = 10) -> Dict:
        """Batch process multiple images for embedding generation"""
        if max_workers is None:
            max_workers = self.max_workers
        
        try:
            start_time = time.time()
            
            # Process in batches
            batches = [image_paths[i:i + batch_size] for i in range(0, len(image_paths), batch_size)]
            
            # Process batches in parallel
            batch_tasks = []
            for batch in batches:
                task = self._process_batch_embeddings(batch)
                batch_tasks.append(task)
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            all_embeddings = []
            all_faces = []
            successful_batches = 0
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch failed: {result}")
                    continue
                
                if result['success']:
                    all_embeddings.extend(result.get('embeddings', []))
                    all_faces.extend(result.get('faces', []))
                    successful_batches += 1
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'total_images': len(image_paths),
                'successful_batches': successful_batches,
                'total_embeddings': len(all_embeddings),
                'total_faces': len(all_faces),
                'embeddings': all_embeddings,
                'faces': all_faces,
                'processing_time': processing_time,
                'max_workers': max_workers,
                'batch_size': batch_size
            }
            
        except Exception as e:
            logger.error(f"Error in batch embedding generation: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_images': len(image_paths)
            }
    
    async def batch_verify_faces(self, face_pairs: List[Dict], max_workers: int = None, confidence_threshold: float = 50.0) -> Dict:
        """Batch verify multiple face pairs"""
        if max_workers is None:
            max_workers = self.max_workers
        
        try:
            start_time = time.time()
            
            # Process verification tasks in parallel
            loop = asyncio.get_event_loop()
            tasks = []
            
            for pair in face_pairs:
                image1 = pair.get('image1_base64')
                image2 = pair.get('image2_base64')
                
                if image1 and image2:
                    task = self.verify_faces_parallel(image1, image2, confidence_threshold)
                    tasks.append(task)
            
            # Wait for all verifications to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            successful_verifications = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Verification {i} failed: {result}")
                    failed_count += 1
                    continue
                
                if result['success']:
                    successful_verifications.append(result)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'total_pairs': len(face_pairs),
                'successful_verifications': len(successful_verifications),
                'failed_verifications': failed_count,
                'results': successful_verifications,
                'processing_time': processing_time,
                'max_workers': max_workers,
                'confidence_threshold': confidence_threshold
            }
            
        except Exception as e:
            logger.error(f"Error in batch face verification: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_pairs': len(face_pairs)
            }
    
    async def realtime_detect_faces(self, image_path: str, stream_mode: str = 'single') -> Dict:
        """Real-time face detection with streaming support"""
        try:
            start_time = time.time()
            
            # Detect faces
            result = await self.detect_faces_in_image_async(image_path)
            
            if result['success']:
                processing_time = time.time() - start_time
                result['realtime_metrics'] = {
                    'processing_time': processing_time,
                    'fps': 1.0 / processing_time if processing_time > 0 else 0,
                    'stream_mode': stream_mode
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in realtime face detection: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def realtime_verify_faces(self, image1_base64: str, image2_base64: str, confidence_threshold: float, stream_mode: str = 'single') -> Dict:
        """Real-time face verification with streaming support"""
        try:
            start_time = time.time()
            
            # Verify faces
            result = await self.verify_faces_parallel(image1_base64, image2_base64, confidence_threshold)
            
            if result['success']:
                processing_time = time.time() - start_time
                result['realtime_metrics'] = {
                    'processing_time': processing_time,
                    'fps': 1.0 / processing_time if processing_time > 0 else 0,
                    'stream_mode': stream_mode
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in realtime face verification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
