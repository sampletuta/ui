#!/usr/bin/env python3
"""
Test script to verify the face detection fix
"""
import sys
import os
from pathlib import Path

# Add the face_ai directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'face_ai'))

def test_face_detection():
    """Test face detection with the fixed service"""
    import logging
    logging.basicConfig(level=logging.DEBUG)

    from face_ai.services.face_detection import FaceDetectionService

    print("🧪 Testing Face Detection Fix")
    print("=" * 50)

    # Initialize the service
    try:
        face_service = FaceDetectionService()
        print("✅ FaceDetectionService initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize FaceDetectionService: {e}")
        return

    # Test images
    test_images = [
        "/home/user/Desktop/ui/media/target_photos/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg",
        "/home/user/Desktop/ui/media/target_photos/Abiy_Ahmed_with_LI_Yong_2018_cropped.jpeg"
    ]

    for image_path in test_images:
        print(f"\n🔍 Testing image: {os.path.basename(image_path)}")

        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            continue

        # Test face detection
        try:
            result = face_service.detect_faces_in_image(image_path)

            if result['success']:
                faces_detected = result['faces_detected']
                print(f"✅ Detection successful: {faces_detected} faces detected")

                if faces_detected > 0:
                    for i, face in enumerate(result['faces']):
                        bbox = face['bbox']
                        confidence = face['confidence']
                        print(f"   Face {i+1}: bbox={bbox}, confidence={confidence:.3f}")
                else:
                    print("   ℹ️  No faces detected in this image")
            else:
                print(f"❌ Detection failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Exception during detection: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 50)
    print("🎯 Test complete")

if __name__ == "__main__":
    test_face_detection()
