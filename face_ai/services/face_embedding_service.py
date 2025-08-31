import logging
import torch
import torch.nn.functional as F
from facenet_pytorch import InceptionResnetV1
from PIL import Image
import numpy as np
from typing import List, Dict, Optional, Tuple
import cv2
import os
import base64
import io

logger = logging.getLogger(__name__)

class FaceEmbeddingService:
    """Service for generating face embeddings using Facenet-Pytorch InceptionResnetV1"""
    
    def __init__(self, device=None, model_path=None):
        """
        Initialize Facenet embedding model
        
        Args:
            device: PyTorch device ('cuda', 'cpu', or None for auto-detection)
            model_path: Path to custom model weights (optional)
        """
        try:
            # Set device
            if device is None:
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            else:
                self.device = torch.device(device)
            
            logger.info(f"Using device: {self.device}")
            
            # Load Facenet model
            self.model = InceptionResnetV1(pretrained='vggface2')
            self.model.to(self.device)
            self.model.eval()
            
            # Configuration
            self.embedding_dim = 512
            self.face_size = (160, 160)  # Facenet input size
            self.mean = np.array([131.0912, 103.8827, 91.4953])  # Facenet normalization
            self.std = np.array([1, 1, 1])
            
            logger.info(f"Initialized Facenet model with {self.embedding_dim}-dimensional embeddings")
            
        except Exception as e:
            logger.error(f"Failed to initialize Facenet model: {e}")
            raise
    
    def generate_embedding_from_image(self, image_path: str, bbox: List[int]) -> Optional[np.ndarray]:
        """
        Generate embedding for a specific face in an image
        
        Args:
            image_path: Path to the image file
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Face embedding as numpy array (512-dimensional) or None if failed
        """
        try:
            logger.info(f"🔄 Starting embedding generation for image: {image_path}")
            logger.info(f"  Bounding box: {bbox}")
            
            # Validate bbox
            if len(bbox) != 4:
                logger.error(f"❌ Invalid bbox format: {bbox} (expected 4 values)")
                return None
            
            x1, y1, x2, y2 = bbox
            if x1 >= x2 or y1 >= y2:
                logger.error(f"❌ Invalid bbox coordinates: {bbox} (x1<x2 and y1<y2 required)")
                return None
            
            # Load and crop face
            logger.debug(f"📸 Extracting face from image using bbox {bbox}")
            face_image = self._extract_face_from_image(image_path, bbox)
            if face_image is None:
                logger.error(f"❌ Failed to extract face from image: {image_path}")
                return None
            
            logger.info(f"✅ Face extracted successfully: size={face_image.size}")
            
            # Preprocess face for Facenet
            logger.debug("🔧 Preprocessing face for Facenet model")
            face_tensor = self._preprocess_face(face_image)
            if face_tensor is None:
                logger.error("❌ Failed to preprocess face for Facenet")
                return None
            
            logger.info(f"✅ Face preprocessed: tensor shape={face_tensor.shape}, dtype={face_tensor.dtype}")
            
            # Generate embedding
            logger.debug("🧠 Generating embedding using Facenet model")
            with torch.no_grad():
                embedding = self.model(face_tensor.unsqueeze(0).to(self.device))
                embedding = embedding.squeeze(0).cpu().numpy()
                
                # Normalize embedding
                embedding = embedding / np.linalg.norm(embedding)
                
                logger.info(f"🎯 Embedding generated successfully!")
                logger.info(f"  Shape: {embedding.shape}")
                logger.info(f"  Norm: {np.linalg.norm(embedding):.6f}")
                logger.info(f"  Sample values: {embedding[:5]}")
                
                return embedding
                
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            logger.error(f"  Image path: {image_path}")
            logger.error(f"  Bbox: {bbox}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return None
    
    def generate_embeddings_from_detections(self, detections: List[Dict]) -> Dict:
        """
        Generate embeddings for multiple face detections
        
        Args:
            detections: List of detection dictionaries with image_path and bbox
            
        Returns:
            Dictionary with embedding results
        """
        try:
            all_embeddings = []
            failed_detections = []
            
            for detection in detections:
                image_path = detection.get('image_path')
                bbox = detection.get('bbox')
                
                if not image_path or not bbox:
                    failed_detections.append({
                        'detection': detection,
                        'error': 'Missing image_path or bbox'
                    })
                    continue
                
                # Generate embedding
                embedding = self.generate_embedding_from_image(image_path, bbox)
                
                if embedding is not None:
                    embedding_data = {
                        'image_path': image_path,
                        'bbox': bbox,
                        'embedding': embedding.tolist(),
                        'embedding_dim': self.embedding_dim,
                        'confidence_score': detection.get('confidence_score', 0.0),
                        'face_area': detection.get('face_area', 0)
                    }
                    all_embeddings.append(embedding_data)
                else:
                    failed_detections.append({
                        'detection': detection,
                        'error': 'Failed to generate embedding'
                    })
            
            return {
                'success': True,
                'total_embeddings': len(all_embeddings),
                'embeddings': all_embeddings,
                'failed_detections': failed_detections,
                'message': f"Generated {len(all_embeddings)} embeddings from {len(detections)} detections"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': []
            }
    
    def generate_embedding_from_base64(self, base64_string: str, bbox: List[int]) -> Optional[np.ndarray]:
        """
        Generate embedding from base64 encoded image
        
        Args:
            base64_string: Base64 encoded image string
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Face embedding as numpy array or None if failed
        """
        try:
            # Convert base64 to image
            image = self._base64_to_image(base64_string)
            if image is None:
                return None
            
            # Crop face
            face_image = self._crop_face_from_array(image, bbox)
            if face_image is None:
                return None
            
            # Preprocess and generate embedding
            face_tensor = self._preprocess_face(face_image)
            if face_tensor is None:
                return None
            
            with torch.no_grad():
                embedding = self.model(face_tensor.unsqueeze(0).to(self.device))
                embedding = embedding.squeeze(0).cpu().numpy()
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
                
        except Exception as e:
            logger.error(f"Failed to generate embedding from base64: {e}")
            return None
    
    def verify_faces_with_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray, 
                                   threshold: float = 0.6) -> Dict:
        """
        Verify two faces using their embeddings
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Similarity threshold (0-1)
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2)
            similarity_percentage = similarity * 100
            
            # Determine if faces match
            faces_match = similarity >= threshold
            
            return {
                'success': True,
                'faces_match': faces_match,
                'similarity_score': round(similarity_percentage, 2),
                'threshold': threshold,
                'threshold_met': faces_match,
                'message': f"Faces {'match' if faces_match else 'do not match'} with {similarity_percentage:.2f}% similarity"
            }
            
        except Exception as e:
            logger.error(f"Face verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_face_from_image(self, image_path: str, bbox: List[int]) -> Optional[Image.Image]:
        """Extract face region from image using bounding box"""
        try:
            logger.debug(f"📁 Checking if image exists: {image_path}")
            # Load image
            if not os.path.exists(image_path):
                logger.error(f"❌ Image file not found: {image_path}")
                return None
            
            logger.debug(f"📸 Reading image with OpenCV")
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"❌ Failed to read image with OpenCV: {image_path}")
                return None
            
            logger.info(f"✅ Image loaded successfully: shape={image.shape}, dtype={image.dtype}")
            
            # Validate bbox coordinates
            x1, y1, x2, y2 = bbox
            img_height, img_width = image.shape[:2]
            
            logger.debug(f"🔍 Image dimensions: {img_width}x{img_height}")
            logger.debug(f"🔍 Bbox coordinates: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            
            # Check if bbox is within image bounds
            if x1 < 0 or y1 < 0 or x2 > img_width or y2 > img_height:
                logger.warning(f"⚠️ Bbox extends beyond image bounds, clamping coordinates")
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(img_width, x2)
                y2 = min(img_height, y2)
                logger.debug(f"🔍 Clamped bbox: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            
            # Ensure minimum face size
            face_width = x2 - x1
            face_height = y2 - y1
            if face_width < 20 or face_height < 20:
                logger.error(f"❌ Face too small: {face_width}x{face_height} (minimum 20x20)")
                raise ValueError(f"Face too small: {face_width}x{face_height} pixels (minimum 20x20). Please use higher resolution images with larger faces.")
            
            logger.debug(f"✂️ Cropping face region: {face_width}x{face_height}")
            # Crop face region
            face_region = image[y1:y2, x1:x2]
            
            if face_region.size == 0:
                logger.error(f"❌ Cropped face region is empty")
                raise ValueError("Failed to crop face region from image. The detected face coordinates may be invalid.")
            
            logger.info(f"✅ Face region cropped: shape={face_region.shape}")
            
            # Convert BGR to RGB
            face_region_rgb = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            face_image = Image.fromarray(face_region_rgb)
            
            logger.info(f"✅ Face image created: size={face_image.size}, mode={face_image.mode}")
            return face_image
            
        except Exception as e:
            logger.error(f"❌ Failed to extract face from image: {e}")
            logger.error(f"  Image path: {image_path}")
            logger.error(f"  Bbox: {bbox}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            
            # Re-raise with more context for better error handling
            if "Face too small" in str(e):
                raise e  # Re-raise the specific error we created
            else:
                raise ValueError(f"Failed to extract face from image: {str(e)}. Please ensure the image contains a clear, well-lit face.")
    
    def _crop_face_from_array(self, image_array: np.ndarray, bbox: List[int]) -> Optional[Image.Image]:
        """Crop face from numpy array using bounding box"""
        try:
            x1, y1, x2, y2 = bbox
            face_region = image_array[y1:y2, x1:x2]
            
            # Convert to PIL Image
            face_image = Image.fromarray(face_region)
            
            return face_image
            
        except Exception as e:
            logger.error(f"Failed to crop face from array: {e}")
            return None
    
    def _preprocess_face(self, face_image: Image.Image) -> Optional[torch.Tensor]:
        """Preprocess face image for Facenet model"""
        try:
            logger.debug(f"🔄 Starting face preprocessing")
            logger.debug(f"  Input image: size={face_image.size}, mode={face_image.mode}")
            
            # Resize to required dimensions
            logger.debug(f"📏 Resizing image to {self.face_size}")
            face_image = face_image.resize(self.face_size)
            logger.debug(f"✅ Image resized to {face_image.size}")

            # Convert to numpy array
            logger.debug("🔄 Converting PIL image to numpy array")
            face_array = np.array(face_image, dtype=np.float32)
            logger.debug(f"✅ Numpy array created: shape={face_array.shape}, dtype={face_array.dtype}")

            # Normalize using Facenet statistics
            logger.debug(f"🔧 Normalizing with mean={self.mean}, std={self.std}")
            face_array = (face_array - self.mean) / self.std
            logger.debug(f"✅ Normalization completed: min={face_array.min():.3f}, max={face_array.max():.3f}")

            # Convert to tensor and add batch dimension
            logger.debug("🔄 Converting numpy array to PyTorch tensor")
            face_tensor = torch.from_numpy(face_array).permute(2, 0, 1)  # HWC to CHW
            logger.debug(f"✅ Tensor created: shape={face_tensor.shape}, dtype={face_tensor.dtype}")
            
            # Ensure tensor is float32 (not double)
            if face_tensor.dtype != torch.float32:
                logger.debug(f"🔄 Converting tensor from {face_tensor.dtype} to float32")
                face_tensor = face_tensor.float()
                logger.debug(f"✅ Tensor dtype converted to {face_tensor.dtype}")

            logger.info(f"✅ Face preprocessing completed successfully!")
            logger.info(f"  Final tensor: shape={face_tensor.shape}, dtype={face_tensor.dtype}")
            logger.info(f"  Tensor range: min={face_tensor.min():.3f}, max={face_tensor.max():.3f}")

            return face_tensor

        except Exception as e:
            logger.error(f"❌ Failed to preprocess face: {e}")
            logger.error(f"  Input image: size={face_image.size}, mode={face_image.mode}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return None
    
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
            
            return image_array
            
        except Exception as e:
            logger.error(f"Failed to convert base64 to image: {e}")
            return None
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            'model_name': 'Facenet InceptionResnetV1',
            'embedding_dimension': self.embedding_dim,
            'face_size': self.face_size,
            'device': str(self.device),
            'normalization': {
                'mean': self.mean.tolist(),
                'std': self.std.tolist()
            }
        }
