# Data Ingestion Service Specification

## 🎯 **Simple Requirements**

### **1. Receive New Source**
- Accept POST request with source information
- Return immediate acknowledgment

### **2. Send Source Status**
- Provide endpoint to check processing status
- Return current status (processing, completed, failed)

### **3. Process File Source**
- Read the source file from provided URL
- Extract video frames at original FPS
- Maintain original size/resolution
- Publish frames to Kafka topic: `zone.cameras.file` (configurable)

---

## 📡 **API Endpoints**

### **POST /api/sources**
Receive new source notification

**Request:**
```json
{
  "source_id": "uuid-1234",
  "file_url": "https://example.com/video.mp4",
  "fps": 30.0,
  "width": 1920,
  "height": 1080
}
```

**Response:**
```json
{
  "success": true,
  "ingestion_id": "ingest-abc123",
  "message": "Source queued for processing"
}
```

### **GET /api/sources/{source_id}/status**
Get processing status

**Response:**
```json
{
  "source_id": "uuid-1234",
  "status": "processing",
  "progress": 65,
  "frames_processed": 1950
}
```

---

## 📊 **Kafka Configuration**

### **Topic**
- **Name**: `zone.cameras.file` (configurable via environment variable)
- **Message Format**: Simple frame data

### **Message Structure**
```json
{
  "source_id": "uuid-1234",
  },
  {
    "frame_id":"uuid",
    "frame_data_base64":"base64 data",
    "frame_shape":["height", "width", "channels"],
    "frame_number": integer,
    "video_timestamp":"Time position in the video stream (in seconds)",
    "frame_decoded_timestamp":"Unix timestamp when the frame was processed",,,
    "frame_size":"size",
    "frame_codec":"string"
}
```

---

## ⚙️ **Configuration**

### **Environment Variables**
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=zone.cameras.file
FFMPEG_PATH=/usr/bin/ffmpeg
```

---

## 🏗️ **Simple Architecture**

```
Source Management → Data Ingestion Service → Kafka (zone.cameras.file)
```

1. **Receive source** → Extract file URL, FPS, size
2. **Read video file** → Use FFmpeg to extract frames
3. **Publish to Kafka** → Send frames to configurable topic
4. **Status updates** → Track and report progress

---

## 📦 **Dependencies**

```txt
fastapi
aiokafka
ffmpeg-python
uvicorn
```

That's it! Simple service that:
- Receives source info
- Reads video file
- Publishes to configurable Kafka topic
- Provides status updates
