# Data Ingestion Service Configuration

This document explains how to configure the source management system to notify the data ingestion service about new sources.

## Configuration

Add the following configuration to your Django `settings.py`:

```python
# Data Ingestion Service Configuration
DATA_INGESTION_SERVICE = {
    'BASE_URL': 'http://localhost:8001',  # URL of your data ingestion service
    'NOTIFY_ENDPOINT': '/api/v1/notify-new-source',  # Endpoint to notify about new sources
    'HEALTH_ENDPOINT': '/api/v1/health',  # Health check endpoint
    'API_KEY': 'your-api-key-here',  # Optional API key for authentication
    'TIMEOUT': 30,  # Request timeout in seconds
}
```

## How It Works

1. **Source Creation**: When a new file source is created, the system automatically notifies the data ingestion service
2. **Notification**: A POST request is sent to the data ingestion service with source information
3. **Non-blocking**: The notification happens in the background and doesn't block source creation
4. **Error Handling**: If notification fails, the source is still created successfully

## Notification Payload

The data ingestion service receives this JSON payload:

```json
{
  "source_id": "uuid-1234-5678-9abc-def0",
  "name": "Security Footage",
  "description": "Video from security camera",
  "location": "Building A, Floor 1",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "tags": ["security", "camera", "footage"],
  "created_by": "user@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "file_info": {
    "filename": "videos/security.mp4",
    "file_size": 10485760,
    "file_format": "mp4"
  },
  "access_info": {
    "access_token": "abc123...",
    "api_endpoint": "http://localhost:8000/source-management/api/video/abc123/",
    "stream_url": "http://localhost:8000/source-management/api/video/abc123/stream/"
  }
}
```

## Expected Response

The data ingestion service should respond with:

- **Status 200 or 202**: Success (source notification received)
- **Status 4xx**: Client error (bad request, validation failed)
- **Status 5xx**: Server error (service unavailable)

## Headers

The request includes these headers:

```
Content-Type: application/json
X-Source-ID: uuid-1234-5678-9abc-def0
Authorization: Bearer your-api-key-here  # If API_KEY is configured
```

## Error Handling

- **Timeout**: If the request times out, it's logged as a warning
- **Connection Error**: If the service is unreachable, it's logged as a warning
- **Non-blocking**: All errors are logged but don't prevent source creation

## Health Check

You can check if the data ingestion service is healthy:

```python
from source_management.services import DataIngestionService

service = DataIngestionService()
health = service.health()

if health['ok']:
    print("Data ingestion service is healthy")
else:
    print(f"Data ingestion service error: {health.get('error')}")
```

## Testing

To test the integration:

1. Create a new file source through the web interface
2. Check the logs for notification messages
3. Verify the source status changes to 'ready'
4. Check the `ingestion_notified` and `ingestion_response` fields

## Monitoring

Monitor these fields in the FileSource model:

- `ingestion_notified`: Boolean indicating if notification was sent
- `ingestion_notified_at`: Timestamp when notification was sent
- `ingestion_response`: Response from the data ingestion service

## Troubleshooting

### Common Issues

1. **Service Unreachable**
   - Check if the data ingestion service is running
   - Verify the BASE_URL configuration
   - Check network connectivity

2. **Authentication Failed**
   - Verify the API_KEY configuration
   - Check if the service requires different authentication

3. **Timeout Errors**
   - Increase the TIMEOUT value
   - Check if the service is responding slowly

4. **Payload Validation**
   - Ensure the service accepts the JSON payload format
   - Check if required fields are missing

### Debug Mode

Enable debug logging to see detailed notification information:

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
        'source_management.services': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```


