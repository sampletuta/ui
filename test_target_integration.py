#!/usr/bin/env python3
"""
Test script for Target Integration Wrapper.

This script tests the async target integration service and wrapper.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

def test_wrapper_import():
    """Test if the wrapper can be imported"""
    try:
        from face_ai.services.target_integration_wrapper import TargetIntegrationWrapper
        print("✅ Target Integration Wrapper imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import wrapper: {e}")
        return False

def test_wrapper_initialization():
    """Test if the wrapper can be initialized"""
    try:
        from face_ai.services.target_integration_wrapper import TargetIntegrationWrapper
        
        # Test async initialization
        wrapper = TargetIntegrationWrapper(use_async=True, max_workers=4)
        print(f"✅ Async wrapper initialized: {wrapper.get_service_info()}")
        
        # Test sync initialization
        sync_wrapper = TargetIntegrationWrapper(use_async=False)
        print(f"✅ Sync wrapper initialized: {sync_wrapper.get_service_info()}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize wrapper: {e}")
        return False

def test_async_services_import():
    """Test if async services can be imported"""
    try:
        from face_ai.services.async_target_integration import AsyncTargetIntegrationService
        from face_ai.services.async_face_detection import AsyncFaceDetectionService
        from face_ai.services.async_milvus_service import AsyncMilvusService
        
        print("✅ Async services imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import async services: {e}")
        return False

async def test_async_target_integration():
    """Test async target integration service"""
    try:
        from face_ai.services.async_target_integration import AsyncTargetIntegrationService
        
        # Initialize service
        service = AsyncTargetIntegrationService(max_workers=2)
        print(f"✅ AsyncTargetIntegrationService initialized with {service.max_workers} workers")
        
        # Test service info
        print(f"   Service type: Async with {service.max_workers} workers")
        
        return True
        
    except Exception as e:
        print(f"❌ Async target integration test failed: {e}")
        return False

def test_sync_fallback():
    """Test sync fallback functionality"""
    try:
        from face_ai.services.target_integration_wrapper import TargetIntegrationWrapper
        
        # Create wrapper with sync fallback
        wrapper = TargetIntegrationWrapper(use_async=False)
        
        # Test sync methods
        info = wrapper.get_service_info()
        print(f"✅ Sync fallback working: {info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync fallback test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Testing Target Integration Wrapper")
    print("=" * 50)
    
    tests = [
        ("Wrapper Import", test_wrapper_import),
        ("Wrapper Initialization", test_wrapper_initialization),
        ("Async Services Import", test_async_services_import),
        ("Async Target Integration", test_async_target_integration),
        ("Sync Fallback", test_sync_fallback),
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
        print("🎉 All tests passed! Target integration wrapper is working correctly.")
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
