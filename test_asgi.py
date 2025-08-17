#!/usr/bin/env python3
"""
Test script for ASGI setup and parallel processing.

This script tests the ASGI application and face-ai parallel processing capabilities.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

def test_asgi_import():
    """Test if ASGI application can be imported"""
    try:
        from backend.asgi import application
        print("✅ ASGI application imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import ASGI application: {e}")
        return False

def test_face_ai_async_import():
    """Test if face-ai async views can be imported"""
    try:
        from face_ai import async_views
        print("✅ Face AI async views imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Face AI async views: {e}")
        return False

def test_async_services():
    """Test if async services can be imported"""
    try:
        from face_ai.services.async_face_detection import AsyncFaceDetectionService
        from face_ai.services.async_milvus_service import AsyncMilvusService
        print("✅ Async services imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import async services: {e}")
        return False

async def test_parallel_processing():
    """Test parallel processing capabilities"""
    try:
        from face_ai.services.async_face_detection import AsyncFaceDetectionService
        
        # Initialize service
        service = AsyncFaceDetectionService(max_workers=4)
        print(f"✅ AsyncFaceDetectionService initialized with {service.max_workers} workers")
        
        # Test batch processing
        test_image_paths = [
            "/path/to/test1.jpg",
            "/path/to/test2.jpg",
            "/path/to/test3.jpg"
        ]
        
        print("🔄 Testing batch face detection...")
        start_time = time.time()
        
        # This would normally process real images
        result = await service.batch_detect_faces(test_image_paths, max_workers=2)
        
        processing_time = time.time() - start_time
        print(f"✅ Batch processing test completed in {processing_time:.2f}s")
        print(f"   Result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Parallel processing test failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    try:
        from face_ai.asgi_config import get_config, get_parallel_config
        
        config = get_config()
        parallel_config = get_parallel_config()
        
        print("✅ Configuration loaded successfully")
        print(f"   Parallel workers: {parallel_config['MAX_WORKERS']}")
        print(f"   Batch size: {parallel_config['BATCH_SIZE']}")
        print(f"   Thread pool size: {parallel_config['THREAD_POOL_SIZE']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Testing ASGI Setup and Parallel Processing")
    print("=" * 50)
    
    tests = [
        ("ASGI Import", test_asgi_import),
        ("Face AI Async Import", test_face_ai_async_import),
        ("Async Services", test_async_services),
        ("Configuration", test_configuration),
        ("Parallel Processing", test_parallel_processing),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ASGI setup is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
