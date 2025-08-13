# Source Manager - REST API Documentation

## 🌐 **API Overview**

The Source Manager provides a comprehensive RESTful API for managing video sources, processing videos, and integrating with external services like FastPublisher. This document describes all available endpoints, request/response schemas, and usage examples.

**Base URL**: `http://localhost:8000`  
**API Version**: v1  
**Content-Type**: `application/json`

## 📋 **Table of Contents**

- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Data Schemas](#data-schemas)
- [Error Handling](#error-handling)
- [FastPublisher Integration](#fastpublisher-integration)
- [Examples](#examples)
- [Testing](#testing)

## 🔐 **Authentication**

### **Authenticated Endpoints**
Most endpoints require user authentication via the `@login_required_source_list` decorator. Users must be logged in to access:
- Dashboard and source management
- Video upload and processing
- Source CRUD operations

### **Unauthenticated Endpoints**
FastPublisher integration endpoints are intentionally unauthenticated for seamless service-to-service communication:
- Video submission for processing
- Video streaming access
- Video metadata retrieval
- Processing status checks
- Callback handling

## 🚀 **Endpoints**

### **Dashboard & Source Management**

#### **GET** `/source-management/`
**Authentication Required**: Yes  
**Description**: Main dashboard showing all video sources

#### **GET** `/source-management/dashboard/`
**Authentication Required**: Yes  
**Description**: Alternative dashboard route

---

### **Source Creation & Management**

#### **GET** `/source-management/add/`
**Authentication Required**: Yes  
**Description**: Form to create new video sources

#### **POST** `/source-management/add/`
**Authentication Required**: Yes  
**Description**: Create new video source

#### **GET** `/source-management/file/{source_id}/`
**Authentication Required**: Yes  
**Description**: View file source details

#### **GET** `/source-management/file/{source_id}/edit/`
**Authentication Required**: Yes  
**Description**: Edit file source form

#### **POST** `/source-management/file/{source_id}/edit/`
**Authentication Required**: Yes  
**Description**: Update file source

#### **POST** `/source-management/file/{source_id}/delete/`
**Authentication Required**: Yes  
**Description**: Delete file source

---

### **API Endpoints (Authenticated)**

#### **GET** `/source-management/api/source/{source_id}/`
**Authentication Required**: Yes  
**Description**: Get source metadata

#### **GET** `/source-management/api/video/{access_token}/`
**Authentication Required**: Yes  
**Description**: Get video access information

#### **GET** `/source-management/api/video/{access_token}/metadata/`
**Authentication Required**: Yes  
**Description**: Get video metadata

#### **GET** `/source-management/api/video/{access_token}/download/`
**Authentication Required**: Yes  
**Description**: Download video file

#### **GET** `/source-management/api/video/{access_token}/stream/`
**Authentication Required**: Yes  
**Description**: Stream video (authenticated)

---

### **Video Processing (Authenticated)**

#### **POST** `/source-management/api/process-video/{source_id}/`
**Authentication Required**: Yes  
**Description**: Submit video for processing

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

#### **GET** `/source-management/api/processing-status/{job_id}/`
**Authentication Required**: Yes  
**Description**: Get processing job status

#### **POST** `/source-management/api/cancel-processing/{job_id}/`
**Authentication Required**: Yes  
**Description**: Cancel processing job

#### **GET** `/source-management/api/processing-jobs/{source_id}/`
**Authentication Required**: Yes  
**Description**: List processing jobs for a source

---

## 🔗 **FastPublisher Integration (Unauthenticated)**

All FastPublisher integration endpoints are **unauthenticated** to ensure seamless service-to-service communication.

### **1. Submit Video for Processing**

#### **POST** `/source-management/api/fastpublisher-submit/{source_id}/`
**Authentication Required**: No  
**Description**: Submit video for FastPublisher processing

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
**Authentication Required**: No  
**Description**: Stream video file for FastPublisher processing

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
**Authentication Required**: No  
**Description**: Get comprehensive video metadata

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
**Authentication Required**: No  
**Description**: Check video processing job status

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
**Authentication Required**: No  
**Description**: FastPublisher sends processing results back

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

---

## 📊 **Data Schemas**

### **Video Source Schema**
```json
{
  "source_id": "uuid",
  "name": "string",
  "description": "string",
  "source_type": "file|camera|stream",
  "status": "uploading|processing|ready|failed",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### **File Source Schema**
```json
{
  "source_id": "uuid",
  "name": "string",
  "description": "string",
  "file_size": "integer",
  "duration": "float",
  "width": "integer",
  "height": "integer",
  "fps": "float",
  "codec": "string",
  "audio_codec": "string",
  "bitrate": "integer",
  "file_format": "string",
  "status": "string",
  "access_token": "string",
  "api_endpoint": "string",
  "stream_url": "string",
  "thumbnail_url": "string"
}
```

### **Processing Job Schema**
```json
{
  "job_id": "string",
  "source": "uuid",
  "target_fps": "integer",
  "target_resolution": "string",
  "status": "pending|processing|completed|failed|cancelled",
  "external_job_id": "string",
  "callback_url": "string",
  "access_token": "string",
  "submitted_at": "datetime",
  "started_at": "datetime",
  "completed_at": "datetime",
  "error_message": "string"
}
```

---

## ⚠️ **Error Handling**

### **Standard Error Response**
```json
{
  "error": "Error message description",
  "details": "Additional error details if available"
}
```

### **HTTP Status Codes**
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `405 Method Not Allowed` - HTTP method not supported
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## 🔄 **Integration Flow Examples**

### **FastPublisher Integration Flow**

#### **Step 1: Submit Video for Processing**
```bash
curl -X POST "http://localhost:8000/source-management/api/fastpublisher-submit/{source_id}/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "target_fps=5&target_resolution=640x480"
```

#### **Step 2: Access Video Stream**
```bash
curl "http://localhost:8000/source-management/api/fastpublisher-video/{source_id}/" \
  -H "Range: bytes=0-1048575" \
  --output video_chunk.mp4
```

#### **Step 3: Send Results Back**
```bash
curl -X POST "http://localhost:8000/source-management/api/processing-callback/{access_token}/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "ext-job-123",
    "status": "completed",
    "message": "Processing completed successfully"
  }'
```

### **User Workflow (Authenticated)**

#### **Step 1: Upload Video**
```bash
# Upload video file via web interface
POST /source-management/add/
```

#### **Step 2: Submit for Processing**
```bash
curl -X POST "http://localhost:8000/source-management/api/process-video/{source_id}/" \
  -H "Cookie: sessionid=your_session_id" \
  -d "target_fps=3&target_resolution=320x240"
```

#### **Step 3: Check Status**
```bash
curl "http://localhost:8000/source-management/api/processing-status/{job_id}/" \
  -H "Cookie: sessionid=your_session_id"
```

---

## 🧪 **Testing**

### **Test FastPublisher Endpoints (Unauthenticated)**
```bash
# Test video submission
curl -X POST "http://localhost:8000/source-management/api/fastpublisher-submit/{valid_source_id}/" \
  -d "target_fps=3&target_resolution=320x240"

# Test video streaming
curl -I "http://localhost:8000/source-management/api/fastpublisher-video/{valid_source_id}/"

# Test metadata access
curl "http://localhost:8000/source-management/api/fastpublisher-metadata/{valid_source_id}/"
```

### **Test Authenticated Endpoints**
```bash
# First, get a session cookie by logging in via web interface
# Then use the session cookie for authenticated requests

curl "http://localhost:8000/source-management/api/video/{access_token}/" \
  -H "Cookie: sessionid=your_session_id"
```

---

## 📝 **Notes**

1. **Video Status**: Only videos with status `'ready'` can be processed
2. **FPS Limits**: `target_fps` must be between 1-5 for FastPublisher integration
3. **Resolution Format**: `target_resolution` must be in format "widthxheight" (e.g., "640x480")
4. **File Formats**: Supports MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
5. **Streaming**: Video streaming supports HTTP Range requests for efficient processing
6. **Authentication**: FastPublisher endpoints are intentionally unauthenticated for seamless integration

---

## 🆘 **Troubleshooting**

### **Common Issues**

1. **Video Not Ready**: Ensure video status is `'ready'` before processing
2. **Invalid Parameters**: Check `target_fps` (1-5) and `target_resolution` format
3. **Stream Access**: Verify source_id exists and video file is accessible
4. **Callback Errors**: Ensure access_token is valid and callback URL is correct
5. **Authentication Errors**: Use session cookies for authenticated endpoints

### **Debug Endpoints**

- **Health Check**: `/source-management/api/fastpublisher-status/{source_id}/`
- **Metadata**: `/source-management/api/fastpublisher-metadata/{source_id}/`
- **Processing Jobs**: `/source-management/api/processing-jobs/{source_id}/`

This API provides comprehensive video source management with seamless FastPublisher integration for video processing and Kafka publishing.
