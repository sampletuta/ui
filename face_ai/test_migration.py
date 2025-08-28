#!/usr/bin/env python3
"""
Test script to verify the migration from InsightFace to OpenCV Yunet + Facenet
This script tests the new face detection and embedding services
"""

import os
import sys
import logging
import tempfile
import numpy as np
from PIL import Image, ImageDraw
import cv2

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_image(width=640, height=480, faces=1):
    """Create a test image with synthetic faces"""
    try:
        # Create a blank image
        image = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(image)
        
        # Add some synthetic faces (simple colored rectangles)
        face_size = 100
        for i in range(faces):
            x = 100 + i * 150
            y = 150
            # Face rectangle
            draw.rectangle([x, y, x + face_size, y + face_size], fill='peachpuff', outline='black', width=2)
            # Eyes
            draw.ellipse([x + 20, y + 30, x + 40, y + 50], fill='white', outline='black')
            draw.ellipse([x + 60, y + 30, x + 80, y + 50], fill='white', outline='black')
            # Nose
            draw.rectangle([x + 45, y + 55, x + 55, y + 75], fill='pink', outline='black')
            # Mouth
            draw.arc([x + 25, y + 80, x + 75, y + 100], start=0, end=180, fill='red', width=3)
        
        return image
        
    except Exception as e:
        logger.error(f"Failed to create test image: {e}")
        return None

def test_face_detection_service():
    """Test the new OpenCV Yunet face detection service"""
    logger.info("Testing OpenCV Yunet Face Detection Service...")
    
    try:
        from services.face_detection import FaceDetectionService
        
        # Initialize service
        detection_service = FaceDetectionService(confidence_threshold=0.3)
        logger.info("✓ Face Detection Service initialized successfully")
        
        # Create test image
        test_image = create_test_image(faces=2)
        if test_image is None:
            logger.error("✗ Failed to create test image")
            return False
        
        # Save test image temporarily
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            test_image.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Test face detection
            detection_result = detection_service.detect_faces_in_image(temp_path)
            
            if detection_result['success']:
                logger.info(f"✓ Face detection successful: {detection_result['faces_detected']} faces detected")
                logger.info(f"  Detection details: {detection_result['faces']}")
                return True
            else:
                logger.error(f"✗ Face detection failed: {detection_result.get('error', 'Unknown error')}")
                return False
                
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"✗ Face Detection Service test failed: {e}")
        return False

def test_face_embedding_service():
    """Test the new Facenet embedding service"""
    logger.info("Testing Facenet Face Embedding Service...")
    
    try:
        from services.face_embedding_service import FaceEmbeddingService
        
        # Initialize service
        embedding_service = FaceEmbeddingService()
        logger.info("✓ Face Embedding Service initialized successfully")
        
        # Create test image with face
        test_image = create_test_image(faces=1)
        if test_image is None:
            logger.error("✗ Failed to create test image")
            return False
        
        # Save test image temporarily
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            test_image.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Define a face bounding box (approximate location of synthetic face)
            bbox = [100, 150, 200, 250]  # [x1, y1, x2, y2]
            
            # Test embedding generation
            embedding = embedding_service.generate_embedding_from_image(temp_path, bbox)
            
            if embedding is not None:
                logger.info(f"✓ Face embedding generated successfully")
                logger.info(f"  Embedding shape: {embedding.shape}")
                logger.info(f"  Embedding norm: {np.linalg.norm(embedding):.4f}")
                logger.info(f"  Embedding sample: {embedding[:5]}")
                return True
            else:
                logger.error("✗ Face embedding generation failed")
                return False
                
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"✗ Face Embedding Service test failed: {e}")
        return False

def test_face_search_service():
    """Test the integrated face search service"""
    logger.info("Testing Integrated Face Search Service...")
    
    try:
        from services.face_search_service import FaceSearchService
        
        # Initialize service
        search_service = FaceSearchService()
        logger.info("✓ Face Search Service initialized successfully")
        
        # Get service info
        service_info = search_service.get_service_info()
        logger.info(f"✓ Service info retrieved: {service_info['status']}")
        
        # Test service components
        detection_info = service_info.get('detection_model', {})
        embedding_info = service_info.get('embedding_model', {})
        
        logger.info(f"  Detection model: {detection_info.get('model_name', 'Unknown')}")
        logger.info(f"  Embedding model: {embedding_info.get('model_name', 'Unknown')}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Face Search Service test failed: {e}")
        return False

def test_async_face_detection():
    """Test the async face detection service"""
    logger.info("Testing Async Face Detection Service...")
    
    try:
        import asyncio
        from services.async_face_detection import AsyncFaceDetectionService
        
        # Initialize service
        async_service = AsyncFaceDetectionService(max_workers=2)
        logger.info("✓ Async Face Detection Service initialized successfully")
        
        # Create test image
        test_image = create_test_image(faces=1)
        if test_image is None:
            logger.error("✗ Failed to create test image")
            return False
        
        # Save test image temporarily
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            test_image.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Test async face detection
            async def test_async_detection():
                result = await async_service.detect_faces_in_image_async(temp_path)
                return result
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(test_async_detection())
            loop.close()
            
            if result['success']:
                logger.info(f"✓ Async face detection successful: {result['faces_detected']} faces detected")
                return True
            else:
                logger.error(f"✗ Async face detection failed: {result.get('error', 'Unknown error')}")
                return False
                
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            # Cleanup async service
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_service.cleanup())
                loop.close()
            except:
                pass
                
    except Exception as e:
        logger.error(f"✗ Async Face Detection Service test failed: {e}")
        return False

def test_model_download():
    """Test Yunet model availability"""
    logger.info("Testing Yunet Model Availability...")
    
    try:
        # Check for user-provided model first
        user_model = os.path.join(os.path.dirname(__file__), 'face_detection_yunet_2023mar.onnx')
        if os.path.exists(user_model):
            file_size = os.path.getsize(user_model)
            logger.info(f"✓ Found user-provided Yunet model")
            logger.info(f"  Model path: {user_model}")
            logger.info(f"  Model size: {file_size / 1024 / 1024:.2f} MB")
            return True
        
        # Check models directory
        model_dir = os.path.join(os.path.dirname(__file__), 'services', 'models')
        model_path = os.path.join(model_dir, 'yunet_n_120_160.onnx')
        
        if os.path.exists(model_path):
            file_size = os.path.getsize(model_path)
            logger.info(f"✓ Found Yunet model in models directory")
            logger.info(f"  Model path: {model_path}")
            logger.info(f"  Model size: {file_size / 1024 / 1024:.2f} MB")
            return True
        
        logger.error("✗ No Yunet model found")
        return False
            
    except Exception as e:
        logger.error(f"✗ Model availability test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Starting Migration Test Suite")
    logger.info("Testing OpenCV Yunet + Facenet Implementation")
    logger.info("=" * 60)
    
    tests = [
        ("Model Download", test_model_download),
        ("Face Detection Service", test_face_detection_service),
        ("Face Embedding Service", test_face_embedding_service),
        ("Face Search Service", test_face_search_service),
        ("Async Face Detection", test_async_face_detection),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status} - {test_name}")
        if success:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Migration successful!")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
