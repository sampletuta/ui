# Face Search Service

A comprehensive face similarity search service that allows users to upload images, detect faces, and search for similar faces using Milvus vector database and InsightFace face recognition.

## Features

- **Image Upload**: Users can upload images containing faces
- **Face Detection**: Automatic face detection using InsightFace
- **Face Embedding**: Generation of 512-dimensional face embeddings
- **Vector Search**: Similarity search using Milvus vector database
- **Top 5 Results**: Returns the top 5 most similar faces by default
- **Configurable Parameters**: Adjustable confidence threshold and result count
- **Rich Results**: Detailed information about matched targets and photos
- **Modern UI**: Clean, responsive interface with Bootstrap styling

## Architecture

The face search service consists of three main components:

### 1. Face Detection Service (`face_ai/services/face_detection.py`)
- Uses InsightFace for face detection and recognition
- Generates normalized face embeddings
- Supports multiple face detection in single images
- Provides age and gender estimation

### 2. Milvus Service (`face_ai/services/milvus_service.py`)
- Manages connection to Milvus vector database
- Handles collection creation and management
- Performs vector similarity searches
- Supports configurable search parameters

### 3. Face Search Service (`face_ai/services/face_search_service.py`)
- Integrates face detection and Milvus search
- Handles image processing and temporary file management
- Enriches search results with target information
- Provides comprehensive search statistics

## Installation & Setup

### Prerequisites

1. **Django Project**: Ensure your Django project is properly configured
2. **Milvus Database**: Milvus server running on localhost:19530 (default)
3. **Python Dependencies**: Install required packages from `requirements.txt`
4. **InsightFace Models**: Models will be automatically downloaded on first use

### Configuration

The service uses Django settings for configuration. Add these to your `settings.py`:

```python
# Milvus Configuration
MILVUS_CONFIG = {
    'HOST': 'localhost',
    'PORT': 19530,
    'COLLECTION_NAME': 'watchlist',
    'DIMENSION': 512,
    'METRIC_TYPE': 'COSINE',
    'INDEX_TYPE': 'IVF_FLAT',
    'AUTO_CREATE_COLLECTION': True,
    'AUTO_LOAD_COLLECTION': True,
}
```

## Usage

### Web Interface

1. Navigate to the Face Search page (`/milvus_search/`)
2. Upload an image containing a face
3. Configure search parameters:
   - **Number of Results**: 1-20 (default: 5)
   - **Confidence Threshold**: 0.0-1.0 (default: 0.6)
4. Click "Search for Similar Faces"
5. View results with similarity scores and target information

### API Usage

```python
from face_ai.services.face_search_service import FaceSearchService

# Initialize service
face_search_service = FaceSearchService()

# Perform face search
result = face_search_service.search_faces_in_image(
    image_file, 
    top_k=5, 
    confidence_threshold=0.6
)

# Check results
if result['success']:
    print(f"Found {result['total_results']} similar faces")
    for face in result['results']:
        print(f"Target: {face['target']['name']}, Score: {face['similarity_score']}")
```

## Search Process

1. **Image Upload**: User uploads image file
2. **Face Detection**: InsightFace detects faces in the image
3. **Embedding Generation**: Face embeddings are generated for detected faces
4. **Vector Search**: Milvus performs similarity search using the embedding
5. **Result Enrichment**: Raw results are enriched with target and photo information
6. **Display**: Results are displayed with similarity scores and metadata

## Result Format

Search results include:

- **Similarity Score**: Cosine similarity between query and result faces
- **Target Information**: Name, gender, age, case association
- **Photo Information**: Image URL, upload timestamp
- **Metadata**: Search parameters and statistics

## Performance Considerations

- **Face Detection**: Uses CPU-based InsightFace models (GPU acceleration available)
- **Vector Search**: Milvus provides fast similarity search with configurable indexes
- **Image Processing**: Temporary files are automatically cleaned up
- **Database Queries**: Optimized queries with proper indexing

## Error Handling

The service includes comprehensive error handling:

- **Face Detection Errors**: No faces found, detection failures
- **Embedding Generation Errors**: Model loading issues, processing failures
- **Milvus Connection Errors**: Database connectivity issues
- **File Processing Errors**: Upload failures, temporary file issues

## Testing

Run the test suite to verify service functionality:

```bash
python3 test_face_search.py
```

This will test:
- Service initialization
- Face detection capabilities
- Milvus connectivity
- Search functionality

## Troubleshooting

### Common Issues

1. **Milvus Connection Failed**
   - Ensure Milvus server is running
   - Check host/port configuration
   - Verify network connectivity

2. **Face Detection Fails**
   - Check InsightFace model installation
   - Verify image format and quality
   - Ensure sufficient system resources

3. **No Search Results**
   - Lower confidence threshold
   - Check if watchlist has face embeddings
   - Verify image contains clear, detectable faces

### Debug Mode

Enable debug logging in Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'face_ai.services': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Future Enhancements

- **Batch Processing**: Support for multiple image uploads
- **Advanced Filtering**: Filter by case, date range, or target attributes
- **Real-time Search**: Live search with video streams
- **Performance Optimization**: GPU acceleration and caching
- **API Endpoints**: RESTful API for external integrations

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive error handling
3. Include unit tests for new functionality
4. Update documentation for any changes
5. Test with various image formats and qualities

## License

This service is part of the larger UI project and follows the same licensing terms.


