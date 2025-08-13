#!/usr/bin/env python3
"""
Real-time test script for Video Player API
Simulates external services sending data asynchronously
Uses uploaded videos and real online video sources
"""

import requests
import time
import json
import random
from datetime import datetime
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:8000/video/api/"

# Video Sources Configuration
VIDEO_FILES_DIR = "../media/videos"

# Real online video sources for testing
ONLINE_VIDEO_SOURCES = {
    "camera_1": {
        "name": "Camera 1 - Main Entrance",
        "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "status": "live",
        "location": "Main Entrance",
        "description": "High-traffic security checkpoint"
    },
    "camera_2": {
        "name": "Camera 2 - Parking Lot",
        "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "status": "recorded",
        "location": "Parking Lot",
        "description": "Vehicle monitoring and access control"
    },
    "camera_3": {
        "name": "Camera 3 - Security Gate",
        "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "status": "live",
        "location": "Security Gate",
        "description": "Perimeter security and access control"
    },
    "camera_4": {
        "name": "Camera 4 - Loading Dock",
        "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "status": "warning",
        "location": "Loading Dock",
        "description": "Logistics and safety monitoring"
    },
    "camera_5": {
        "name": "Camera 5 - Office Area",
        "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        "status": "recorded",
        "location": "Office Area",
        "description": "Internal security and activity monitoring"
    }
}

def get_uploaded_videos():
    """Get list of uploaded video files"""
    video_dir = Path(VIDEO_FILES_DIR)
    video_files = []
    
    if video_dir.exists():
        for file in video_dir.glob("*.mp4"):
            video_files.append({
                'name': file.stem,
                'path': str(file),
                'size': file.stat().st_size
            })
    
    return video_files

def create_hybrid_video_sources():
    """Create video sources using uploaded videos and online sources"""
    uploaded_videos = get_uploaded_videos()
    hybrid_sources = {}
    
    print(f"📁 Found {len(uploaded_videos)} uploaded video files")
    
    # Use uploaded videos for first 5 cameras if available
    for i in range(1, 6):
        camera_id = f"camera_{i}"
        
        if i <= len(uploaded_videos):
            # Use uploaded video
            video_file = uploaded_videos[i-1]
            hybrid_sources[camera_id] = {
                "name": ONLINE_VIDEO_SOURCES[camera_id]["name"],
                "liveUrl": f"/media/videos/{video_file['name']}.mp4",
                "archiveUrl": f"/media/videos/{video_file['name']}.mp4",
                "status": ONLINE_VIDEO_SOURCES[camera_id]["status"],
                "location": ONLINE_VIDEO_SOURCES[camera_id]["location"],
                "description": ONLINE_VIDEO_SOURCES[camera_id]["description"],
                "source_type": "uploaded",
                "file_size": f"{video_file['size'] / (1024*1024):.1f} MB"
            }
            print(f"   Camera {i}: Using uploaded video - {video_file['name']}.mp4")
        else:
            # Use online video source
            hybrid_sources[camera_id] = ONLINE_VIDEO_SOURCES[camera_id].copy()
            hybrid_sources[camera_id]["source_type"] = "online"
            print(f"   Camera {i}: Using online video source")
    
    # Add more cameras with online sources
    for i in range(6, 11):
        camera_id = f"camera_{i}"
        online_sources = [
            {
                "name": f"Camera {i} - Surveillance Point {i}",
                "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "status": random.choice(["live", "recorded", "warning"]),
                "location": f"Surveillance Point {i}",
                "description": f"Additional security camera {i}",
                "source_type": "online"
            },
            {
                "name": f"Camera {i} - Monitoring Station {i}",
                "liveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                "archiveUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                "status": random.choice(["live", "recorded", "warning"]),
                "location": f"Monitoring Station {i}",
                "description": f"Remote monitoring camera {i}",
                "source_type": "online"
            }
        ]
        hybrid_sources[camera_id] = random.choice(online_sources)
        print(f"   Camera {i}: Using online video source")
    
    return hybrid_sources

def send_video_stream_update(camera_id, update_data):
    """Send video stream update to API"""
    try:
        response = requests.put(
            f"{BASE_URL}camera/{camera_id}/",
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Camera {camera_id} updated: {result['message']}")
            return True
        else:
            print(f"❌ Failed to update camera {camera_id}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating camera {camera_id}: {e}")
        return False

def add_detection_event(detection_data):
    """Add detection event to API"""
    try:
        response = requests.post(
            f"{BASE_URL}detection-event/add/",
            json=detection_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Detection event added: {result['message']}")
            return True
        else:
            print(f"❌ Failed to add detection event: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding detection event: {e}")
        return False

def initialize_video_sources():
    """Initialize all video sources in the API"""
    print("📤 Initializing video sources...")
    
    hybrid_sources = create_hybrid_video_sources()
    
    try:
        response = requests.post(
            f"{BASE_URL}video-streams/",
            json=hybrid_sources,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Video sources initialized: {result['message']}")
            return True
        else:
            print(f"❌ Failed to initialize video sources: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing video sources: {e}")
        return False

def simulate_live_detections():
    """Simulate live detection events with multiple cameras"""
    print("🎯 Starting live detection simulation...")
    print("Press Ctrl+C to stop")
    
    detection_count = 0
    camera_names = {
        "camera_1": "Main Entrance",
        "camera_2": "Parking Lot", 
        "camera_3": "Security Gate",
        "camera_4": "Loading Dock",
        "camera_5": "Office Area",
        "camera_6": "Surveillance Point 6",
        "camera_7": "Monitoring Station 7",
        "camera_8": "Surveillance Point 8",
        "camera_9": "Monitoring Station 9",
        "camera_10": "Surveillance Point 10"
    }
    
    while True:
        try:
            # Random camera selection (1-10 cameras)
            camera_id = f"camera_{random.randint(1, 10)}"
            camera_name = camera_names.get(camera_id, f"Camera {camera_id[-1]}")
            
            # Random detection type
            detection_types = [
                "Person detected", "Vehicle entry", "Motion detected", "Suspicious activity",
                "Unauthorized access", "Security breach", "Equipment malfunction", "Safety violation",
                "Guard response", "System reset", "Door opened", "Window breach",
                "Perimeter breach", "Fire alarm", "Medical emergency", "Equipment failure"
            ]
            detection_type = random.choice(detection_types)
            
            # Random timestamp
            timestamp = random.randint(30, 600)  # 30 seconds to 10 minutes
            minutes = timestamp // 60
            seconds = timestamp % 60
            time_label = f"{minutes:02d}:{seconds:02d}"
            
            # Random status with weighted probability
            status_weights = {"live": 0.4, "recorded": 0.4, "warning": 0.2}
            status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
            
            # Create detection event
            detection_data = {
                "id": f"live_detection_{detection_count}_{int(time.time())}",
                "camera_id": camera_id,
                "camera_name": f"Camera {camera_id[-1]} - {camera_name}",
                "thumbnail": f"https://i.imgur.com/{random.choice(['xVwYpWi', '39N24qU', 'KzXGmh4', 'i4aYwzB', 'fPbnMo9', 'yVwYpWi', '39N24qU', 'KzXGmh4'])}.jpeg",
                "time_ago": "Just now",
                "status": status,
                "location": camera_name,
                "timestamp": timestamp,
                "time_label": time_label,
                "detection_type": detection_type
            }
            
            # Add detection event
            add_detection_event(detection_data)
            
            # Randomly update camera status (40% chance)
            if random.random() < 0.4:
                camera_update = {
                    "last_detection": "Just now",
                    "status": status,
                    "last_activity": datetime.now().isoformat()
                }
                send_video_stream_update(camera_id, camera_update)
            
            detection_count += 1
            
            # Random delay between 2-6 seconds
            delay = random.uniform(2, 6)
            print(f"⏱️  Next detection in {delay:.1f} seconds... (Camera: {camera_id})")
            time.sleep(delay)
            
        except KeyboardInterrupt:
            print("\n🛑 Live detection simulation stopped")
            break
        except Exception as e:
            print(f"❌ Error in simulation: {e}")
            time.sleep(5)

def simulate_camera_updates():
    """Simulate camera status updates for multiple cameras"""
    print("📹 Starting camera status simulation...")
    print("Press Ctrl+C to stop")
    
    while True:
        try:
            # Update random camera (1-10 cameras)
            camera_id = f"camera_{random.randint(1, 10)}"
            
            # Random status update with more variety
            status_updates = [
                {"status": "live", "last_detection": "Just now", "connection_quality": "excellent"},
                {"status": "recorded", "last_detection": "1 min ago", "connection_quality": "good"},
                {"status": "warning", "last_detection": "2 min ago", "connection_quality": "poor"},
                {"status": "live", "last_detection": "30 seconds ago", "connection_quality": "excellent"},
                {"status": "recorded", "last_detection": "5 min ago", "connection_quality": "good"},
                {"status": "warning", "last_detection": "1 min ago", "connection_quality": "poor"},
                {"status": "live", "last_detection": "45 seconds ago", "connection_quality": "excellent"}
            ]
            
            update_data = random.choice(status_updates)
            update_data["last_activity"] = datetime.now().isoformat()
            
            send_video_stream_update(camera_id, update_data)
            
            # Random delay between 8-15 seconds
            delay = random.uniform(8, 15)
            print(f"⏱️  Next camera update in {delay:.1f} seconds... (Camera: {camera_id})")
            time.sleep(delay)
            
        except KeyboardInterrupt:
            print("\n🛑 Camera status simulation stopped")
            break
        except Exception as e:
            print(f"❌ Error in camera simulation: {e}")
            time.sleep(5)

def simulate_video_source_changes():
    """Simulate video source changes (switching between uploaded and online sources)"""
    print("🔄 Starting video source change simulation...")
    print("Press Ctrl+C to stop")
    
    uploaded_videos = get_uploaded_videos()
    online_sources = [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
    ]
    
    while True:
        try:
            # Random camera selection
            camera_id = f"camera_{random.randint(1, 5)}"
            
            # Randomly switch between uploaded and online sources
            if random.random() < 0.5 and uploaded_videos:
                # Switch to uploaded video
                video_file = random.choice(uploaded_videos)
                update_data = {
                    "liveUrl": f"/media/videos/{video_file['name']}.mp4",
                    "archiveUrl": f"/media/videos/{video_file['name']}.mp4",
                    "source_type": "uploaded",
                    "last_change": datetime.now().isoformat()
                }
                print(f"🔄 Camera {camera_id}: Switching to uploaded video - {video_file['name']}.mp4")
            else:
                # Switch to online source
                online_source = random.choice(online_sources)
                update_data = {
                    "liveUrl": online_source,
                    "archiveUrl": online_source,
                    "source_type": "online",
                    "last_change": datetime.now().isoformat()
                }
                print(f"🔄 Camera {camera_id}: Switching to online video source")
            
            send_video_stream_update(camera_id, update_data)
            
            # Random delay between 20-40 seconds
            delay = random.uniform(20, 40)
            print(f"⏱️  Next source change in {delay:.1f} seconds...")
            time.sleep(delay)
            
        except KeyboardInterrupt:
            print("\n🛑 Video source change simulation stopped")
            break
        except Exception as e:
            print(f"❌ Error in source change simulation: {e}")
            time.sleep(5)

def main():
    """Main function"""
    print("🎥 Video Player Real-time Test with Multiple Sources")
    print("=" * 60)
    print("This script simulates external services sending data to the video player API")
    print("Uses uploaded videos and real online video sources")
    print("Make sure the Django server is running on localhost:8000")
    print()
    
    # Test API connection
    try:
        response = requests.get(f"{BASE_URL}video-streams/get/")
        if response.status_code == 200:
            print("✅ API connection successful")
        else:
            print("❌ API connection failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return
    
    # Initialize video sources
    if not initialize_video_sources():
        print("❌ Failed to initialize video sources")
        return
    
    print("\nChoose simulation mode:")
    print("1. Live detections (adds detection events)")
    print("2. Camera updates (updates camera status)")
    print("3. Video source changes (switches between uploaded/online)")
    print("4. All simulations (runs in separate threads)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        simulate_live_detections()
    elif choice == "2":
        simulate_camera_updates()
    elif choice == "3":
        simulate_video_source_changes()
    elif choice == "4":
        import threading
        
        print("🔄 Starting all simulations...")
        
        # Start detection simulation in separate thread
        detection_thread = threading.Thread(target=simulate_live_detections)
        detection_thread.daemon = True
        detection_thread.start()
        
        # Start camera updates in separate thread
        camera_thread = threading.Thread(target=simulate_camera_updates)
        camera_thread.daemon = True
        camera_thread.start()
        
        # Start source changes in main thread
        simulate_video_source_changes()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main() 