#!/usr/bin/env python3
"""
Debug script to test face detection on failing images
"""
import sys
import os
import cv2
import numpy as np
from pathlib import Path

# Add the face_ai directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'face_ai'))

def debug_image(image_path):
    """Debug face detection on a single image"""
    print(f"\n=== Debugging image: {image_path} ===")

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image file does not exist: {image_path}")
        return

    # Load image with OpenCV
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Failed to load image with OpenCV: {image_path}")
        return

    print(f"✅ Image loaded successfully")
    print(f"   Shape: {img.shape}")
    print(f"   Dtype: {img.dtype}")
    print(f"   Size: {img.size} bytes")

    # Check image properties
    height, width = img.shape[:2]
    print(f"   Dimensions: {width}x{height}")
    print(f"   Channels: {img.shape[2] if len(img.shape) > 2 else 1}")

    # Check if image is too small
    min_dimension = min(width, height)
    print(f"   Min dimension: {min_dimension}")

    if min_dimension < 20:
        print(f"⚠️  Image might be too small for face detection (min dimension: {min_dimension})")

    # Convert to grayscale for basic analysis
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Check image brightness and contrast
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)
    print(f"   Mean brightness: {mean_brightness:.2f}")
    print(f"   Brightness std: {std_brightness:.2f}")

    if mean_brightness < 50:
        print("⚠️  Image is very dark")
    elif mean_brightness > 200:
        print("⚠️  Image is very bright")

    if std_brightness < 20:
        print("⚠️  Image has low contrast")

    # Try to load the YuNet model
    try:
        model_path = "/home/user/Desktop/ui/face_detection_yunet_2023mar.onnx"
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return

        print(f"\n📁 Loading YuNet model: {model_path}")

        # Initialize FaceDetectorYN
        face_detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),  # Use smaller input size for testing
            0.5,          # Lower confidence threshold
            0.3,          # NMS threshold
            5000          # Max faces
        )

        if face_detector is None:
            print("❌ Failed to create FaceDetectorYN")
            return

        print("✅ FaceDetectorYN created successfully")

        # Set input size to match image
        face_detector.setInputSize((width, height))
        print(f"✅ Input size set to {width}x{height}")

        # Perform detection
        print("🔍 Performing face detection...")
        detection_result = face_detector.detect(img)

        print(f"   Detection result type: {type(detection_result)}")

        if detection_result is None:
            print("❌ Detection returned None")
            return

        if isinstance(detection_result, tuple):
            print(f"   Detection result is tuple with {len(detection_result)} elements")
            if len(detection_result) == 2:
                faces, confidences = detection_result
                print(f"   Faces shape: {faces.shape if hasattr(faces, 'shape') else 'No shape'}")
                print(f"   Confidences shape: {confidences.shape if hasattr(confidences, 'shape') else 'No shape'}")
            elif len(detection_result) == 1:
                faces = detection_result[0]
                confidences = None
                print(f"   Faces shape: {faces.shape if hasattr(faces, 'shape') else 'No shape'}")
        else:
            faces = detection_result
            confidences = None
            print(f"   Faces shape: {faces.shape if hasattr(faces, 'shape') else 'No shape'}")

        # Analyze faces array
        if faces is None:
            print("❌ Faces is None")
            return

        if hasattr(faces, 'shape'):
            print(f"   Faces array shape: {faces.shape}")
            print(f"   Faces array size: {faces.size}")

            if faces.size == 0:
                print("❌ Faces array is empty")
                return

            if len(faces.shape) == 1:
                if len(faces) >= 15:
                    faces = faces.reshape(1, -1)
                    print("   Reshaped 1D faces array to 2D")
                else:
                    print(f"❌ Invalid 1D faces array length: {len(faces)}")
                    return

            if len(faces.shape) != 2 or faces.shape[1] < 15:
                print(f"❌ Invalid faces array shape: {faces.shape}")
                return

            print(f"✅ Valid faces array shape: {faces.shape}")
            print(f"   Number of faces detected: {faces.shape[0]}")

            # Print face details
            for i, face in enumerate(faces):
                x, y, w, h = face[0], face[1], face[2], face[3]
                confidence = face[14] if len(face) > 14 else 0.0
                print(f"   Face {i+1}: bbox=({x:.1f}, {y:.1f}, {w:.1f}, {h:.1f}), confidence={confidence:.3f}")

                # Check if face is too small
                if w < 20 or h < 20:
                    print(f"   ⚠️  Face {i+1} is very small: {w}x{h}")

                # Check if face bbox is within image bounds
                if x < 0 or y < 0 or x + w > width or y + h > height:
                    print(f"   ⚠️  Face {i+1} bbox extends outside image bounds")

        else:
            print(f"❌ Faces object doesn't have shape attribute: {type(faces)}")

    except Exception as e:
        print(f"❌ Exception during face detection: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main debug function"""
    print("🔧 Face Detection Debug Tool")
    print("=" * 50)

    # Test images
    test_images = [
        "/home/user/Desktop/ui/media/target_photos/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg",
        "/home/user/Desktop/ui/media/target_photos/Abiy_Ahmed_with_LI_Yong_2018_cropped.jpeg"
    ]

    for image_path in test_images:
        debug_image(image_path)

    print("\n" + "=" * 50)
    print("🎯 Debug complete")

if __name__ == "__main__":
    main()


