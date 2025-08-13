# Video Player API Documentation

This document describes the API endpoints for the Video Player module that allows external services to send video streams and detection events asynchronously.

## Base URL
```
http://localhost:8000/video_player/
```

## API Endpoints

### 1. Receive Video Streams
**POST** `/api/video-streams/`

Receives video streams data from external services.

**Request Body:**
```json
{
    "camera_1": {
        "name": "Camera 1 - Main Entrance",
        "liveUrl": "https://example.com/live.mp4",
        "archiveUrl": "https://example.com/archive.mp4",
        "status": "live",
        "location": "Main Entrance",
        "last_detection": "2 min ago",
        "duration": 596,
        "timeTags": [
            {
                "id": "tag_1_1",
                "time": 30,
                "label": "Person detected",
                "type": "detection",
                "color": "#ef4444"
            }
        ],
        "bookmarks": [
            {
                "id": "bookmark_1_1",
                "time": 60,
                "label": "Morning shift start",
                "description": "Security guard arrives"
            }
        ]
    }
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Received 1 video streams",
    "timestamp": 1703123456.789
}
```

### 2. Receive Detection Events
**POST** `/api/detection-events/`

Receives detection events data from external services.

**Request Body:**
```json
[
    {
        "id": "detection_1",
        "camera_id": "camera_1",
        "camera_name": "Camera 1 - Main Entrance",
        "thumbnail": "https://example.com/thumb.jpg",
        "time_ago": "1 min ago",
        "status": "live",
        "location": "Main Entrance",
        "timestamp": 30,
        "time_label": "00:30"
    }
]
```

**Response:**
```json
{
    "status": "success",
    "message": "Received 1 detection events",
    "timestamp": 1703123456.789
}
```

### 3. Get Current Video Streams
**GET** `/api/video-streams/get/`

Retrieves current video streams data.

**Response:**
```json
{
    "status": "success",
    "data": {
        "camera_1": {
            "name": "Camera 1 - Main Entrance",
            "liveUrl": "https://example.com/live.mp4",
            "archiveUrl": "https://example.com/archive.mp4",
            "status": "live",
            "location": "Main Entrance",
            "last_detection": "2 min ago",
            "duration": 596,
            "timeTags": [...],
            "bookmarks": [...]
        }
    },
    "timestamp": 1703123456.789
}
```

### 4. Get Current Detection Events
**GET** `/api/detection-events/get/`

Retrieves current detection events.

**Response:**
```json
{
    "status": "success",
    "data": [
        {
            "id": "detection_1",
            "camera_id": "camera_1",
            "camera_name": "Camera 1 - Main Entrance",
            "thumbnail": "https://example.com/thumb.jpg",
            "time_ago": "1 min ago",
            "status": "live",
            "location": "Main Entrance",
            "timestamp": 30,
            "time_label": "00:30"
        }
    ],
    "timestamp": 1703123456.789
}
```

### 5. Update Specific Camera
**PUT** `/api/camera/{camera_id}/`

Updates data for a specific camera.

**Request Body:**
```json
{
    "status": "warning",
    "last_detection": "Just now",
    "timeTags": [
        {
            "id": "tag_update_1",
            "time": 90,
            "label": "New detection",
            "type": "detection",
            "color": "#ef4444"
        }
    ]
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Updated camera camera_1",
    "timestamp": 1703123456.789
}
```

### 6. Add Single Detection Event
**POST** `/api/detection-event/add/`

Adds a single detection event to the current list.

**Request Body:**
```json
{
    "id": "detection_123",
    "camera_id": "camera_1",
    "camera_name": "Camera 1 - Main Entrance",
    "thumbnail": "https://example.com/thumb.jpg",
    "time_ago": "Just now",
    "status": "live",
    "location": "Main Entrance",
    "timestamp": 30,
    "time_label": "00:30"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Detection event added",
    "timestamp": 1703123456.789
}
```

### 7. Clear All Data
**DELETE** `/api/clear-data/`

Clears all video streams and detection events data.

**Response:**
```json
{
    "status": "success",
    "message": "All data cleared",
    "timestamp": 1703123456.789
}
```

## Data Formats

### Video Stream Object
```json
{
    "name": "Camera Name",
    "liveUrl": "https://example.com/live.mp4",
    "archiveUrl": "https://example.com/archive.mp4",
    "status": "live|recorded|warning",
    "location": "Location Description",
    "last_detection": "time ago",
    "duration": 596,
    "timeTags": [
        {
            "id": "unique_tag_id",
            "time": 30,
            "label": "Event Label",
            "type": "detection|event|alert",
            "color": "#ef4444"
        }
    ],
    "bookmarks": [
        {
            "id": "unique_bookmark_id",
            "time": 60,
            "label": "Bookmark Label",
            "description": "Bookmark Description"
        }
    ]
}
```

### Detection Event Object
```json
{
    "id": "unique_detection_id",
    "camera_id": "camera_id",
    "camera_name": "Camera Name",
    "thumbnail": "https://example.com/thumb.jpg",
    "time_ago": "time ago",
    "status": "live|recorded|warning",
    "location": "Location Description",
    "timestamp": 30,
    "time_label": "MM:SS"
}
```

## Error Responses

All endpoints return error responses in the following format:

```json
{
    "status": "error",
    "message": "Error description"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid JSON or data format)
- `500`: Internal Server Error

## Usage Examples

### Python Example
```python
import requests
import json

# Send video streams
video_streams = {
    "camera_1": {
        "name": "Camera 1 - Main Entrance",
        "liveUrl": "https://example.com/live.mp4",
        "archiveUrl": "https://example.com/archive.mp4",
        "status": "live",
        "location": "Main Entrance",
        "last_detection": "2 min ago",
        "duration": 596,
        "timeTags": [],
        "bookmarks": []
    }
}

response = requests.post(
    "http://localhost:8000/video_player/api/video-streams/",
    json=video_streams,
    headers={'Content-Type': 'application/json'}
)

print(response.json())
```

### JavaScript Example
```javascript
// Send detection events
const detectionEvents = [
    {
        id: "detection_1",
        camera_id: "camera_1",
        camera_name: "Camera 1 - Main Entrance",
        thumbnail: "https://example.com/thumb.jpg",
        time_ago: "1 min ago",
        status: "live",
        location: "Main Entrance",
        timestamp: 30,
        time_label: "00:30"
    }
];

fetch('http://localhost:8000/video_player/api/detection-events/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(detectionEvents)
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL Example
```bash
# Send video streams
curl -X POST http://localhost:8000/video_player/api/video-streams/ \
  -H "Content-Type: application/json" \
  -d '{
    "camera_1": {
      "name": "Camera 1 - Main Entrance",
      "liveUrl": "https://example.com/live.mp4",
      "archiveUrl": "https://example.com/archive.mp4",
      "status": "live",
      "location": "Main Entrance",
      "last_detection": "2 min ago",
      "duration": 596,
      "timeTags": [],
      "bookmarks": []
    }
  }'

# Get current data
curl http://localhost:8000/video_player/api/video-streams/get/
```

## Real-time Integration

The API is designed for real-time integration with external services:

1. **Asynchronous Updates**: All endpoints are non-blocking and handle concurrent requests
2. **Thread-Safe**: Uses locks to prevent data corruption during concurrent updates
3. **Memory Management**: Automatically limits detection events to prevent memory issues
4. **Fallback Data**: If no real-time data is available, falls back to sample data

## Testing

Use the provided `api_example.py` script to test all endpoints:

```bash
python video_player/api_example.py
```

This script demonstrates:
- Sending video streams and detection events
- Adding single detection events
- Updating specific cameras
- Retrieving current data
- Simulating real-time updates

## Security Notes

- All endpoints are CSRF exempt for external service integration
- Consider adding authentication for production use
- Input validation is performed on all endpoints
- Error handling prevents data corruption 