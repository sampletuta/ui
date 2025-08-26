# Notification API Documentation

This document describes how external applications can send notifications to users through the Django Notifications system.

## Overview

The Notification API allows external applications to create notifications for users in the system. Notifications are stored using the [django-notifications](https://github.com/django-notifications/django-notifications) library and can be displayed in the user interface.

## Endpoint

**URL:** `POST /source-management/api/notifications/create/`

**Authentication:** Currently no authentication required (consider adding API key authentication for production)

## Request Format

Send a POST request with JSON data in the request body.

### Required Fields

- `recipient_id`: Integer - The ID of the user who should receive the notification
- `verb`: String - The action being performed (e.g., "uploaded", "processed", "failed", "completed")
- `description`: String - Human-readable description of the notification

### Optional Fields

- `actor_id`: Integer - ID of the object performing the action (e.g., user ID, system ID)
- `target_id`: Integer - ID of the object being acted upon (e.g., video ID, source ID)
- `action_object_id`: Integer - ID of the action object (e.g., job ID, task ID)
- `level`: String - Notification level. Must be one of: `success`, `info`, `warning`, `error` (default: `info`)
- `category`: String - Custom category for grouping notifications (optional)

## Example Requests

### Basic Notification

```bash
curl -X POST http://your-domain/source-management/api/notifications/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_id": 123,
    "verb": "uploaded",
    "description": "Video processing completed successfully",
    "level": "success"
  }'
```

### Detailed Notification

```bash
curl -X POST http://your-domain/source-management/api/notifications/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_id": 123,
    "actor_id": 456,
    "verb": "processed",
    "target_id": 789,
    "action_object_id": 101,
    "description": "Video 'sample_video.mp4' has been processed and is ready for viewing",
    "level": "success",
    "category": "video_processing"
  }'
```

### Error Notification

```bash
curl -X POST http://your-domain/source-management/api/notifications/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_id": 123,
    "verb": "failed",
    "description": "Video processing failed due to unsupported format",
    "level": "error",
    "category": "video_processing"
  }'
```

## Response Format

### Success Response (201 Created)

```json
{
  "success": true,
  "notification_id": 42,
  "message": "Notification created successfully"
}
```

### Error Responses

#### Missing Required Fields (400 Bad Request)

```json
{
  "error": "Missing required fields: recipient_id, verb, description"
}
```

#### Invalid Level (400 Bad Request)

```json
{
  "error": "Invalid level. Must be one of: success, info, warning, error"
}
```

#### User Not Found (404 Not Found)

```json
{
  "error": "Recipient user not found"
}
```

#### Invalid JSON (400 Bad Request)

```json
{
  "error": "Invalid JSON data"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "error": "Internal server error",
  "details": "Error description"
}
```

## Notification Levels

- `success`: Green notification for successful operations
- `info`: Blue notification for informational messages
- `warning`: Yellow notification for warnings
- `error`: Red notification for errors

## Use Cases

### Video Processing Notifications

```json
{
  "recipient_id": 123,
  "verb": "processed",
  "description": "Video 'vacation_video.mp4' has been processed successfully",
  "level": "success",
  "category": "video_processing"
}
```

### System Status Notifications

```json
{
  "recipient_id": 123,
  "verb": "updated",
  "description": "System maintenance completed. All services are now operational.",
  "level": "info",
  "category": "system_status"
}
```

### Error Notifications

```json
{
  "recipient_id": 123,
  "verb": "failed",
  "description": "Failed to connect to camera source 'Front Door Camera'",
  "level": "error",
  "category": "camera_connection"
}
```

## Security Considerations

1. **API Key Authentication**: Consider implementing API key authentication for production use
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **Input Validation**: All inputs are validated server-side
4. **User Verification**: Ensure the recipient_id corresponds to a valid user

## Integration Examples

### Python

```python
import requests
import json

def send_notification(recipient_id, verb, description, level="info", **kwargs):
    url = "http://your-domain/source-management/api/notifications/create/"
    
    data = {
        "recipient_id": recipient_id,
        "verb": verb,
        "description": description,
        "level": level,
        **kwargs
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create notification: {response.text}")

# Usage
send_notification(
    recipient_id=123,
    verb="completed",
    description="Data analysis job finished",
    level="success",
    category="data_analysis"
)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function sendNotification(recipientId, verb, description, level = 'info', options = {}) {
    const url = 'http://your-domain/source-management/api/notifications/create/';
    
    const data = {
        recipient_id: recipientId,
        verb,
        description,
        level,
        ...options
    };
    
    try {
        const response = await axios.post(url, data);
        return response.data;
    } catch (error) {
        throw new Error(`Failed to create notification: ${error.response?.data?.error || error.message}`);
    }
}

// Usage
sendNotification(123, 'processed', 'Video uploaded successfully', 'success', {
    category: 'video_upload'
});
```

## Testing

You can test the API using tools like:

- **cURL**: Command-line HTTP client
- **Postman**: GUI-based API testing tool
- **Insomnia**: Modern API client
- **Python requests**: Python HTTP library

## Support

For questions or issues with the Notification API, please contact the development team or create an issue in the project repository.
