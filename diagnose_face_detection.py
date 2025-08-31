#!/usr/bin/env python3
"""
Diagnostic script to identify and fix face detection issues
"""
import sys
import os
from pathlib import Path

# Add the face_ai directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'face_ai'))

def diagnose_face_detection():
    """Diagnose face detection issues"""
    print("🔍 Face Detection Diagnostic Tool")
    print("=" * 50)

    try:
        from face_ai.services.async_face_detection import AsyncFaceDetectionService

        # Initialize the service
        print("📦 Initializing AsyncFaceDetectionService...")
        face_service = AsyncFaceDetectionService()
        print("✅ Service initialized successfully")

        # Test with a sample image
        test_image = "/home/user/Desktop/ui/media/target_photos/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg"

        if os.path.exists(test_image):
            print(f"\n🖼️  Testing with image: {os.path.basename(test_image)}")

            # Run detection
            import asyncio
            result = asyncio.run(face_service.detect_faces_in_image_async(test_image))

            print(f"🎯 Detection Result: {result.get('success', False)}")
            print(f"   Faces detected: {result.get('faces_detected', 0)}")

            if result.get('success') and result.get('faces_detected', 0) > 0:
                print("   ✅ Face detection working!")
                for i, face in enumerate(result.get('faces', [])):
                    print(f"   Face {i+1}: bbox={face['bbox']}, confidence={face['confidence']:.3f}")
            else:
                print(f"   ❌ Detection failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Test image not found: {test_image}")

    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("🏁 Diagnostic complete")

if __name__ == "__main__":
    diagnose_face_detection()


