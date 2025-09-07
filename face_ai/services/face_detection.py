import logging
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from PIL import Image
import os
import base64
import io
from pathlib import Path

logger = logging.getLogger(__name__)

class FaceDetectionService:
    """
    Professional face detection service using OpenCV FaceDetectorYN (YuNet) model.
    
    This service provides robust face detection capabilities with proper error handling,
    input validation, and consistent return formats.
    """
    
    # YuNet model output format constants
    YUNET_BBOX_X = 0
    YUNET_BBOX_Y = 1
    YUNET_BBOX_W = 2
    YUNET_BBOX_H = 3
    YUNET_RIGHT_EYE_X = 4
    YUNET_RIGHT_EYE_Y = 5
    YUNET_LEFT_EYE_X = 6
    YUNET_LEFT_EYE_Y = 7
    YUNET_NOSE_X = 8
    YUNET_NOSE_Y = 9
    YUNET_RIGHT_MOUTH_X = 10
    YUNET_RIGHT_MOUTH_Y = 11
    YUNET_LEFT_MOUTH_X = 12
    YUNET_LEFT_MOUTH_Y = 13
    YUNET_SCORE = 14
    
    def __init__(self, confidence_threshold: float = 0.5, min_face_size: int = 20):
        """
        Initialize the face detection service.
        
        Args:
            confidence_threshold: Minimum confidence score for face detection (0.0-1.0)
            min_face_size: Minimum face size in pixels
            
        Raises:
            FileNotFoundError: If the model file cannot be found
            RuntimeError: If model initialization fails
        """
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        
        if min_face_size <= 0:
            raise ValueError("min_face_size must be positive")
        
        self.confidence_threshold = confidence_threshold
        self.min_face_size = min_face_size
        
        # Model path resolution
        model_path = self._resolve_model_path()
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Yunet model file not found: {model_path}")
        
        try:
            # Initialize FaceDetectorYN with proper parameters based on libfacedetection reference
            # The key is to use appropriate input size and confidence threshold
            self.yunet_model = cv2.FaceDetectorYN.create(
                model_path,
                "",
                (1280, 1280),  # Standard input size that works well with YuNet
                0.5,          # Lower confidence threshold to catch more faces
                0.3,          # NMS threshold
                5000          # Maximum faces to detect
            )
            
            logger.info(f"Face detection service initialized successfully with model: {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize FaceDetectorYN model: {e}")
            raise RuntimeError(f"Model initialization failed: {e}")
    
    def _resolve_model_path(self) -> str:
        """Resolve the path to the Yunet model file."""
        # Try multiple possible locations, preferring non-quantized version for compatibility
        possible_paths = [
            # Parent face_ai directory (non-quantized version - preferred for compatibility)
            os.path.join(os.path.dirname(__file__), "..", "face_detection_yunet_2023mar.onnx"),
            # Current services directory (quantized version - fallback)
            os.path.join(os.path.dirname(__file__), "face_detection_yunet_2023mar_int8bq.onnx"),
            # Absolute path from workspace root (non-quantized)
            os.path.join("/home/user/Desktop/ui/face_ai", "face_detection_yunet_2023mar.onnx"),
            # Absolute path from workspace root (quantized)
            os.path.join("/home/user/Desktop/ui", "face_detection_yunet_2023mar_int8bq.onnx"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Yunet model at: {path}")
                return os.path.abspath(path)
        
        # If none found, log the attempted paths and return the first expected path
        logger.error(f"Yunet model not found in any of these paths: {possible_paths}")
        return possible_paths[0]
    
    def _set_input_size(self, width: int, height: int) -> None:
        """
        Set the input size for the face detection model.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        try:
            self.yunet_model.setInputSize((int(width), int(height)))
            logger.debug(f"Model input size set to {width}x{height}")
        except Exception as e:
            logger.warning(f"Failed to set model input size to {width}x{height}: {e}")
            # Fallback to default size
            try:
                self.yunet_model.setInputSize((320, 320))
                logger.debug("Model input size set to default 320x320")
            except Exception as fallback_e:
                logger.error(f"Failed to set default input size: {fallback_e}")
    
    def _validate_image(self, image: np.ndarray) -> bool:
        """
        Validate that an image is suitable for face detection.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            True if image is valid, False otherwise
        """
        if image is None:
            return False
        
        if len(image.shape) < 2 or len(image.shape) > 3:
            return False
        
        if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            return False
        
        return True
    
    def _ensure_bgr_u8(self, image: np.ndarray) -> np.ndarray:
        """Ensure image is 3-channel BGR with uint8 dtype and contiguous memory, without resizing."""
        try:
            img = image
            if img.dtype != np.uint8:
                # Assume [0,1] floats -> scale to [0,255]
                if np.issubdtype(img.dtype, np.floating):
                    img = np.clip(img * 255.0, 0, 255).astype(np.uint8)
                else:
                    img = img.astype(np.uint8)
            # Handle color channels
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif len(img.shape) == 3:
                if img.shape[2] == 4:
                    # Assume BGRA; if source was PIL RGBA we convert there, but handle here too
                    try:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    except Exception:
                        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif img.shape[2] == 3:
                    # Assume already BGR for cv2.imread; if came from PIL we convert earlier
                    pass
                else:
                    # Unexpected channels, force BGR by dropping extras
                    img = img[:, :, :3]
            # Ensure contiguous
            if not img.flags['C_CONTIGUOUS']:
                img = np.ascontiguousarray(img)
            return img
        except Exception:
            return np.ascontiguousarray(image)
    
    def _process_detection_result(self, detection_result: Tuple, image_shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process the raw detection result from the model.

        Args:
            detection_result: Raw detection result from FaceDetectorYN.detect()
            image_shape: Shape of the input image (height, width)

        Returns:
            Tuple of (faces_array, confidences_array)
        """
        # OpenCV YuNet detect() returns either:
        # - (faces, confidences) in some builds, or
        # - faces only (Nx15) in others (scores are faces[:, 14]).
        faces: Optional[np.ndarray] = None
        confidences: Optional[np.ndarray] = None
        try:
            if isinstance(detection_result, tuple):
                if len(detection_result) == 2:
                    faces, confidences = detection_result
                    # Handle case where faces is returned as int (bug in some OpenCV builds)
                    if isinstance(faces, (int, np.integer)) and confidences is not None:
                        # If faces is an int but confidences looks like face data (shape ends with 15)
                        if hasattr(confidences, 'shape') and len(confidences.shape) >= 2 and confidences.shape[-1] == 15:
                            logger.debug("Detected OpenCV bug: faces returned as int, using confidences as faces data")
                            faces = confidences
                            confidences = None
                        elif isinstance(faces, (int, np.integer)) and faces == 0:
                            # faces is 0, meaning no faces detected
                            logger.debug("No faces detected (faces=0)")
                            faces = np.array([])
                        else:
                            logger.warning(f"Unexpected detection result format: faces={type(faces)} value={faces}, confidences shape={confidences.shape if hasattr(confidences, 'shape') else 'no shape'}")
                            faces = None
                    elif not isinstance(faces, np.ndarray) and hasattr(faces, '__len__') and len(faces) == 0:
                        # Empty faces array
                        faces = np.array([])
                elif len(detection_result) == 1:
                    faces = detection_result[0]
                else:
                    # Unexpected tuple shape
                    faces = None
            else:
                # Some OpenCV versions return a single ndarray
                faces = detection_result
        except Exception as e:
            logger.error(f"Failed to parse detection result: {e}")
            return np.array([]), np.array([])
        
        # Handle case where no faces are detected
        if faces is None or (hasattr(faces, '__len__') and len(faces) == 0):
            logger.debug("No faces detected")
            return np.array([]), np.array([])
        
        # Convert to numpy arrays if needed
        if not isinstance(faces, np.ndarray):
            faces = np.array(faces)
        if confidences is not None and not isinstance(confidences, np.ndarray):
            confidences = np.array(confidences)
        
        # Handle empty arrays
        if faces.size == 0:
            return np.array([]), np.array([])
        
        # Ensure faces is 2D array
        if len(faces.shape) == 1:
            if len(faces) >= 15:
                faces = faces.reshape(1, -1)
            else:
                logger.warning(f"Invalid 1D faces array length: {len(faces)}")
                return np.array([]), np.array([])
        
        # Validate shape
        if len(faces.shape) != 2 or faces.shape[1] < 15:
            logger.warning(f"Invalid faces array shape: {faces.shape}")
            return np.array([]), np.array([])
        
        # Handle confidences
        if confidences is None or (hasattr(confidences, "size") and confidences.size == 0):
            # Try to extract score from the last column of faces (index 14)
            try:
                confidences = faces[:, self.YUNET_SCORE]
            except Exception:
                confidences = np.ones(faces.shape[0])
        elif confidences.shape[0] != faces.shape[0]:
            confidences = np.ones(faces.shape[0])
        
        logger.debug(f"Processed detection: {faces.shape[0]} faces")
        return faces, confidences
    
    def _extract_face_info(self, face_data: np.ndarray, confidence: float, image_shape: Tuple[int, int]) -> Optional[Dict]:
        """
        Extract face information from detection data.
        
        Args:
            face_data: Raw face detection data from model
            confidence: Confidence score for the detection
            image_shape: Shape of the input image (height, width)
            
        Returns:
            Dictionary with face information or None if face should be filtered out
        """
        try:
            # Debug: Check face_data structure
            logger.debug(f"Extracting face info from data shape: {face_data.shape if hasattr(face_data, 'shape') else 'no shape'}")
            logger.debug(f"Face data type: {type(face_data)}")
            if hasattr(face_data, 'shape'):
                logger.debug(f"Face data: {face_data}")

            # Extract bounding box coordinates
            x = int(face_data[self.YUNET_BBOX_X])
            y = int(face_data[self.YUNET_BBOX_Y])
            w = int(face_data[self.YUNET_BBOX_W])
            h = int(face_data[self.YUNET_BBOX_H])
            
            # Validate face size
            if w < self.min_face_size or h < self.min_face_size:
                logger.debug(f"Face filtered out due to small size: {w}x{h} < {self.min_face_size}")
                return None
            
            # Validate confidence
            if confidence < self.confidence_threshold:
                logger.debug(f"Face filtered out due to low confidence: {confidence:.3f} < {self.confidence_threshold}")
                return None
            
            # Clamp bounding box within image bounds (do not discard partially out-of-bounds boxes)
            logger.debug(f"Image shape: {image_shape}")
            height, width = image_shape
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(width, x + w)
            y2 = min(height, y + h)
            # Ensure valid box after clamping
            if x2 <= x1 or y2 <= y1:
                logger.debug(f"Clamped bbox invalid, skipping: original [{x}, {y}, {w}, {h}], clamped [{x1}, {y1}, {x2}, {y2}] vs image {width}x{height}")
                return None
            
            # Extract landmarks
            landmarks = []
            if len(face_data) >= 15:
                landmarks = [
                    [int(face_data[self.YUNET_RIGHT_EYE_X]), int(face_data[self.YUNET_RIGHT_EYE_Y])],
                    [int(face_data[self.YUNET_LEFT_EYE_X]), int(face_data[self.YUNET_LEFT_EYE_Y])],
                    [int(face_data[self.YUNET_NOSE_X]), int(face_data[self.YUNET_NOSE_Y])],
                    [int(face_data[self.YUNET_RIGHT_MOUTH_X]), int(face_data[self.YUNET_RIGHT_MOUTH_Y])],
                    [int(face_data[self.YUNET_LEFT_MOUTH_X]), int(face_data[self.YUNET_LEFT_MOUTH_Y])]
                ]
            
            return {
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence,
                'landmarks': landmarks,
                'face_area': w * h,
                'face_width': w,
                'face_height': h,
                'center_x': x + w // 2,
                'center_y': y + h // 2
            }
            
        except (IndexError, ValueError, TypeError) as e:
            logger.warning(f"Failed to extract face information: {e}")
            return None
    
    def detect_faces_in_image(self, image_path: Union[str, Path]) -> Dict:
        """
        Detect faces in an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with detection results containing:
                - success: Boolean indicating if detection was successful
                - faces_detected: Number of faces detected
                - faces: List of detected face information
                - error: Error message if detection failed
                - message: Success message if detection succeeded
        """
        try:
            # Validate input
            if not image_path or not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Load image
            img = cv2.imread(str(image_path))
            if not self._validate_image(img):
                return {
                    'success': False,
                    'error': f'Failed to load or invalid image: {image_path}',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Ensure correct format (no resizing, preserve aspect ratio)
            img = self._ensure_bgr_u8(img)
            
            # Set model input size to exact image size
            height, width = img.shape[:2]
            self._set_input_size(width, height)
            
            logger.debug(f"Processing image {image_path} with shape {img.shape}")

            # Perform face detection
            __, detection_result = self.yunet_model.detect(img)
            logger.debug(f"Raw detection result type: {type(detection_result)}")
            if isinstance(detection_result, tuple):
                logger.debug(f"Detection result tuple length: {len(detection_result)}")
                for i, item in enumerate(detection_result):
                    logger.debug(f"  Item {i}: type={type(item)}, value={item}")

            result = self._process_detection_result(detection_result, (height, width))
            logger.debug(f"Process result type: {type(result)}, length: {len(result) if hasattr(result, '__len__') else 'N/A'}")
            faces, confidences = result
            
            if len(faces) == 0:
                logger.info(f"No faces detected in image: {image_path}")
                return {
                    'success': True,
                    'faces_detected': 0,
                    'faces': [],
                    'message': 'No faces detected in the image'
                }
            
            # Process detected faces
            processed_faces = []
            for i in range(len(faces)):
                try:
                    face_data = faces[i]
                    confidence = confidences[i] if i < len(confidences) else 0.8
                    
                    face_info = self._extract_face_info(face_data, confidence, (height, width))
                    if face_info:
                        processed_faces.append(face_info)
                        logger.debug(f"Face {i+1}: bbox={face_info['bbox']}, confidence={face_info['confidence']:.3f}")
                except Exception as e:
                    logger.warning(f"Failed to process face {i+1}: {e}")
                    continue
            
            logger.info(f"Successfully detected {len(processed_faces)} faces in {image_path}")
            
            return {
                'success': True,
                'faces_detected': len(processed_faces),
                'faces': processed_faces,
                'message': f'Successfully detected {len(processed_faces)} faces'
            }
            
        except Exception as e:
            logger.error(f"Face detection failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }
    
    def detect_faces_in_image_base64(self, base64_string: str) -> Dict:
        """
        Detect faces in a base64 encoded image.
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Validate input
            if not base64_string or not isinstance(base64_string, str):
                return {
                    'success': False,
                    'error': 'Invalid base64 string provided',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Convert base64 to image
            img = self._base64_to_image(base64_string)
            if not self._validate_image(img):
                return {
                    'success': False,
                    'error': 'Failed to decode base64 image or invalid image data',
                    'faces_detected': 0,
                    'faces': []
                }
            
            # Ensure correct format (no resizing, preserve aspect ratio)
            img = self._ensure_bgr_u8(img)
            
            # Set model input size to exact image size
            height, width = img.shape[:2]
            self._set_input_size(width, height)
            
            logger.debug(f"Processing base64 image with shape {img.shape}")
            
            # Perform face detection
            detection_result = self.yunet_model.detect(img)
            height, width = img.shape[:2]
            faces, confidences = self._process_detection_result(detection_result, (height, width))
            
            if len(faces) == 0:
                logger.info("No faces detected in base64 image")
                return {
                    'success': True,
                    'faces_detected': 0,
                    'faces': [],
                    'message': 'No faces detected in the image'
                }
            
            # Process detected faces
            processed_faces = []
            for i in range(len(faces)):
                try:
                    face_data = faces[i]
                    confidence = confidences[i] if i < len(confidences) else 0.8
                    
                    face_info = self._extract_face_info(face_data, confidence, (height, width))
                    if face_info:
                        processed_faces.append(face_info)
                        logger.debug(f"Face {i+1}: bbox={face_info['bbox']}, confidence={face_info['confidence']:.3f}")
                except Exception as e:
                    logger.warning(f"Failed to process face {i+1}: {e}")
                    continue
            
            logger.info(f"Successfully detected {len(processed_faces)} faces in base64 image")
            
            return {
                'success': True,
                'faces_detected': len(processed_faces),
                'faces': processed_faces,
                'message': f'Successfully detected {len(processed_faces)} faces'
            }
            
        except Exception as e:
            logger.error(f"Base64 face detection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'faces': []
            }
    
    def detect_faces_in_images(self, image_paths: List[Union[str, Path]]) -> Dict:
        """
        Detect faces in multiple images.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            Dictionary with detection results for all images
        """
        if not image_paths:
            return {
                'success': False,
                'error': 'No image paths provided',
                'total_detections': 0,
                'detections': [],
                'failed_images': []
            }
        
        all_detections = []
        failed_images = []
        
        for image_path in image_paths:
            detection_result = self.detect_faces_in_image(image_path)
            
            if not detection_result['success']:
                failed_images.append({
                    'image_path': str(image_path),
                    'error': detection_result['error']
                })
                continue
            
            if detection_result['faces_detected'] > 0:
                for face in detection_result['faces']:
                    detection_data = {
                        'image_path': str(image_path),
                        'bbox': face['bbox'],
                        'confidence': face['confidence'],
                        'face_area': face['face_area'],
                        'landmarks': face['landmarks']
                    }
                    all_detections.append(detection_data)
        
        return {
            'success': True,
            'total_detections': len(all_detections),
            'detections': all_detections,
            'failed_images': failed_images,
            'message': f"Processed {len(image_paths)} images, detected {len(all_detections)} faces"
        }

    def detect_and_generate_embeddings(self, image_path: Union[str, Path], max_faces: int = 1) -> Dict:
        """
        Detect faces in a single image and generate embeddings for up to max_faces.
        Returns a dictionary with embeddings and associated metadata.
        """
        try:
            detection = self.detect_faces_in_image(image_path)
            if not detection.get('success'):
                return {
                    'success': False,
                    'error': detection.get('error', 'Face detection failed'),
                    'embeddings': []
                }

            if detection.get('faces_detected', 0) == 0:
                return {
                    'success': True,
                    'embeddings': [],
                    'message': 'No faces detected'
                }

            # Prepare detections for embedding service
            detections: List[Dict] = []
            for face in detection['faces'][: max(1, int(max_faces))]:
                detections.append({
                    'image_path': str(image_path),
                    'bbox': face['bbox'],
                    'confidence_score': float(face.get('confidence', 0.0)),
                    'face_area': int(face.get('face_area', 0))
                })

            # Lazy import to avoid circular import at module import time
            from .face_embedding_service import FaceEmbeddingService
            embedding_service = FaceEmbeddingService()
            embedding_result = embedding_service.generate_embeddings_from_detections(detections)

            return embedding_result

        except Exception as e:
            logger.error(f"detect_and_generate_embeddings failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': []
            }

    def detect_and_generate_embeddings_base64(self, base64_string: str, max_faces: int = 1) -> Dict:
        """
        Detect faces in a base64 image and generate embeddings for up to max_faces directly from base64.
        """
        try:
            detection = self.detect_faces_in_image_base64(base64_string)
            if not detection.get('success'):
                return {
                    'success': False,
                    'error': detection.get('error', 'Face detection failed'),
                    'embeddings': []
                }

            if detection.get('faces_detected', 0) == 0:
                return {
                    'success': True,
                    'embeddings': [],
                    'message': 'No faces detected'
                }

            # Generate embeddings using base64-capable path for each face
            from .face_embedding_service import FaceEmbeddingService
            embedding_service = FaceEmbeddingService()

            all_embeddings: List[Dict] = []
            failed: List[Dict] = []
            for face in detection['faces'][: max(1, int(max_faces))]:
                bbox = face['bbox']
                try:
                    emb = embedding_service.generate_embedding_from_base64(base64_string, bbox)
                    if emb is None:
                        failed.append({'bbox': bbox, 'error': 'Embedding generation failed'})
                        continue
                    all_embeddings.append({
                        'bbox': bbox,
                        'embedding': emb.tolist(),
                        'embedding_dim': getattr(embedding_service, 'embedding_dim', 512),
                        'confidence_score': float(face.get('confidence', 0.0)),
                        'face_area': int(face.get('face_area', 0))
                    })
                except Exception as e:
                    failed.append({'bbox': bbox, 'error': str(e)})

            return {
                'success': True,
                'total_embeddings': len(all_embeddings),
                'embeddings': all_embeddings,
                'failed_detections': failed,
                'message': f"Generated {len(all_embeddings)} embeddings from {detection.get('faces_detected', 0)} detections"
            }

        except Exception as e:
            logger.error(f"detect_and_generate_embeddings_base64 failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'embeddings': []
            }
    
    def generate_face_embeddings(self, image_paths: List[Union[str, Path]]) -> Dict:
        """
        Legacy method for backward compatibility.
        This method only performs face detection - embeddings should be generated 
        using the FaceEmbeddingService separately.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            Dictionary with detection results formatted for embedding generation
        """
        logger.warning("generate_face_embeddings is deprecated. Use detect_faces_in_images() and FaceEmbeddingService.generate_embeddings_from_detections() instead.")
        
        # Use the new detection method
        detection_result = self.detect_faces_in_images(image_paths)
        
        if not detection_result['success']:
            return {
                'success': False,
                'error': detection_result['error'],
                'embeddings': []
            }
        
        # Format results for backward compatibility
        embeddings_data = []
        for detection in detection_result['detections']:
            embeddings_data.append({
                'image_path': detection['image_path'],
                'bbox': detection['bbox'],
                'confidence_score': detection['confidence'],
                'face_area': detection['face_area'],
                # Note: No actual embedding - this needs to be generated by FaceEmbeddingService
                'embedding': None  # Placeholder - actual embedding generation happens elsewhere
            })
        
        return {
            'success': True,
            'total_detections': len(embeddings_data),
            'embeddings': embeddings_data,
            'failed_images': detection_result['failed_images'],
            'message': f"Face detection completed for {len(image_paths)} images. Use FaceEmbeddingService for actual embedding generation."
        }
    
    def verify_faces(self, image1_base64: str, image2_base64: str) -> Dict:
        """
        Verify that faces are present in two images (detection only).
        
        Args:
            image1_base64: Base64 encoded first image
            image2_base64: Base64 encoded second image
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Detect faces in both images
            result1 = self.detect_faces_in_image_base64(image1_base64)
            result2 = self.detect_faces_in_image_base64(image2_base64)
            
            if not result1['success'] or not result2['success']:
                return {
                    'success': False,
                    'error': f"Face detection failed: Image 1: {result1.get('error', 'Unknown')}, Image 2: {result2.get('error', 'Unknown')}"
                }
            
            if result1['faces_detected'] == 0 or result2['faces_detected'] == 0:
                return {
                    'success': False,
                    'error': f"No faces detected in one or both images: Image 1: {result1['faces_detected']}, Image 2: {result2['faces_detected']}"
                }
            
            # Get the first detected face from each image
            face1 = result1['faces'][0]
            face2 = result2['faces'][0]
            
            return {
                'success': True,
                'faces_detected': True,
                'face1': {
                    'bbox': face1['bbox'],
                    'confidence': face1['confidence'],
                    'landmarks': face1['landmarks']
                },
                'face2': {
                    'bbox': face2['bbox'],
                    'confidence': face2['confidence'],
                    'landmarks': face2['landmarks']
                },
                'message': 'Faces detected in both images (face verification requires embedding comparison)'
            }
            
        except Exception as e:
            logger.error(f"Face verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _base64_to_image(self, base64_string: str) -> Optional[np.ndarray]:
        """
        Convert base64 string to numpy image array.
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            Numpy array representation of the image or None if conversion fails
        """
        try:
            # Remove data URL prefix if present
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data)).convert('RGBA') if True else Image.open(io.BytesIO(image_data))
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Convert to BGR
            if len(image_array.shape) == 3 and image_array.shape[2] == 4:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2BGR)
            elif len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            elif len(image_array.shape) == 2:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
            
            return image_array
            
        except Exception as e:
            logger.error(f"Failed to convert base64 to image: {e}")
            return None
    
    def image_to_base64(self, image_field) -> str:
        """
        Convert Django ImageField to base64 string.
        
        Args:
            image_field: Django ImageField instance
            
        Returns:
            Base64 encoded string representation of the image
            
        Raises:
            ValueError: If the image field is invalid
            IOError: If the image cannot be read
        """
        try:
            if not image_field:
                raise ValueError("Image field is required")
            
            with image_field.open('rb') as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                return base64_string
                
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """
        Get information about the loaded face detection model.
        
        Returns:
            Dictionary containing model information
        """
        return {
            'model_name': 'OpenCV FaceDetectorYN (Yunet)',
            'model_version': '2023mar',
            'confidence_threshold': self.confidence_threshold,
            'min_face_size': self.min_face_size,
            'input_size': (320, 320),
            'max_faces': 5000
        }
    
    def update_confidence_threshold(self, new_threshold: float) -> bool:
        """
        Update the confidence threshold for face detection.
        
        Args:
            new_threshold: New confidence threshold (0.0-1.0)
            
        Returns:
            True if threshold was updated successfully, False otherwise
        """
        try:
            if not 0.0 <= new_threshold <= 1.0:
                logger.error(f"Invalid confidence threshold: {new_threshold}. Must be between 0.0 and 1.0")
                return False
            
            self.confidence_threshold = new_threshold
            logger.info(f"Confidence threshold updated to {new_threshold}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update confidence threshold: {e}")
            return False
    
    def update_min_face_size(self, new_size: int) -> bool:
        """
        Update the minimum face size for detection.
        
        Args:
            new_size: New minimum face size in pixels
            
        Returns:
            True if size was updated successfully, False otherwise
        """
        try:
            if new_size <= 0:
                logger.error(f"Invalid minimum face size: {new_size}. Must be positive")
                return False
            
            self.min_face_size = new_size
            logger.info(f"Minimum face size updated to {new_size} pixels")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update minimum face size: {e}")
            return False
