# ClearSight - Video Management & Face Detection

## Project Overview

This is a Django-based ClearSight that separates video management from search functionality, integrates with external face detection services, and provides advanced search capabilities with geospatial filtering and Milvus vector search integration.

## 🚀 Quick Start

To get started with this application:

```bash
# Clone the repository
git clone <repository-url>
cd ui

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python3 manage.py migrate

# Create superuser
python3 manage.py createsuperuser

# Start the development server
python3 manage.py runserver

# Access the application
# Open http://localhost:8000 in your browser
```

## Key Features

### 🔍 Advanced Search System
- **Quick Search**: Simple text-based search
- **Advanced Search**: Date filtering, geospatial search with Folium maps, confidence thresholds
- **Milvus Search**: Vector similarity search integration
- **Search History**: Track and review previous searches
- **Video Face Search**: Search within video content

### 📹 Source Management (New App)
- **Video Source Management**: Handle cameras, files, and streams
- **Video Upload System**: Support for large file uploads with chunking
- **External Service Integration**: Send videos to face detection service via HTTP POST
- **Processing Job Tracking**: Monitor face detection and processing status
- **Metadata Generation**: Automatic video metadata extraction

### 🎯 Target Management
- **Target Watchlist**: Add and manage surveillance targets
- **Photo Management**: Upload and manage target photos
- **Case Association**: Link targets to specific cases

### 🔐 User Management
- **Custom User Model**: Email-based authentication
- **Role-based Access**: Different user roles and permissions
- **Notifications**: Real-time notifications using django-notifications-hq

## Architecture

### Core Apps

#### `backendapp` (Main Application)
- **Models**: CustomUser, Case, Targets_watchlist, TargetPhoto, SearchQuery, SearchResult
- **Views**: Authentication, target management, search functionality
- **Forms**: User forms, search forms, target forms
- **Templates**: Main UI templates with Bootstrap 5

#### `source_management` (New Video Management App)
- **Models**: VideoSource, VideoFile, VideoChunk, ProcessingJob
- **Views**: CRUD operations, file upload, external service integration
- **Forms**: Source forms, upload forms, job forms
- **Templates**: Video management interface

#### `video_player` (Video Streaming App)
- **Models**: Video, Chapter
- **Views**: Video streaming and playback
- **Templates**: Video player interface

### External Service Integration

#### Face Detection Service
- **HTTP POST Integration**: Send video files to external service
- **Callback System**: Receive detection results via webhook
- **Payload Structure**: Comprehensive JSON with video metadata and callback URL
- **Status Tracking**: Monitor processing jobs and results

#### Milvus Vector Database (Planned)
- **Vector Storage**: Store face embeddings for similarity search
- **Collection Management**: Organize vectors by search queries
- **Distance Metrics**: Calculate similarity scores

## Source Management App Details

### Purpose
The Source Management app was created to **separate video uploads from search functionality** as requested. It handles:

1. **Video Source Management**
   - Camera sources (IP cameras, RTSP streams)
   - File sources (uploaded video files)
   - Stream sources (live video streams)

2. **Video File Processing**
   - Large file uploads with chunking support
   - Automatic metadata extraction
   - Integration with external face detection service

3. **Processing Job Tracking**
   - Monitor face detection jobs
   - Track processing status
   - Handle callback results

### Key Features

#### Video Sources
- **Dynamic Forms**: Different forms for camera vs file sources
- **Metadata Generation**: Automatic extraction of video properties
- **Source Types**: Camera, File, Stream with specific fields for each

#### Video Files
- **Upload System**: Support for large files with progress tracking
- **Face Detection Integration**: Send videos to external service
- **Status Tracking**: Monitor processing and detection status
- **Metadata Storage**: Store video properties and detection results

#### Processing Jobs
- **Job Creation**: Automatic job creation for face detection
- **Status Updates**: Real-time status updates via callbacks
- **Result Storage**: Store detection results and metadata

### API Endpoints

#### Face Detection Integration
```python
# Send video to face detection service
POST /source-management/api/video/{video_id}/send-to-detection/

# Receive detection results
POST /source-management/api/face-detection-callback/
```

#### Video Management
```python
# Get video metadata
GET /source-management/api/video/{video_id}/metadata/

# Get source metadata
GET /source-management/api/source/{source_id}/metadata/

# Get processing status
GET /source-management/api/job/{job_id}/status/
```

## Search System Architecture

### Search Types

#### Quick Search
- Simple text-based search
- Target name, description, case filtering
- Fast results with basic filtering

#### Advanced Search
- **Date Filtering**: Start/end date ranges
- **Geospatial Search**: Latitude/longitude with radius
- **Confidence Threshold**: Filter by detection confidence
- **Target Filtering**: Specific target selection
- **Interactive Maps**: Folium-based location selection

#### Milvus Search
- **Vector Similarity**: Face embedding comparison
- **Collection Management**: Organize vectors by search context
- **Distance Metrics**: Calculate similarity scores
- **Partition Support**: Separate vectors by search queries

### Search Results
- **Interactive Maps**: Display results on Folium maps
- **Confidence Scores**: Show detection confidence
- **Source Information**: Link to original video sources
- **Metadata Display**: Show detection timestamps and locations

## Installation & Setup

### Prerequisites
```bash
# Install system dependencies
sudo apt-get install libspatialite7 spatialite-bin

# Install Python dependencies
pip install -r requirements.txt
```

### Database Setup
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Configuration
```python
# settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Face Detection Service
FACE_DETECTION_SERVICE_URL = 'http://your-face-detection-service.com/api'
BASE_URL = 'http://localhost:8001'

# File Upload Settings
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

# Milvus Configuration
MILVUS_CONFIG = {
    'host': 'localhost',
    'port': 19530,
    'collection_name': 'face_embeddings',
}
```

## Usage

### Source Management Workflow

1. **Add Video Source**
   - Navigate to Source Management → Video Sources
   - Choose source type (Camera, File, Stream)
   - Fill in source-specific details
   - Save source configuration

2. **Upload Video File**
   - Go to Source Management → Upload Video
   - Select video file or drag & drop
   - Add metadata (title, description, tags)
   - Choose processing options (face detection)
   - Upload and monitor progress

3. **Monitor Processing**
   - View processing jobs in Source Management → Dashboard
   - Track face detection status
   - Review detection results and metadata

### Search Workflow

1. **Quick Search**
   - Use top navbar search for simple queries
   - Filter by target name, description, or case

2. **Advanced Search**
   - Navigate to Search → Advanced Search
   - Set date ranges, location, confidence threshold
   - Select specific targets
   - Use interactive map for location selection
   - Execute search and view results

3. **Milvus Search**
   - Go to Search → Milvus Search
   - Upload reference face image
   - Set similarity threshold
   - Search vector database for matches

## API Documentation

### Face Detection Service Integration

#### Send Video for Detection
```bash
curl -X POST http://localhost:8001/source-management/api/video/1/send-to-detection/ \
  -H "Content-Type: application/json" \
  -d '{"enable_face_detection": true}'
```

#### Callback Endpoint
```bash
curl -X POST http://localhost:8001/source-management/api/face-detection-callback/ \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": 1,
    "job_id": "job_123",
    "status": "completed",
    "detections": [...],
    "metadata": {...}
  }'
```

## Development

### Project Structure
```
ui/
├── backend/                 # Django project settings
├── backendapp/             # Main application
│   ├── models.py          # Core models
│   ├── views.py           # Main views
│   ├── forms.py           # Forms
│   └── templates/         # Main templates
├── source_management/     # Video management app
│   ├── models.py          # Video models
│   ├── views.py           # Video views
│   ├── forms.py           # Video forms
│   └── templates/         # Video templates
├── video_player/          # Video streaming app
└── manage.py
```

### Key Models

#### Source Management Models
- **VideoSource**: Camera, file, or stream sources
- **VideoFile**: Uploaded video files with metadata
- **VideoChunk**: Large file chunking support
- **ProcessingJob**: Face detection job tracking

#### Search Models
- **SearchQuery**: Advanced search parameters
- **SearchResult**: Search results with metadata
- **SearchHistory**: Search history tracking

## Future Enhancements

### Planned Features
- **Real-time Video Processing**: Live face detection
- **Advanced Analytics**: Detection statistics and trends
- **Multi-tenant Support**: Organization-based access
- **API Rate Limiting**: Protect against abuse
- **Video Compression**: Automatic video optimization
- **Batch Processing**: Bulk video upload and processing

### Milvus Integration
- **Vector Indexing**: Efficient similarity search
- **Collection Management**: Organize embeddings
- **Partition Strategy**: Optimize search performance
- **Distance Metrics**: Multiple similarity algorithms

## Troubleshooting

### Common Issues

#### Migration Errors
```bash
# Reset migrations if needed
python manage.py migrate --fake-initial
```

#### File Upload Issues
- Check `MEDIA_ROOT` permissions
- Verify `MAX_UPLOAD_SIZE` settings
- Ensure chunked upload is working

#### External Service Integration
- Verify `FACE_DETECTION_SERVICE_URL` is accessible
- Check callback endpoint is publicly reachable
- Monitor job status and error logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the troubleshooting section

---

**Note**: This system is designed for surveillance and security applications. Ensure compliance with local privacy laws and regulations when deploying in production environments. 