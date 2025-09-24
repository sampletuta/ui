# Source Management Django App

## Overview

The `source_management` Django app is a comprehensive video source management system that handles multiple types of video sources including file uploads, camera streams, and live streams. It provides a unified interface for managing video sources, processing them through external microservices, and integrating with downstream AI/ML systems.

## Features

### Core Functionality
- **Multi-source Support**: Handles three types of video sources:
  - **File Sources**: Uploaded video files (MP4, AVI, MOV, etc.)
  - **Camera Sources**: IP cameras, USB cameras, PTZ cameras
  - **Stream Sources**: RTSP, RTMP, HTTP streams, HLS, DASH

- **Video Processing**: Integration with external data ingestion services
- **Stream Processing**: Real-time stream management and control
- **API Access**: RESTful APIs for programmatic access
- **User Management**: Authentication and authorization
- **Notifications**: Real-time notifications for processing events

### Advanced Features
- **Metadata Extraction**: Automatic video metadata extraction using FFprobe
- **Chunked Uploads**: Support for large file uploads
- **Stream Integration**: Real-time stream processing with external services
- **Topic Management**: MQTT topic generation for downstream systems
- **Health Monitoring**: Service health checks and status monitoring
- **Source Activation**: Bulk activation/deactivation of sources

## Architecture

### Models

#### BaseSource (Abstract)
Base model for all video sources with common fields:
- `source_id`: UUID primary key
- `name`: Display name
- `description`: Optional description
- `location`: Physical location
- `latitude`/`longitude`: GPS coordinates
- `tags`: JSON array for categorization
- `created_at`/`updated_at`: Timestamps
- `created_by`: User foreign key

#### FileSource
Manages uploaded video files:
- File upload and storage
- Metadata extraction (duration, resolution, codec, etc.)
- Processing status tracking
- Access token generation
- API endpoint generation
- Data ingestion service integration

#### CameraSource
Manages IP/USB cameras:
- Camera configuration (IP, port, protocol)
- Authentication credentials
- Video/audio parameters
- Network settings
- Stream processor integration
- Topic name generation for downstream systems

#### StreamSource
Manages live video streams:
- Stream URL and protocol
- Quality and performance settings
- Authentication and headers
- Stream processor integration
- Topic name generation for downstream systems

#### VideoProcessingJob
Tracks video processing jobs:
- External service integration
- Job status tracking
- Processing parameters
- Error handling

### Views Structure

The app uses a modular view structure organized by functionality:

```
views/
├── __init__.py
├── api_views.py              # REST API endpoints
├── callback_views.py          # External service callbacks
├── decorators.py             # Custom decorators
├── fastpublisher_views.py    # FastPublisher integration
├── health_views.py           # Health check endpoints
├── source_activation_views.py # Source activation/deactivation
├── source_crud_views.py      # CRUD operations
├── source_list_views.py      # Source listing
├── stream_control_views.py   # Stream management
├── utils.py                  # Utility functions
└── video_processing_views.py # Video processing
```

### Forms

#### CameraSourceForm
- Camera configuration fields
- Validation for IP addresses, ports, FPS
- Topic suffix validation
- JSON configuration validation

#### FileSourceForm
- File upload handling
- Chunked upload support
- File size and format validation
- Metadata extraction

#### StreamSourceForm
- Stream URL validation
- Authentication fields
- Quality and performance settings
- JSON parameter validation

## API Endpoints

### Public API (No Authentication Required)
- `GET /api/public/video/<access_token>/` - Video access
- `GET /api/public/video/<access_token>/metadata/` - Video metadata
- `GET /api/public/video/<access_token>/download/` - Video download
- `GET /api/public/video/<access_token>/stream/` - Video streaming

### Authenticated API
- `GET /api/source/<source_id>/` - Source metadata
- `GET /api/video/<access_token>/` - Video access
- `GET /api/video/<access_token>/metadata/` - Video metadata
- `GET /api/video/<access_token>/download/` - Video download
- `GET /api/video/<access_token>/stream/` - Video streaming

### Video Processing API
- `POST /api/process-video/<source_id>/` - Submit video for processing
- `GET /api/processing-status/<job_id>/` - Get processing status
- `POST /api/cancel-processing/<job_id>/` - Cancel processing job
- `GET /api/processing-jobs/<source_id>/` - List processing jobs

### Stream Control API
- `POST /api/stream/<source_id>/create/` - Create stream
- `POST /api/stream/<source_id>/submit/` - Submit stream
- `POST /api/stream/<source_id>/submit-comprehensive/` - Comprehensive stream submission
- `POST /api/stream/<source_id>/start/` - Start stream
- `POST /api/stream/<source_id>/stop/` - Stop stream
- `GET /api/stream/<source_id>/status/` - Get stream status

### Health Check API
- `GET /api/data-ingestion/health/` - Data ingestion service health
- `GET /api/data-ingestion/status/<source_id>/` - Source processing status

### Source Activation API
- `POST /api/source/<source_id>/activate/` - Activate source
- `POST /api/source/<source_id>/deactivate/` - Deactivate source
- `POST /api/source/<source_id>/toggle/` - Toggle source activation
- `POST /api/source/<source_type>/bulk-activation/` - Bulk activation

### Notification API
- `POST /api/notifications/create/` - Create notification for external apps

## Microservice Integration

### Data Ingestion Service

The source management app integrates with a **Data Ingestion Service** for video processing:

**Service Details:**
- **Base URL**: `http://localhost:8001` (configurable)
- **Purpose**: Processes uploaded videos for AI/ML analysis
- **Integration**: Automatic notification when videos are ready

**API Endpoints:**
- `POST /api/sources` - Submit video for processing
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/sources/{source_id}/status` - Get source processing status
- `GET /health` - Health check

**Integration Flow:**
1. User uploads video file
2. FileSource processes video and extracts metadata
3. System automatically notifies Data Ingestion Service
4. Service processes video and returns results
5. Status updates are tracked via VideoProcessingJob model

**Configuration:**
```python
DATA_INGESTION_SERVICE = {
    'BASE_URL': 'http://localhost:8001',
    'NOTIFY_ENDPOINT': '/api/sources',
    'HEALTH_ENDPOINT': '/health',
    'STATUS_ENDPOINT': '/api/sources/{source_id}/status',
    'API_KEY': 'your-api-key',
    'TIMEOUT': 30
}
```

### Stream Processor Service

The app integrates with a **Stream Processor Service** for real-time stream management:

**Service Details:**
- **Base URL**: `http://localhost:8002` (configurable)
- **Purpose**: Manages real-time video streams from cameras and live sources
- **Integration**: Automatic stream registration and control

**API Endpoints:**
- `POST /api/external/streams` - Register/create stream
- `PUT /api/external/streams/{stream_id}` - Update stream
- `DELETE /api/external/streams/{stream_id}` - Delete stream
- `PUT /api/external/streams/{stream_id}/start` - Start stream
- `PUT /api/external/streams/{stream_id}/stop` - Stop stream
- `GET /api/external/streams/{stream_id}/status` - Get stream status

**Integration Flow:**
1. User creates CameraSource or StreamSource
2. System generates topic name for downstream systems
3. Stream is automatically registered with Stream Processor Service
4. Service manages stream processing and provides status updates
5. Users can start/stop streams via API

**Configuration:**
```python
STREAM_PROCESSOR_CONFIG = {
    'BASE_URL': 'http://localhost:8002',
    'EXTERNAL_SERVICE_ID': 'django-source-management',
    'TIMEOUT': 30,
    'ENABLED': True
}
```

**Topic Management:**
- Automatic topic name generation for downstream model integration
- Format: `{zone}_camera_{suffix}` or `{zone}_stream_{suffix}`
- Customizable topic suffixes (max 6 characters)
- Clean naming (spaces/special chars replaced with underscores)

### FastPublisher Integration

Alternative video processing service integration:

**Service Details:**
- **Purpose**: Alternative video processing service
- **Integration**: Health monitoring and video submission
- **Endpoints**: `/api/fastpublisher/health/`, `/api/fastpublisher/submit-video/`

## Configuration

### Settings

The app uses several Django settings for configuration:

```python
# Stream Processor Configuration
STREAM_PROCESSOR_CONFIG = {
    'BASE_URL': 'http://localhost:8002',
    'EXTERNAL_SERVICE_ID': 'django-source-management',
    'TIMEOUT': 30,
    'ENABLED': True
}

# Data Ingestion Service Configuration
DATA_INGESTION_SERVICE = {
    'BASE_URL': 'http://localhost:8001',
    'NOTIFY_ENDPOINT': '/api/sources',
    'HEALTH_ENDPOINT': '/health',
    'STATUS_ENDPOINT': '/api/sources/{source_id}/status',
    'API_KEY': 'your-api-key',
    'TIMEOUT': 30
}

# File Upload Settings
MAX_VIDEO_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
```

### Environment Variables

- `BASE_URL`: Base URL for API endpoints
- `DATA_INGESTION_SERVICE_URL`: Data ingestion service URL
- `STREAM_PROCESSOR_CONFIG`: Stream processor configuration

## Usage Examples

### Creating a Camera Source

```python
from source_management.models import CameraSource

camera = CameraSource.objects.create(
    name="Front Door Camera",
    description="Main entrance camera",
    location="Building A, Floor 1",
    camera_ip="192.168.1.100",
    camera_port=554,
    camera_protocol="rtsp",
    camera_type="ip",
    camera_fps=30,
    camera_resolution_width=1920,
    camera_resolution_height=1080,
    zone="Zone A",
    is_active=True,
    created_by=request.user
)
```

### Creating a File Source

```python
from source_management.models import FileSource

file_source = FileSource.objects.create(
    name="Security Footage",
    description="Uploaded security video",
    location="Building A",
    video_file=uploaded_file,
    created_by=request.user
)

# Process the video to extract metadata
file_source.process_video()
```

### Creating a Stream Source

```python
from source_management.models import StreamSource

stream = StreamSource.objects.create(
    name="Live Stream",
    description="Live video stream",
    location="Building A",
    stream_url="rtsp://192.168.1.100:554/stream",
    stream_protocol="rtsp",
    stream_fps=30.0,
    stream_resolution_width=1920,
    stream_resolution_height=1080,
    zone="Zone A",
    is_active=True,
    created_by=request.user
)
```

### Submitting Video for Processing

```python
from source_management.services import VideoProcessingService

service = VideoProcessingService()
result = service.submit_video_processing(
    file_source=file_source,
    target_fps=5,
    target_resolution="640x480"
)

if result['success']:
    print(f"Job submitted: {result['job_id']}")
else:
    print(f"Error: {result['error']}")
```

### Stream Control Operations

```python
# Start a camera stream
result = camera.start_processor_stream()

# Stop a stream
result = stream.stop_processor_stream()

# Get stream status
status = camera.get_processor_status()
```

## Microservice Communication Patterns

### 1. Video Processing Workflow

```
Django App → Data Ingestion Service → AI/ML Processing → Results
     ↓              ↓                      ↓
File Upload → Video Processing → Analysis Results → Notifications
```

### 2. Stream Processing Workflow

```
Django App → Stream Processor Service → Real-time Processing
     ↓              ↓                         ↓
Camera/Stream → Stream Management → Downstream Systems
```

### 3. Health Monitoring

```
Django App → Health Check APIs → Service Status
     ↓              ↓              ↓
Monitoring → Service Health → Status Updates
```

## Admin Interface

The app provides comprehensive Django admin interfaces for all models:

- **CameraSourceAdmin**: Camera configuration management
- **FileSourceAdmin**: File source management with processing status
- **StreamSourceAdmin**: Stream source configuration
- **VideoProcessingJobAdmin**: Processing job monitoring

## Templates

The app includes responsive Bootstrap-based templates:

- `dashboard.html`: Main dashboard with statistics
- `source_list.html`: Source listing with filtering
- `source_detail.html`: Detailed source view
- `source_form.html`: Source creation/editing forms
- `source_confirm_delete.html`: Deletion confirmation

## Management Commands

### Database Schema Check
```bash
python manage.py check_db_schema
```

### UUID Data Fix
```bash
python manage.py fix_uuid_data --dry-run
python manage.py fix_uuid_data
```

## Security Features

- **Authentication**: Custom decorator for source list access
- **Access Tokens**: Secure token-based video access
- **Input Validation**: Comprehensive form validation
- **File Upload Security**: File type and size validation
- **SQL Injection Protection**: Django ORM usage

## Performance Considerations

- **Query Optimization**: Limited field fetching for large lists
- **Pagination**: Configurable pagination for source lists
- **Caching**: Session-based caching for repeated operations
- **File Streaming**: Range request support for large files
- **Background Processing**: Asynchronous video processing

## Error Handling

- **Graceful Degradation**: Service failures don't break the app
- **Comprehensive Logging**: Detailed logging for debugging
- **User-Friendly Messages**: Clear error messages for users
- **Retry Logic**: Automatic retry for transient failures

## Testing

The app includes comprehensive test coverage:
- Model tests
- View tests
- API endpoint tests
- Integration tests
- Service tests

## Deployment

### Requirements
- Django 4.2+
- Python 3.8+
- FFmpeg/FFprobe for video processing
- External services (Data Ingestion, Stream Processor)

### Database Migrations
```bash
python manage.py makemigrations source_management
python manage.py migrate
```

### Static Files
```bash
python manage.py collectstatic
```

## Contributing

1. Follow Django best practices
2. Add tests for new features
3. Update documentation
4. Use type hints where appropriate
5. Follow the existing code structure

## License

This app is part of the larger Django project and follows the same licensing terms.

## Support

For issues and questions:
1. Check the logs in `logs/django.log`
2. Review the admin interface for data integrity
3. Check external service health endpoints
4. Consult the Django documentation for framework-specific issues