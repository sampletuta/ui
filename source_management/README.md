# Enhanced File Source Management System

This system provides a comprehensive file source management solution where users can upload video files, automatically extract metadata, and generate access links for downstream models.

## Features

### 1. Automatic Video Processing
- **Upload**: Users can upload video files (MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V)
- **Processing**: Videos are automatically processed to extract metadata using ffprobe
- **Status Tracking**: Real-time status updates (uploading → processing → ready/failed)

### 2. Comprehensive Video Metadata
The system automatically extracts:
- **Basic Info**: Duration, file size, format
- **Video Properties**: Resolution, frame rate, bitrate, codec
- **Audio Properties**: Audio codec, channels, sample rate
- **Processing Info**: Start/completion times, error messages

### 3. API Access for Downstream Models
Each processed video generates:
- **Access Token**: Unique identifier for API access
- **API Endpoint**: `http://localhost:8000/api/video/{access_token}/`
- **Stream URL**: `http://localhost:8000/stream/{access_token}/`
- **Download URL**: `http://localhost:8000/api/video/{access_token}/download/`
- **Metadata URL**: `http://localhost:8000/api/video/{access_token}/metadata/`

## API Endpoints

### Video Access (No Authentication Required)
```
GET /api/video/{access_token}/
GET /api/video/{access_token}/metadata/
GET /api/video/{access_token}/download/
GET /stream/{access_token}/
```

### Example API Response
```json
{
  "id": 1,
  "source_id": "file_001",
  "name": "Security Footage",
  "description": "Video from security camera",
  "status": "ready",
  "file_info": {
    "filename": "videos/file_001/security.mp4",
    "format": "mp4",
    "size": 10485760,
    "duration": 120.5,
    "resolution": "1920x1080",
    "fps": 30.0,
    "codec": "h264",
    "audio_codec": "aac"
  },
  "api_links": {
    "api_endpoint": "http://localhost:8000/api/video/abc123/",
    "stream_url": "http://localhost:8000/stream/abc123/",
    "access_token": "abc123",
    "metadata_url": "http://localhost:8000/api/video/abc123/metadata/",
    "download_url": "http://localhost:8000/api/video/abc123/download/"
  }
}
```

## Usage for Downstream Models

### 1. Access Video via Token
```python
import requests

# Get video information
response = requests.get('http://localhost:8000/api/video/abc123/')
video_data = response.json()

# Access video metadata
metadata_response = requests.get('http://localhost:8000/api/video/abc123/metadata/')
metadata = metadata_response.json()

# Download video file
download_response = requests.get('http://localhost:8000/api/video/abc123/download/')
with open('video.mp4', 'wb') as f:
    f.write(download_response.content)
```

### 2. Stream Video
```html
<video controls>
    <source src="http://localhost:8000/stream/abc123/" type="video/mp4">
    Your browser does not support the video tag.
</video>
```

## File Upload Process

1. **User Uploads Video**: Through the web interface
2. **Auto-Generation**: Source ID and name are auto-generated if not provided
3. **Async Processing**: Video processing starts in background thread
4. **Metadata Extraction**: Using ffprobe to extract video information
5. **Link Generation**: API endpoints are generated automatically
6. **Status Update**: Status changes to 'ready' when complete

## Configuration

### Required Dependencies
- **ffprobe**: For video metadata extraction
- **Django**: Web framework
- **Pillow**: Image processing (optional)

### Settings
Add to your Django settings:
```python
BASE_URL = 'http://localhost:8000'  # Your domain
MEDIA_ROOT = '/path/to/media/files'
MEDIA_URL = '/media/'
```

## Testing

### Test Video Processing
```bash
python manage.py test_video_processing --file-path /path/to/video.mp4
```

### Manual Testing
1. Go to `/source-management/add/?type=file`
2. Upload a video file
3. Check the processing status
4. View the generated API links

## Error Handling

- **File Size**: Maximum 100MB
- **File Format**: Only supported video formats
- **Processing Errors**: Stored in `processing_error` field
- **Status Tracking**: Clear status indicators (uploading, processing, ready, failed)

## Security

- **Access Tokens**: Cryptographically secure random tokens
- **No Authentication**: API endpoints designed for downstream model access
- **File Validation**: Strict file type and size validation
- **Error Isolation**: Processing errors don't affect system stability

## Future Enhancements

- **Thumbnail Generation**: Automatic video thumbnails
- **Scene Analysis**: AI-powered scene detection
- **Batch Processing**: Multiple file upload support
- **Cloud Storage**: Integration with cloud storage providers
- **Video Transcoding**: Automatic format conversion 