# FastPublisher ↔ Source Manager Integration Guide

This document explains how FastPublisher integrates with the Django Source Manager to process videos and publish frames to Kafka.

## 🌐 **Overview**

The integration follows this flow:
1. **Source Manager** stores video files and provides unauthenticated access to them
2. **FastPublisher** submits video processing requests via unauthenticated endpoints
3. **FastPublisher** pulls video streams without authentication
4. **FastPublisher** sends processing results back via callback URLs
5. **FastPublisher** publishes processed frames to Kafka

## 🔗 **Base URLs**

- **Source Manager**: `http://localhost:8000` (configurable via `BASE_URL`)
- **FastPublisher**: `http://localhost:5665` (configurable on Source Manager via `VIDEO_PROCESSING_SERVICE.BASE_URL`)

## 📡 **Unauthenticated Endpoints**

All FastPublisher integration endpoints are **unauthenticated** to ensure seamless integration.

### **1. Submit Video for Processing**

#### **POST** `/source-management/api/fastpublisher-submit/{source_id}/`

Submit a video for processing. This endpoint is specifically designed for FastPublisher and doesn't require authentication.

**Request Body:**
```json
{
  "target_fps": 5,
  "target_resolution": "640x480"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Video processing job submitted successfully",
  "job_id": "job-a1b2c3d4",
  "external_job_id": "ext-job-123",
  "estimated_completion_time": "Calculating...",
  "processing_started_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Job submitted successfully
- `400 Bad Request` - Invalid parameters or video not ready
- `404 Not Found` - Video source not found

---

### **2. Access Video Stream**

#### **GET** `/source-management/api/fastpublisher-video/{source_id}/`

Stream the video file directly. This endpoint provides unauthenticated access to video content for FastPublisher processing.

**Features:**
- Supports HTTP Range requests for efficient streaming
- Returns video with proper MIME type (`video/mp4`)
- No authentication required
- Optimized for large file streaming

**Response Headers:**
```
Content-Type: video/mp4
Accept-Ranges: bytes
Content-Length: [file_size]
```

**Status Codes:**
- `200 OK` - Full video stream
- `206 Partial Content` - Range request response
- `400 Bad Request` - Video not ready
- `404 Not Found` - Video not found

---

### **3. Get Video Metadata**

#### **GET** `/source-management/api/fastpublisher-metadata/{source_id}/`

Get comprehensive video metadata without authentication.

**Response:**
```json
{
  "source_id": "uuid-1234-5678-9abc-def0",
  "name": "sample_video.mp4",
  "file_size": 10485760,
  "duration": 120.5,
  "width": 1920,
  "height": 1080,
  "fps": 30.0,
  "codec": "h264",
  "audio_codec": "aac",
  "audio_channels": 2,
  "audio_sample_rate": 44100,
  "bitrate": 8000000,
  "file_format": "mp4",
  "status": "ready",
  "stream_url": "/source-management/api/fastpublisher-video/uuid-1234-5678-9abc-def0/",
  "access_token": "abc123def456"
}
```

---

### **4. Check Processing Status**

#### **GET** `/source-management/api/fastpublisher-status/{source_id}/`

Check the status of video processing jobs for a specific source.

**Response:**
```json
{
  "source_id": "uuid-1234-5678-9abc-def0",
  "job_id": "job-a1b2c3d4",
  "status": "processing",
  "message": "Job is processing normally",
  "processed_video_url": null
}
```

---

### **5. Processing Callback**

#### **POST** `/source-management/api/processing-callback/{access_token}/`

FastPublisher sends processing results back to Source Manager.

**Request Body:**
```json
{
  "job_id": "ext-job-123",
  "status": "completed",
  "message": "Processing completed successfully",
  "processed_video_url": "https://fastpublisher.com/processed/video123.mp4",
  "metadata": {
    "frames_processed": 1500,
    "processing_time": 45.2,
    "output_resolution": "640x480",
    "output_fps": 5
  }
}
```

## 🔄 **Integration Flow**

### **Step 1: Submit Video for Processing**
```bash
curl -X POST "http://localhost:8000/source-management/api/fastpublisher-submit/{source_id}/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "target_fps=5&target_resolution=640x480"
```

### **Step 2: Access Video Stream**
```bash
curl "http://localhost:8000/source-management/api/fastpublisher-video/{source_id}/" \
  -H "Range: bytes=0-1048575" \
  --output video_chunk.mp4
```

### **Step 3: Process Video and Publish to Kafka**
FastPublisher processes the video stream and publishes frames to Kafka topics.

### **Step 4: Send Results Back**
```bash
curl -X POST "http://localhost:8000/source-management/api/processing-callback/{access_token}/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "ext-job-123",
    "status": "completed",
    "message": "Processing completed successfully"
  }'
```

## ⚙️ **Configuration**

### **Source Manager Settings**
```python
# settings.py
VIDEO_PROCESSING_SERVICE = {
    'BASE_URL': 'http://localhost:5665',  # FastPublisher URL
    'API_KEY': 'your-api-key',           # Optional authentication
    'SUBMIT_ENDPOINT': '/process_video',
    'STATUS_ENDPOINT': '/status/{source_id}',
    'TIMEOUT': 30
}

BASE_URL = 'http://localhost:8000'  # Source Manager URL
```

### **FastPublisher Settings**
```python
# FastPublisher config
SOURCE_MANAGER_BASE_URL = "http://localhost:8000"
VIDEO_PROCESSING_ENDPOINTS = {
    'submit': '/source-management/api/fastpublisher-submit/{source_id}/',
    'stream': '/source-management/api/fastpublisher-video/{source_id}/',
    'metadata': '/source-management/api/fastpublisher-metadata/{source_id}/',
    'status': '/source-management/api/fastpublisher-status/{source_id}/'
}
```

## 🚀 **FastPublisher Implementation**

### **Python Example**
```python
import requests
import json

class SourceManagerClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def submit_video(self, source_id, target_fps, target_resolution):
        """Submit video for processing"""
        url = f"{self.base_url}/source-management/api/fastpublisher-submit/{source_id}/"
        data = {
            'target_fps': target_fps,
            'target_resolution': target_resolution
        }
        response = requests.post(url, data=data)
        return response.json()
    
    def get_video_stream(self, source_id, range_header=None):
        """Get video stream for processing"""
        url = f"{self.base_url}/source-management/api/fastpublisher-video/{source_id}/"
        headers = {}
        if range_header:
            headers['Range'] = range_header
        
        response = requests.get(url, headers=headers, stream=True)
        return response
    
    def get_video_metadata(self, source_id):
        """Get video metadata"""
        url = f"{self.base_url}/source-management/api/fastpublisher-metadata/{source_id}/"
        response = requests.get(url)
        return response.json()
    
    def send_callback(self, access_token, callback_data):
        """Send processing results back"""
        url = f"{self.base_url}/source-management/api/processing-callback/{access_token}/"
        response = requests.post(url, json=callback_data)
        return response.json()

# Usage
client = SourceManagerClient()

# Submit video for processing
result = client.submit_video("uuid-1234", 5, "640x480")
print(f"Job submitted: {result['job_id']}")

# Get video stream and process
stream_response = client.get_video_stream("uuid-1234")
# Process video stream and publish to Kafka...

# Send results back
callback_data = {
    "job_id": "ext-job-123",
    "status": "completed",
    "message": "Processing completed successfully"
}
client.send_callback(result['access_token'], callback_data)
```

## 🔒 **Security Considerations**

- **No Authentication Required**: FastPublisher endpoints are intentionally unauthenticated for seamless integration
- **Access Token Validation**: Callback URLs use unique access tokens for security
- **Source ID Validation**: All endpoints validate source_id to prevent unauthorized access
- **Rate Limiting**: Consider implementing rate limiting for production use

## 🧪 **Testing**

### **Test Video Submission**
```bash
# Test with a valid source_id
curl -X POST "http://localhost:8000/source-management/api/fastpublisher-submit/{valid_source_id}/" \
  -d "target_fps=3&target_resolution=320x240"
```

### **Test Video Streaming**
```bash
# Test video stream access
curl -I "http://localhost:8000/source-management/api/fastpublisher-video/{valid_source_id}/"
```

### **Test Metadata Access**
```bash
# Test metadata endpoint
curl "http://localhost:8000/source-management/api/fastpublisher-metadata/{valid_source_id}/"
```

## 📝 **Notes**

1. **Video Status**: Only videos with status `'ready'` can be processed
2. **FPS Limits**: `target_fps` must be between 1-5 as per FastPublisher requirements
3. **Resolution Format**: `target_resolution` must be in format "widthxheight" (e.g., "640x480")
4. **File Formats**: Supports MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
5. **Streaming**: Video streaming supports HTTP Range requests for efficient processing
6. **Error Handling**: All endpoints return proper HTTP status codes and error messages

## 🆘 **Troubleshooting**

### **Common Issues**

1. **Video Not Ready**: Ensure video status is `'ready'` before processing
2. **Invalid Parameters**: Check `target_fps` (1-5) and `target_resolution` format
3. **Stream Access**: Verify source_id exists and video file is accessible
4. **Callback Errors**: Ensure access_token is valid and callback URL is correct

### **Debug Endpoints**

- **Health Check**: `/source-management/api/fastpublisher-status/{source_id}/`
- **Metadata**: `/source-management/api/fastpublisher-metadata/{source_id}/`
- **Processing Jobs**: `/source-management/api/processing-jobs/{source_id}/`

This integration ensures that FastPublisher can seamlessly process videos from Source Manager and publish frames to Kafka without authentication barriers.
