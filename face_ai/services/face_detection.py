import logging
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import insightface
from insightface.app import FaceAnalysis
from PIL import Image
import os
import base64
import io

logger = logging.getLogger(__name__)

class FaceDetectionService:
    """Service for face detection, embedding generation, and verification using InsightFace"""
    
    def __init__(self, model_name='buffalo_l', providers=['CPUExecutionProvider']):
        """
        Initialize InsightFace model
        
        Args:
            model_name: InsightFace model name (buffalo_l, buffalo_m, buffalo_s)
            providers: Execution providers (CPUExecutionProvider, CUDAExecutionProvider)
        """
        try:
            self.app = FaceAnalysis(name=model_name, providers=providers)
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info(f"Initialized InsightFace model: {model_name}")
            
            # Configuration
            self.min_face_size = 20
            self.confidence_threshold = 0.5
            self.embedding_dim = 512
            
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            raise
    
    def detect_faces_in_image(self, image_path: str) -> Dict:
        """
        API 1: Detect faces in an image and return detection results
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with face detection results
        """
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
                'message': f"Detected {len(detected_faces)} face(s) in image"
            }
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }

    def detect_faces_in_image_base64(self, base64_string: str) -> Dict:
        """
        Detect faces in a base64 encoded image for validation
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            Dictionary with face detection results
        """
        try:
            # Convert base64 to image
            img = self._base64_to_image(base64_string)
            if img is None:
                return {
                    'success': False,
                    'error': 'Invalid base64 image data',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Detect faces
            faces = self.app.get(img)
            
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
                'message': f"Detected {len(detected_faces)} face(s) in image"
            }
            
        except Exception as e:
            logger.error(f"Base64 face detection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }
    
    def generate_face_embeddings(self, image_paths: List[str]) -> Dict:
        """
        API 2: Generate face embeddings for multiple images (all must have faces)
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            Dictionary with embedding results
        """
        try:
            if not image_paths:
                return {
                    'success': False,
                    'error': 'No image paths provided',
                    'embeddings': []
                }
            
            all_embeddings = []
            failed_images = []
            
            for image_path in image_paths:
                # First check if image has faces
                detection_result = self.detect_faces_in_image(image_path)
                
                if not detection_result['success']:
                    failed_images.append({
                        'image_path': image_path,
                        'error': detection_result['error']
                    })
                    continue
                
                if detection_result['faces_detected'] == 0:
                    failed_images.append({
                        'image_path': image_path,
                        'error': 'No faces detected in image'
                    })
                    continue
                
                # Generate embeddings for detected faces
                try:
                    img = cv2.imread(image_path)
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    faces = self.app.get(img_rgb)
                    
                    image_embeddings = []
                    for face in faces:
                        if face.det_score >= self.confidence_threshold:
                            embedding_data = {
                                'image_path': image_path,
                                'embedding': face.normed_embedding.tolist(),
                                'confidence_score': float(face.det_score),
                                'bbox': face.bbox.astype(int).tolist(),
                                'age': int(face.age) if hasattr(face, 'age') and face.age is not None else None,
                                'gender': 'male' if (hasattr(face, 'gender') and face.gender == 1) else 'female' if (hasattr(face, 'gender') and face.gender == 0) else None
                            }
                            image_embeddings.append(embedding_data)
                    
                    all_embeddings.extend(image_embeddings)
                    
                except Exception as e:
                    failed_images.append({
                        'image_path': image_path,
                        'error': f'Failed to generate embeddings: {str(e)}'
                    })
            
            return {
                'success': True,
                'total_embeddings': len(all_embeddings),
                'embeddings': all_embeddings,
                'failed_images': failed_images,
                'message': f"Generated {len(all_embeddings)} embeddings from {len(image_paths)} images"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate face embeddings: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': []
            }
    
    def verify_faces(self, image1_base64: str, image2_base64: str, confidence_threshold: float = 50.0) -> Dict:
        """
        API 3: Face verification with age and gender estimation
        
        Args:
            image1_base64: Base64 encoded first image
            image2_base64: Base64 encoded second image
            confidence_threshold: Similarity threshold (0-100, default 50)
            
        Returns:
            Dictionary with verification results, age, and gender
        """
        try:
            # Convert base64 to images
            img1 = self._base64_to_image(image1_base64)
            img2 = self._base64_to_image(image2_base64)
            
            if img1 is None or img2 is None:
                return {
                    'success': False,
                    'error': 'Invalid base64 image data'
                }
            
            # Detect faces in both images
            faces1 = self.app.get(img1)
            faces2 = self.app.get(img2)
            
            if not faces1 or not faces2:
                return {
                    'success': False,
                    'error': 'No faces detected in one or both images'
                }
            
            # Get the first detected face from each image
            face1 = faces1[0] if faces1 else None
            face2 = faces2[0] if faces2 else None
            
            if not face1 or not face2:
                return {
                    'success': False,
                    'error': 'Failed to extract faces from images'
                }
            
            # Calculate similarity
            embedding1 = face1.normed_embedding
            embedding2 = face2.normed_embedding
            
            # Convert threshold from percentage to decimal
            threshold_decimal = confidence_threshold / 100.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2)
            similarity_percentage = similarity * 100
            
            # Determine if faces match
            faces_match = similarity_percentage >= confidence_threshold
            
            # Extract age and gender from both faces
            age1 = int(face1.age) if hasattr(face1, 'age') and face1.age is not None else None
            age2 = int(face2.age) if hasattr(face2, 'age') and face2.age is not None else None
            gender1 = 'male' if (hasattr(face1, 'gender') and face1.gender == 1) else 'female' if (hasattr(face1, 'gender') and face1.gender == 0) else None
            gender2 = 'male' if (hasattr(face2, 'gender') and face2.gender == 1) else 'female' if (hasattr(face2, 'gender') and face2.gender == 0) else None
            
            return {
                'success': True,
                'faces_match': faces_match,
                'similarity_score': round(similarity_percentage, 2),
                'confidence_threshold': confidence_threshold,
                'threshold_met': faces_match,
                'face1': {
                    'age': age1,
                    'gender': gender1,
                    'confidence': float(face1.det_score)
                },
                'face2': {
                    'age': age2,
                    'gender': gender2,
                    'confidence': float(face2.det_score)
                },
                'message': f"Faces {'match' if faces_match else 'do not match'} with {similarity_percentage:.2f}% similarity"
            }
            
        except Exception as e:
            logger.error(f"Face verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _base64_to_image(self, base64_string: str) -> Optional[np.ndarray]:
        """Convert base64 string to numpy image array"""
        try:
            # Remove data URL prefix if present
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Convert RGB to BGR if needed
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            return image_array
            
        except Exception as e:
            logger.error(f"Failed to convert base64 to image: {e}")
            return None
    
    def image_to_base64(self, image_field) -> str:
        """Convert Django ImageField to base64 string"""
        try:
            # Open the image file
            with image_field.open('rb') as image_file:
                # Read the image data
                image_data = image_file.read()
                # Encode to base64
                base64_string = base64.b64encode(image_data).decode('utf-8')
                return base64_string
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            'model_name': self.app.models.get('detection', 'Unknown'),
            'embedding_dimension': self.embedding_dim,
            'confidence_threshold': self.confidence_threshold,
            'min_face_size': self.min_face_size
        }
