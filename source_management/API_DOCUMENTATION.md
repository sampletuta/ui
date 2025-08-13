# ultrafastingestion Integration API

- Base URL: http://localhost:5665
- Content-Type: application/json

## Endpoints
- GET `/` – service info
- GET `/health` – basic health
- GET `/api/` – API info
- POST `/process_video` – start job (alias: POST `/api/process-video`)
- GET `/job/{source_id}/status` – job status
- GET `/jobs` – list jobs
- GET `/kafka/stats` – producer stats
- GET `/metrics` – Prometheus metrics (text/plain)

## POST /process_video
Request body (FastpublishRequestSchema):
```json
{
  "source_metadata": {
    "source_id": "string (required)",
    "stream_url": "string (required, URL)",
    "width": "integer (>0, optional; default 604)",
    "height": "integer (>0, optional; default 640)",
    "api_endpoint": "string (optional; callback URL)",
    "access_token": "string (optional; used if auth mode is bearer)"
  },
  "processing_params": {
    "target_fps": "integer (optional; 1 to 5)",
    "target_resolution": "string (optional; WIDTHxHEIGHT)"
  }
}
```
Example:
```bash
curl -X POST http://localhost:5665/process_video \
  -H 'Content-Type: application/json' \
  -d '{
    "source_metadata": {
      "source_id": "camera-001",
      "stream_url": "https://example.com/video.mp4",
      "width": 1920,
      "height": 1080
    },
    "processing_params": {"target_fps": 5, "target_resolution": "640x480"}
  }'
```
Responses:
- 202 Accepted: `{ "status": "success", "message": "Video processing initiated for source_id: camera-001" }`
- 400 Bad Request: `{ "detail": "validation error" }`
- 409 Conflict: `{ "detail": "Job already running for source_id=camera-001" }`

## GET /job/{source_id}/status
Response:
```json
{
  "status": "running|completed|failed",
  "frames_published": 0,
  "frames_failed": 0,
  "start_time": 0.0,
  "last_activity": 0.0,
  "error": null
}
```

## GET /kafka/stats
```json
{
  "kafka_producer": {
    "total_published": 0,
    "total_failed": 0,
    "connected": true,
    "last_publish_time": 0.0,
    "success_rate": 100.0
  },
  "timestamp": 0.0
}
```

## GET /metrics (text)
```
# HELP frames_published_total Total frames successfully published
# TYPE frames_published_total counter
frames_published_total 0
# HELP frames_failed_total Total frames failed to publish
# TYPE frames_failed_total counter
frames_failed_total 0
# HELP jobs_running Number of active jobs
# TYPE jobs_running gauge
jobs_running 0
```

## Kafka message schema (topic: camera.zone.file)
```json
{
  "source_metadata": { "source_id": "camera-001" },
  "frame_metadata": {
    "frame_id": "uuid",
    "frame_shape": "640x480",
    "frame_number": 1,
    "video_timestamp": 0.0,
    "frame_decoded_timestamp": 0.0,
    "frame_size": 0,
    "frame_codec": "jpeg|rawvideo",
    "frame_data_base64": "..."
  }
}
```

## Error callbacks
- PUT to `source_metadata.api_endpoint` with body `{ "processing_error": "..." }`
- Auth modes via env: none (default), bearer (`Authorization: Bearer <token>`), hmac (`X-Signature`)

## Environment (selected)
- `KAFKA_BOOTSTRAP_SERVERS` (e.g., `kafka:29092`)
- `KAFKA_TOPIC` (default `camera.zone.file`)
- `PRODUCER_IMPL` (`confluent`|`kafka-python`)
- `KAFKA_ACKS` (`1` or `all`)
- `PAYLOAD_FORMAT` (`jpeg` default, or `raw`)
- `FFMPEG_THREADS`, `ENABLE_HARDWARE_ACCELERATION`
- `BATCH_FLUSH_MS`, `BATCH_MAX_MESSAGES`
- `QUEUE_MAX_FRAMES`, `QUEUE_MAX_ENCODED`, `ENCODER_WORKERS`
- `AUTH_MODE`, `AUTH_TOKEN`, `HMAC_SECRET`
