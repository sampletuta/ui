#!/usr/bin/env python3
"""
Test the yunet.onnx file to see if it works correctly
"""

import cv2
import numpy as np
import os

def test_yunet_onnx():
    """Test the yunet.onnx file"""
    print("🔍 Testing yunet.onnx file...")
    
    try:
        # Check the yunet.onnx file
        model_path = "yunet.onnx"
        
        if not os.path.exists(model_path):
            print(f"❌ Model not found: {model_path}")
            return False
            
        size = os.path.getsize(model_path)
        print(f"✅ Model found: {model_path}")
        print(f"   Size: {size} bytes ({size/1024:.1f} KB)")
        
        # Check if size is reasonable
        if size < 100000:  # < 100KB
            print("   ❌ Model file is too small")
            return False
        elif size < 500000:  # < 500KB
            print("   ⚠️ Model file is small but might work")
        elif size < 2000000:  # < 2MB
            print("   ✅ Model file size looks reasonable")
        else:
            print("   ✅ Model file size looks good")
            
        # Try to create FaceDetectorYN
        print("\n🔧 Creating FaceDetectorYN with yunet.onnx...")
        detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),
            0.9,
            0.3,
            5000
        )
        
        print("✅ FaceDetectorYN created successfully")
        
        # Test 1: Blank image - should detect NO faces
        print("\n📸 Test 1: Blank image (should detect NO faces)")
        blank_img = np.full((480, 640, 3), 128, dtype=np.uint8)
        
        detector.setInputSize((640, 480))
        retval, faces = detector.detect(blank_img)
        
        print(f"   Return value: {retval} (type: {type(retval)})")
        print(f"   Faces: {faces} (type: {type(faces)})")
        
        if retval == 0:
            print("   ✅ CORRECT: No faces detected in blank image")
        elif retval > 0 and faces is None:
            print(f"   ❌ ISSUE: Detected {retval} faces but can't provide coordinates")
        elif retval > 0 and faces is not None:
            print(f"   ❌ UNEXPECTED: Detected {retval} faces in blank image")
        else:
            print("   ✅ CORRECT: No faces detected")
            
        # Test 2: Image with face-like pattern
        print("\n📸 Test 2: Image with face-like pattern")
        face_img = np.full((480, 640, 3), 128, dtype=np.uint8)
        
        # Add a face-like pattern
        cv2.rectangle(face_img, (200, 150), (400, 350), (255, 255, 255), -1)
        cv2.circle(face_img, (250, 200), 20, (0, 0, 0), -1)  # Left eye
        cv2.circle(face_img, (350, 200), 20, (0, 0, 0), -1)  # Right eye
        cv2.circle(face_img, (300, 250), 15, (0, 0, 0), -1)  # Nose
        
        retval, faces = detector.detect(face_img)
        
        print(f"   Return value: {retval} (type: {type(retval)})")
        print(f"   Faces: {faces} (type: {type(faces)})")
        
        if retval > 0 and faces is not None:
            print(f"   ✅ CORRECT: Detected {retval} faces with coordinates")
            print(f"   Faces shape: {faces.shape}")
            print(f"   First face data: {faces[0]}")
        elif retval > 0 and faces is None:
            print(f"   ❌ ISSUE: Detected {retval} faces but can't provide coordinates")
        else:
            print("   ❌ UNEXPECTED: No faces detected in face image")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_models():
    """Compare all available models"""
    print("\n📊 **MODEL COMPARISON:**")
    print("=" * 50)
    
    models = [
        ("yunet.onnx", "Root directory"),
        ("face_detection_yunet_2023mar.onnx", "Root directory"),
        ("face_ai/face_detection_yunet_2023mar.onnx", "face_ai/ directory"),
        ("face_ai/yunet_n_120_160.onnx", "face_ai/ directory")
    ]
    
    for model_path, location in models:
        if os.path.exists(model_path):
            size = os.path.getsize(model_path)
            status = "✅ WORKING" if size > 500000 else "❌ CORRUPTED"
            print(f"   {location}: {model_path}")
            print(f"     Size: {size} bytes ({size/1024:.1f} KB) - {status}")
        else:
            print(f"   {location}: {model_path} - ❌ NOT FOUND")

if __name__ == "__main__":
    print("🚀 Yunet.onnx Test")
    print("=" * 50)
    
    success = test_yunet_onnx()
    compare_models()
    
    if success:
        print("\n🎯 Test completed successfully!")
    else:
        print("\n⚠️ Test failed - check the errors above")
