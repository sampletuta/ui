# Downstream Service Integration

This document explains how to configure and use the downstream service integration in your video player application.

## Overview

The video player now automatically sends stream information to downstream services when:
- A video is viewed in the detail view
- External streams are played (RTSP, RTMP, HLS, HTTP)
- Real-time streaming events occur
- Analytics data is collected

## Configuration

### 1. Environment Variables

Add these to your `.env` file or environment:

```bash
# Enable downstream service
DOWNSTREAM_SERVICE_ENABLED=true

# Service URL
DOWNSTREAM_SERVICE_URL=https://your-service.com/api/streams

# API Token
DOWNSTREAM_SERVICE_TOKEN=your-secret-token

# Timeout and retry settings
DOWNSTREAM_SERVICE_TIMEOUT=10
DOWNSTREAM_SERVICE_RETRY_ATTEMPTS=3
```

### 2. Django Settings

The configuration is automatically loaded from environment variables in `backend/settings.py`:

```python
DOWNSTREAM_SERVICE = {
    'ENABLED': os.environ.get('DOWNSTREAM_SERVICE_ENABLED', 'false').lower() == 'true',
    'URL': os.environ.get('DOWNSTREAM_SERVICE_URL', 'https://your-service.com/api/streams'),
    'API_TOKEN': os.environ.get('DOWNSTREAM_SERVICE_TOKEN', ''),
    'TIMEOUT': int(os.environ.get('DOWNSTREAM_SERVICE_TIMEOUT', 10)),
    'RETRY_ATTEMPTS': int(os.environ.get('DOWNSTREAM_SERVICE_RETRY_ATTEMPTS', 3)),
    'BATCH_SIZE': int(os.environ.get('DOWNSTREAM_SERVICE_BATCH_SIZE', 100)),
    'ENABLE_ANALYTICS': os.environ.get('DOWNSTREAM_SERVICE_ENABLE_ANALYTICS', 'true').lower() == 'true',
    'ENABLE_EVENTS': os.environ.get('DOWNSTREAM_SERVICE_ENABLE_EVENTS', 'true').lower() == 'true',
}
```

## Data Sent to Downstream Service

### 1. Video Detail View

When a user views a video detail page:

```json
{
    "video_id": "123",
    "title": "Sample Video",
    "description": "Video description",
    "duration": 120,
    "file_path": "/media/videos/sample.mp4",
    "file_size": 1048576,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "stream_type": "video_file",
    "status": "active",
    "metadata": {
        "format": "mp4",
        "resolution": "1920x1080",
        "fps": 30,
        "bitrate": 5000,
        "codec": "h264"
    },
    "chapters": [
        {
            "title": "Chapter 1",
            "start_time": 0,
            "end_time": 60,
            "description": "First chapter"
        }
    ]
}
```

### 2. External Streams

When playing external URLs (RTSP, RTMP, HLS, HTTP):

```json
{
    "stream_id": "external_1234",
    "name": "Live Camera Feed",
    "url": "rtsp://camera.example.com/stream",
    "stream_type": "rtsp_stream",
    "status": "active",
    "initial_seek": 0,
    "timestamp": 1704067200.0,
    "metadata": {
        "protocol": "rtsp",
        "domain": "camera.example.com",
        "path": "camera.example.com/stream",
        "is_live": true,
        "is_video_file": false
    }
}
```

### 3. Streaming Events

Real-time events during playback:

```json
{
    "event_type": "stream_start",
    "timestamp": 1704067200.0,
    "stream_data": {...},
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.100",
    "session_id": "session_123"
}
```

### 4. Analytics Data

Performance and engagement metrics:

```json
{
    "stream_id": "video_123",
    "timestamp": 1704067200.0,
    "analytics_type": "stream_performance",
    "data": {
        "view_duration": 120,
        "buffering_events": 2,
        "quality_changes": 1,
        "user_engagement": "high"
    }
}
```

## API Endpoints

### 1. Video Detail View
- **URL**: `/video-player/video/<video_id>/`
- **Method**: GET
- **Action**: Automatically sends video metadata to downstream service

### 2. External Stream Playback
- **URL**: `/video-player/play-from-url/?url=<stream_url>&name=<stream_name>`
- **Method**: GET
- **Action**: Automatically sends stream metadata to downstream service

## Error Handling

The integration includes robust error handling:

- **Retry Logic**: Automatic retries with exponential backoff
- **Graceful Degradation**: Failures don't break video playback
- **Logging**: All errors are logged for debugging
- **Timeout Protection**: Configurable request timeouts

## Security

- **API Token Authentication**: Bearer token authentication
- **HTTPS Support**: Secure communication with downstream services
- **Input Validation**: All data is validated before sending
- **Rate Limiting**: Configurable batch sizes and retry limits

## Monitoring

### 1. Console Logs
Check your Django console for messages like:
```
Successfully sent stream data for video 123 to downstream service
Successfully sent external stream data for Live Camera to downstream service
```

### 2. Error Logs
Failed requests are logged with details:
```
Failed to send to downstream service: Connection timeout
Downstream service returned status 500: Internal server error
```

## Example Downstream Service

Here's a simple example of what your downstream service might look like:

```python
# Flask example
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/streams', methods=['POST'])
def receive_stream_data():
    data = request.json
    
    # Process the stream data
    print(f"Received stream data: {data}")
    
    # Store in database, send to analytics, etc.
    process_stream_data(data)
    
    return jsonify({'status': 'success', 'message': 'Data received'})

def process_stream_data(data):
    # Your processing logic here
    pass

if __name__ == '__main__':
    app.run(debug=True)
```

## Troubleshooting

### 1. Service Not Receiving Data
- Check `DOWNSTREAM_SERVICE_ENABLED=true`
- Verify `DOWNSTREAM_SERVICE_URL` is correct
- Check network connectivity
- Review console logs for errors

### 2. Authentication Failures
- Verify `DOWNSTREAM_SERVICE_TOKEN` is correct
- Check if token has expired
- Ensure downstream service accepts Bearer tokens

### 3. Timeout Issues
- Increase `DOWNSTREAM_SERVICE_TIMEOUT` value
- Check downstream service performance
- Review network latency

### 4. Data Format Issues
- Verify downstream service accepts JSON
- Check Content-Type headers
- Validate data structure matches expectations

## Performance Considerations

- **Async Processing**: Consider using Celery for heavy processing
- **Batch Processing**: Use `BATCH_SIZE` to group multiple events
- **Caching**: Cache frequently accessed data
- **Monitoring**: Track response times and success rates

## Support

For issues or questions about the downstream service integration:
1. Check the console logs for error messages
2. Verify your configuration settings
3. Test with a simple downstream service first
4. Review the network connectivity and firewall settings
