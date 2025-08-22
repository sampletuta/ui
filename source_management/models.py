import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import json
from django.utils import timezone
from notifications.signals import notify
import requests
import logging
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)

# Stream processor service configuration
STREAM_PROCESSOR_CONFIG = getattr(settings, 'STREAM_PROCESSOR_CONFIG', {
    'BASE_URL': 'http://localhost:8002',
    'EXTERNAL_SERVICE_ID': 'django-source-management',
    'TIMEOUT': 30,
    'ENABLED': True
})

class BaseSource(models.Model):
    """Base model for all video sources"""
    source_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,help_text="Unique identifier for this source")
    name = models.CharField(max_length=200, help_text="Display name for this source")
    description = models.TextField(blank=True, help_text="Optional description")
    location = models.CharField(max_length=200, blank=True, help_text="Physical location")
    latitude = models.FloatField(null=True, blank=True, help_text="GPS latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="GPS longitude")
    # altitude = models.FloatField(null=True, blank=True, help_text="GPS altitude in meters")

    tags = models.JSONField(default=list, blank=True, help_text="Tags for categorization")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.name} ({self.source_id})"

    def get_source_info(self):
        """Get basic source information"""
        info = {
            'id': self.source_id,
            'source_id': self.source_id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        
        # Add zone and is_active if they exist
        if hasattr(self, 'zone'):
            info['zone'] = self.zone
        if hasattr(self, 'is_active'):
            info['is_active'] = self.is_active
            
        return info

    def get_metadata(self):
        """Get source metadata"""
        metadata = {
            'source_info': self.get_source_info(),
            'tags': self.tags,
        }
        
        # Add configuration if it exists
        if hasattr(self, 'configuration'):
            metadata['configuration'] = self.configuration
            
        return metadata

    def _call_stream_processor_api(self, method, endpoint, data=None, stream_id=None):
        """Make HTTP call to stream processor service"""
        if not STREAM_PROCESSOR_CONFIG.get('ENABLED', True):
            logger.warning(f"Stream processor integration is disabled for {self.__class__.__name__} {self.source_id}")
            return {'success': False, 'error': 'Integration disabled'}
        
        try:
            base_url = STREAM_PROCESSOR_CONFIG['BASE_URL']
            timeout = STREAM_PROCESSOR_CONFIG['TIMEOUT']
            
            if stream_id:
                url = f"{base_url}{endpoint.format(stream_id=stream_id)}"
            else:
                url = f"{base_url}{endpoint}"
            
            headers = {'Content-Type': 'application/json'}
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return {'success': False, 'error': f'Unsupported HTTP method: {method}'}
            
            if response.status_code in (200, 201, 202):
                try:
                    response_data = response.json()
                    return {'success': True, 'data': response_data}
                except ValueError:
                    return {'success': True, 'data': response.text}
            else:
                logger.error(f"Stream processor API error: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'API returned {response.status_code}', 'details': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Stream processor API request failed: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Stream processor API unexpected error: {e}")
            return {'success': False, 'error': str(e)}

class CameraSource(BaseSource):
    """Model for camera sources (IP cameras, USB cameras, etc.)"""
    CAMERA_TYPE_CHOICES = [
        ('ip', 'IP Camera'),
        ('usb', 'USB Camera'),
        ('ptz', 'PTZ Camera'),
        ('dome', 'Dome Camera'),
        ('bullet', 'Bullet Camera'),
        ('other', 'Other'),
    ]
    camera_ip = models.GenericIPAddressField(help_text="IP address of the camera")
    camera_port = models.IntegerField(default=554, validators=[MinValueValidator(1), MaxValueValidator(65535)], help_text="Port number for camera connection")
    camera_username = models.CharField(max_length=100, blank=True, help_text="Username for camera authentication")
    camera_password = models.CharField(max_length=100, blank=True, help_text="Password for camera authentication")
    camera_protocol = models.CharField(max_length=10, choices=[
        ('rtsp', 'RTSP'),
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('rtmp', 'RTMP'),
    ], default='rtsp', help_text="Protocol used to connect to the camera")
    camera_type = models.CharField(max_length=20, choices=CAMERA_TYPE_CHOICES, default='ip', help_text="Type of camera hardware")
    camera_resolution = models.CharField(max_length=20, blank=True, help_text="Camera resolution (e.g., 1920x1080)")
    camera_resolution_width = models.IntegerField(null=True, blank=True, help_text="Camera width in pixels")
    camera_resolution_height = models.IntegerField(null=True, blank=True, help_text="Camera height in pixels")
    camera_fps = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(300)], help_text="Frame rate in frames per second")
    camera_bitrate = models.IntegerField(null=True, blank=True, help_text="Camera bitrate in bits per second")
    camera_codec = models.CharField(max_length=50, blank=True, help_text="Video codec (e.g., h264, h265, mjpeg)")
    
    # Audio Parameters
    camera_audio_enabled = models.BooleanField(default=False, help_text="Whether camera has audio capability")
    camera_audio_codec = models.CharField(max_length=50, blank=True, help_text="Audio codec (e.g., aac, pcm, g711)")
    camera_audio_channels = models.IntegerField(null=True, blank=True, help_text="Number of audio channels")
    camera_audio_sample_rate = models.IntegerField(null=True, blank=True, help_text="Audio sample rate in Hz")
    
    # Network & Performance Parameters
    camera_buffer_size = models.IntegerField(null=True, blank=True, help_text="Buffer size in milliseconds")
    camera_timeout = models.IntegerField(null=True, blank=True, help_text="Connection timeout in seconds")
    camera_keepalive = models.BooleanField(default=True, help_text="Whether to use keepalive connections")
    camera_retry_attempts = models.IntegerField(default=3, help_text="Number of retry attempts on failure")

    zone = models.CharField(max_length=100, blank=True, help_text="Zone name for organization")
    is_active = models.BooleanField(default=True, help_text="Whether this source is active")
    configuration = models.JSONField(default=dict, blank=True, help_text="Additional configuration as JSON")
    
    # Topic customization for downstream model integration
    topic_name = models.CharField(max_length=100, blank=True, help_text="Topic name for downstream model subscription (auto-generated)")
    topic_suffix = models.CharField(max_length=6, blank=True, help_text="Custom suffix for topic name (max 6 chars, no spaces, replaces * in zone.camera.*)")

    class Meta:
        verbose_name = "Camera Source"
        verbose_name_plural = "Camera Sources"

    def generate_topic_name(self, suffix=None):
        """Generate topic name for downstream model integration"""
        if self.zone:
            # Clean zone name: replace spaces and special chars with underscores
            clean_zone = self.zone.replace(' ', '_').replace('.', '_').replace('-', '_')
            base_topic = f"{clean_zone}_camera"
            if suffix:
                # Clean suffix: no spaces, max 6 chars, replace special chars
                clean_suffix = suffix.replace(' ', '_').replace('.', '_').replace('-', '_')[:6]
                return f"{base_topic}_{clean_suffix}"
            else:
                return f"{base_topic}_default"
        return "django_camera_default"

    def get_camera_url(self):
        """Generate camera URL for stream processor service"""
        auth_part = ""
        if self.camera_username:
            auth_part = f"{self.camera_username}:{self.camera_password}@"
        
        return f"{self.camera_protocol}://{auth_part}{self.camera_ip}:{self.camera_port}/stream"

    def get_stream_processor_payload(self):
        """Get payload for stream processor service"""
        return {
            'stream_id': str(self.source_id),
            'source_url': self.get_camera_url(),
            'topic_name': self.topic_name or self.generate_topic_name(self.topic_suffix),
            'external_service_id': STREAM_PROCESSOR_CONFIG['EXTERNAL_SERVICE_ID'],
            'target_fps': self.camera_fps or 1.0,
            'frame_quality': 85,
            'resize_enabled': bool(self.camera_resolution_width and self.camera_resolution_height),
            'target_width': self.camera_resolution_width,
            'target_height': self.camera_resolution_height,
            'username': self.camera_username if self.camera_username else None,
            'password': self.camera_password if self.camera_password else None,
            'metadata': {
                'camera_type': self.camera_type,
                'camera_protocol': self.camera_protocol,
                'zone': self.zone,
                'location': self.location,
                'description': self.description
            }
        }

    def save(self, *args, **kwargs):
        # Auto-generate topic name if not set
        if not self.topic_name:
            self.topic_name = self.generate_topic_name(self.topic_suffix)
        
        # Check if this is a new camera or existing one
        # For UUID primary keys, we need to check if the record exists in DB
        is_new = not self.__class__.objects.filter(pk=self.pk).exists()
        
        super().save(*args, **kwargs)
        
        # Integrate with stream processor service
        if is_new and self.is_active:
            # Create new stream in processor service
            self._create_in_stream_processor()
        elif not is_new and self.is_active:
            # Update existing stream in processor service
            self._update_in_stream_processor()

    def delete(self, *args, **kwargs):
        # Remove from stream processor service first
        self._delete_from_stream_processor()
        super().delete(*args, **kwargs)

    def _create_in_stream_processor(self):
        """Create camera stream in stream processor service"""
        payload = self.get_stream_processor_payload()
        result = self._call_stream_processor_api('POST', '/api/external/streams', data=payload)
        
        if result['success']:
            logger.info(f"Camera {self.source_id} created in stream processor service")
        else:
            logger.error(f"Failed to create camera {self.source_id} in stream processor service: {result.get('error')}")

    def _update_in_stream_processor(self):
        """Update camera stream in stream processor service"""
        payload = {
            'stream_id': str(self.source_id),
            'target_fps': self.camera_fps or 1.0,
            'frame_quality': 85,
            'resize_enabled': bool(self.camera_resolution_width and self.camera_resolution_height),
            'target_width': self.camera_resolution_width,
            'target_height': self.camera_resolution_height,
            'metadata': {
                'camera_type': self.camera_type,
                'camera_protocol': self.camera_protocol,
                'zone': self.zone,
                'location': self.location,
                'description': self.description
            }
        }
        
        result = self._call_stream_processor_api('PUT', '/api/external/streams/{stream_id}', data=payload, stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Camera {self.source_id} updated in stream processor service")
        else:
            logger.error(f"Failed to update camera {self.source_id} in stream processor service: {result.get('error')}")

    def _delete_from_stream_processor(self):
        """Delete camera stream from stream processor service"""
        result = self._call_stream_processor_api('DELETE', '/api/external/streams/{stream_id}', stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Camera {self.source_id} deleted from stream processor service")
        else:
            logger.error(f"Failed to delete camera {self.source_id} from stream processor service: {result.get('error')}")

    def get_processor_status(self):
        """Get the current status from the stream processor service"""
        result = self._call_stream_processor_api('GET', '/api/external/streams/{stream_id}/status', stream_id=str(self.source_id))
        
        if result['success']:
            return result
        else:
            # Handle 404 (stream not found) gracefully
            if 'API returned 404' in result.get('error', ''):
                return {
                    'success': False,
                    'error': 'Stream not found in processor service',
                    'not_found': True
                }
            else:
                logger.error(f"Error getting processor status for camera {self.source_id}: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error')
                }

    def start_processor_stream(self):
        """Start the camera stream in the processor service"""
        result = self._call_stream_processor_api('PUT', '/api/external/streams/{stream_id}/start', stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Camera {self.source_id} started in stream processor service")
            return result['data']
        else:
            logger.error(f"Error starting camera {self.source_id} in stream processor service: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error')
            }

    def stop_processor_stream(self):
        """Stop the camera stream in the processor service"""
        result = self._call_stream_processor_api('PUT', '/api/external/streams/{stream_id}/stop', stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Camera {self.source_id} stopped in stream processor service")
            return result['data']
        else:
            logger.error(f"Error stopping camera {self.source_id} in stream processor service: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error')
            }

    def get_camera_info(self):
        """Get camera-specific information"""
        return {
            'ip': self.camera_ip,
            'port': self.camera_port,
            'protocol': self.camera_protocol,
            'type': self.camera_type,
            'resolution': self.camera_resolution,
            'resolution_width': self.camera_resolution_width,
            'resolution_height': self.camera_resolution_height,
            'fps': self.camera_fps,
            'bitrate': self.camera_bitrate,
            'codec': self.camera_codec,
            'audio_enabled': self.camera_audio_enabled,
            'audio_codec': self.camera_audio_codec,
            'audio_channels': self.camera_audio_channels,
            'audio_sample_rate': self.camera_audio_sample_rate,
            'buffer_size': self.camera_buffer_size,
            'timeout': self.camera_timeout,
            'keepalive': self.camera_keepalive,
            'retry_attempts': self.camera_retry_attempts,
            'has_auth': bool(self.camera_username),
            'zone': self.zone,
            'configuration': self.configuration,
            'is_active': self.is_active,
            'topic_name': self.topic_name,
            'topic_suffix': self.topic_suffix,
        }

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('source_management:camera_detail', kwargs={'source_id': self.source_id})

    def get_stream_url(self):
        """Generate stream URL for the camera"""
        return self.get_camera_url()

class FileSource(BaseSource):
    """Model for file sources (uploaded video files)"""
    video_file = models.FileField(upload_to='videos/', help_text="Uploaded video file")
    file_format = models.CharField(max_length=10, blank=True, help_text="File format (e.g., mp4, avi)")
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    
    # Video metadata (auto-extracted)
    duration = models.FloatField(null=True, blank=True, help_text="Video duration in seconds")
    width = models.IntegerField(null=True, blank=True, help_text="Video width in pixels")
    height = models.IntegerField(null=True, blank=True, help_text="Video height in pixels")
    fps = models.FloatField(null=True, blank=True, help_text="Frame rate (frames per second)")
    bitrate = models.IntegerField(null=True, blank=True, help_text="Video bitrate in bits per second")
    codec = models.CharField(max_length=50, blank=True, help_text="Video codec (e.g., h264, h265)")
    audio_codec = models.CharField(max_length=50, blank=True, help_text="Audio codec (e.g., aac, mp3)")
    audio_channels = models.IntegerField(null=True, blank=True, help_text="Number of audio channels")
    audio_sample_rate = models.IntegerField(null=True, blank=True, help_text="Audio sample rate in Hz")
    
    # Access links for downstream models
    access_token = models.CharField(max_length=64, unique=True, blank=True, help_text="Unique access token for API access")
    api_endpoint = models.URLField(blank=True, help_text="API endpoint for accessing this video")
    stream_url = models.URLField(blank=True, help_text="Stream URL for video playback")
    thumbnail_url = models.URLField(blank=True, help_text="URL to video thumbnail")
    
    # Processing metadata
    processing_started_at = models.DateTimeField(null=True, blank=True, help_text="When processing started")
    processing_completed_at = models.DateTimeField(null=True, blank=True, help_text="When processing completed")
    processing_error = models.TextField(blank=True, help_text="Error message if processing failed")
    
    # Additional metadata
    recording_date = models.DateTimeField(null=True, blank=True, help_text="Date when video was recorded")
    camera_info = models.JSONField(default=dict, blank=True, help_text="Camera information if available")
    scene_info = models.JSONField(default=dict, blank=True, help_text="Scene analysis information")
    
    # Data ingestion notification tracking
    ingestion_notified = models.BooleanField(default=False, help_text="Whether data ingestion service was notified")
    ingestion_notified_at = models.DateTimeField(null=True, blank=True, help_text="When data ingestion service was notified")
    ingestion_response = models.JSONField(default=dict, blank=True, help_text="Response from data ingestion service")

    class Meta:
        verbose_name = "File Source"
        verbose_name_plural = "File Sources"

    def save(self, *args, **kwargs):
        # Generate access token if not exists
        if not self.access_token:
            import secrets
            self.access_token = secrets.token_urlsafe(32)
        
        # Generate API endpoints
        if self.pk and self.status == 'ready':
            from django.conf import settings
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            self.api_endpoint = f"{base_url}/source-management/api/video/{self.access_token}/"
            self.stream_url = f"{base_url}/source-management/api/video/{self.access_token}/stream/"
            self.thumbnail_url = f"{base_url}/source-management/api/video/{self.access_token}/stream/"  # Use stream URL for now
        
        super().save(*args, **kwargs)
        try:
            # Notify creator when file source becomes ready
            if self.status == 'ready':
                notify.send(self.created_by, recipient=self.created_by, verb='processing_ready', target=self)
        except Exception:
            pass

    def get_file_info(self):
        """Get file-specific information"""
        return {
            'filename': self.video_file.name if self.video_file else None,
            'format': self.file_format,
            'size': self.file_size,
            'status': self.status,
            'duration': self.duration,
            'resolution': f"{self.width}x{self.height}" if self.width and self.height else None,
            'fps': self.fps,
            'bitrate': self.bitrate,
            'codec': self.codec,
            'audio_codec': self.audio_codec,
            'audio_channels': self.audio_channels,
            'audio_sample_rate': self.audio_sample_rate,
        }

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('source_management:file_detail', kwargs={'source_id': self.source_id})

    def get_file_size_display(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_duration_display(self):
        """Get human-readable duration"""
        if not self.duration:
            return "Unknown"
        
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def get_resolution_display(self):
        """Get human-readable resolution"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"

    def get_api_links(self):
        """Get all API access links for downstream models"""
        return {
            'api_endpoint': self.api_endpoint,
            'stream_url': self.stream_url,
            'thumbnail_url': self.thumbnail_url,
            'access_token': self.access_token,
            'metadata_url': f"{self.api_endpoint}metadata/",
            'download_url': f"{self.api_endpoint}download/",
        }

    def extract_video_metadata(self):
        """Extract video metadata using ffprobe"""
        if not self.video_file:
            return False
        
        try:
            import subprocess
            import json
            import os
            
            file_path = self.video_file.path
            if not os.path.exists(file_path):
                return False
            
            # Use ffprobe to extract video information
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return False
            
            data = json.loads(result.stdout)
            
            # Extract format information
            format_info = data.get('format', {})
            self.duration = float(format_info.get('duration', 0))
            self.file_size = int(format_info.get('size', 0))
            self.bitrate = int(format_info.get('bit_rate', 0))
            
            # Extract video stream information
            video_stream = None
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                elif stream.get('codec_type') == 'audio':
                    audio_stream = stream
            
            if video_stream:
                self.width = int(video_stream.get('width', 0))
                self.height = int(video_stream.get('height', 0))
                # Safely parse frame rate fraction
                frame_rate_str = video_stream.get('r_frame_rate', '0/1')
                try:
                    numerator, denominator = frame_rate_str.split('/')
                    self.fps = float(numerator) / float(denominator) if float(denominator) != 0 else 0
                except (ValueError, ZeroDivisionError):
                    self.fps = 0
                self.codec = video_stream.get('codec_name', '')
            
            if audio_stream:
                self.audio_codec = audio_stream.get('codec_name', '')
                self.audio_channels = int(audio_stream.get('channels', 0))
                self.audio_sample_rate = int(audio_stream.get('sample_rate', 0))
            
            # Extract file format
            self.file_format = format_info.get('format_name', '').split(',')[0]
            
            return True
            
        except Exception as e:
            self.processing_error = str(e)
            return False

    def process_video(self):
        """Process video file and extract metadata"""
        self.status = 'processing'
        self.processing_started_at = timezone.now()
        self.save()
        
        try:
            # Extract video metadata
            if self.extract_video_metadata():
                self.status = 'ready'
                self.processing_completed_at = timezone.now()
                self.save()
                return True
            else:
                self.status = 'failed'
                self.processing_completed_at = timezone.now()
                self.save()
                return False
        except Exception as e:
            self.status = 'failed'
            self.processing_error = str(e)
            self.processing_completed_at = timezone.now()
            self.save()
            return False

class StreamSource(BaseSource):
    """Model for stream sources (RTSP, HTTP streams, etc.)"""
    stream_url = models.CharField(max_length=500, help_text="URL of the video stream (supports RTSP, RTMP, HTTP, UDP, etc.)")
    stream_protocol = models.CharField(max_length=10, choices=[
        ('rtsp', 'RTSP'),
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('rtmp', 'RTMP'),
        ('hls', 'HLS'),
        ('dash', 'DASH'),
    ], default='rtsp', help_text="Protocol of the stream")
    
    # Stream Quality & Performance Parameters
    stream_quality = models.CharField(max_length=20, blank=True, help_text="Stream quality (e.g., 1080p, 720p)")
    stream_resolution_width = models.IntegerField(null=True, blank=True, help_text="Stream width in pixels")
    stream_resolution_height = models.IntegerField(null=True, blank=True, help_text="Stream height in pixels")
    stream_fps = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.1), MaxValueValidator(300)], help_text="Stream frame rate (frames per second)")
    stream_bitrate = models.IntegerField(null=True, blank=True, help_text="Stream bitrate in bits per second")
    stream_codec = models.CharField(max_length=50, blank=True, help_text="Video codec (e.g., h264, h265, av1)")
    
    # Audio Parameters
    stream_audio_codec = models.CharField(max_length=50, blank=True, help_text="Audio codec (e.g., aac, mp3, opus)")
    stream_audio_channels = models.IntegerField(null=True, blank=True, help_text="Number of audio channels")
    stream_audio_sample_rate = models.IntegerField(null=True, blank=True, help_text="Audio sample rate in Hz")
    stream_audio_bitrate = models.IntegerField(null=True, blank=True, help_text="Audio bitrate in bits per second")
    
    # Network & Performance Parameters
    stream_buffer_size = models.IntegerField(null=True, blank=True, help_text="Buffer size in milliseconds")
    stream_timeout = models.IntegerField(null=True, blank=True, help_text="Connection timeout in seconds")
    stream_retry_attempts = models.IntegerField(default=3, help_text="Number of retry attempts on failure")
    stream_keepalive = models.BooleanField(default=True, help_text="Whether to use keepalive connections")
    
    # Advanced Configuration
    stream_parameters = models.JSONField(default=dict, blank=True, help_text="Additional stream parameters as JSON")
    stream_authentication = models.JSONField(default=dict, blank=True, help_text="Authentication credentials as JSON")
    stream_headers = models.JSONField(default=dict, blank=True, help_text="Custom HTTP headers as JSON")
    
    # Additional fields for consistency with other source types
    zone = models.CharField(max_length=100, blank=True, help_text="Zone name for organization")
    is_active = models.BooleanField(default=True, help_text="Whether this source is active")
    configuration = models.JSONField(default=dict, blank=True, help_text="Additional configuration as JSON")
    
    # Topic customization for downstream model integration
    topic_name = models.CharField(max_length=100, blank=True, help_text="Topic name for downstream model subscription (auto-generated)")
    topic_suffix = models.CharField(max_length=6, blank=True, help_text="Custom suffix for topic name (max 6 chars, no spaces, replaces * in zone.camera.*)")

    class Meta:
        verbose_name = "Stream Source"
        verbose_name_plural = "Stream Sources"

    def generate_topic_name(self, suffix=None):
        """Generate topic name for downstream model integration"""
        if self.zone:
            # Clean zone name: replace spaces and special chars with underscores
            clean_zone = self.zone.replace(' ', '_').replace('.', '_').replace('-', '_')
            base_topic = f"{clean_zone}_stream"
            if suffix:
                # Clean suffix: no spaces, max 6 chars, replace special chars
                clean_suffix = suffix.replace(' ', '_').replace('.', '_').replace('-', '_')[:6]
                return f"{base_topic}_{clean_suffix}"
            else:
                return f"{base_topic}_default"
        return "django_stream_default"

    def get_stream_processor_payload(self):
        """Get payload for stream processor service"""
        # Extract authentication from JSON if available
        username = None
        password = None
        if self.stream_authentication:
            username = self.stream_authentication.get('username')
            password = self.stream_authentication.get('password')
        
        return {
            'stream_id': str(self.source_id),
            'source_url': self.stream_url,
            'topic_name': self.topic_name or self.generate_topic_name(self.topic_suffix),
            'external_service_id': STREAM_PROCESSOR_CONFIG['EXTERNAL_SERVICE_ID'],
            'target_fps': self.stream_fps or 1.0,
            'frame_quality': 85,
            'resize_enabled': bool(self.stream_resolution_width and self.stream_resolution_height),
            'target_width': self.stream_resolution_width,
            'target_height': self.stream_resolution_height,
            'username': username,
            'password': password,
            'metadata': {
                'stream_protocol': self.stream_protocol,
                'stream_quality': self.stream_quality,
                'stream_codec': self.stream_codec,
                'zone': self.zone,
                'location': self.location,
                'description': self.description,
                'stream_parameters': self.stream_parameters,
                'stream_headers': self.stream_headers
            }
        }

    def save(self, *args, **kwargs):
        # Auto-generate topic name if not set
        if not self.topic_name:
            self.topic_name = self.generate_topic_name(self.topic_suffix)
        
        # Check if this is a new stream or existing one
        # For UUID primary keys, we need to check if the record exists in DB
        is_new = not self.__class__.objects.filter(pk=self.pk).exists()
        
        super().save(*args, **kwargs)
        
        # Integrate with stream processor service
        if is_new and self.is_active:
            # Create new stream in processor service
            self._create_in_stream_processor()
        elif not is_new and self.is_active:
            # Update existing stream in processor service
            self._update_in_stream_processor()

    def delete(self, *args, **kwargs):
        # Remove from stream processor service first
        self._delete_from_stream_processor()
        super().delete(*args, **kwargs)

    def _create_in_stream_processor(self):
        """Create stream in stream processor service"""
        payload = self.get_stream_processor_payload()
        result = self._call_stream_processor_api('POST', '/api/external/streams', data=payload)
        
        if result['success']:
            logger.info(f"Stream {self.source_id} created in processor service")
        else:
            logger.warning(f"Failed to create stream {self.source_id} in processor service: {result.get('error')}")

    def _update_in_stream_processor(self):
        """Update stream in stream processor service"""
        payload = {
            'stream_id': str(self.source_id),
            'target_fps': self.stream_fps or 1.0,
            'frame_quality': 85,
            'resize_enabled': bool(self.stream_resolution_width and self.stream_resolution_height),
            'target_width': self.stream_resolution_width,
            'target_height': self.stream_resolution_height,
            'metadata': {
                'stream_protocol': self.stream_protocol,
                'stream_quality': self.stream_quality,
                'stream_codec': self.stream_codec,
                'zone': self.zone,
                'location': self.location,
                'description': self.description,
                'stream_parameters': self.stream_parameters,
                'stream_headers': self.stream_headers
            }
        }
        
        result = self._call_stream_processor_api('PUT', '/api/external/streams/{stream_id}', data=payload, stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Stream {self.source_id} updated in processor service")
        else:
            logger.warning(f"Failed to update stream {self.source_id} in processor service: {result.get('error')}")

    def _delete_from_stream_processor(self):
        """Delete stream from stream processor service"""
        result = self._call_stream_processor_api('DELETE', '/api/external/streams/{stream_id}', stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Stream {self.source_id} deleted from processor service")
        else:
            logger.warning(f"Failed to delete stream {self.source_id} from processor service: {result.get('error')}")

    def get_processor_status(self):
        """Get the current status from the stream processor service"""
        result = self._call_stream_processor_api('GET', '/api/external/streams/{stream_id}/status', stream_id=str(self.source_id))
        
        if result['success']:
            return result
        else:
            # Handle 404 (stream not found) gracefully
            if 'API returned 404' in result.get('error', ''):
                return {
                    'success': False,
                    'error': 'Stream not found in processor service',
                    'not_found': True
                }
            else:
                logger.error(f"Error getting processor status for stream {self.source_id}: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error')
                }

    def get_processor_metrics(self):
        """Get metrics from the stream processor service"""
        # This would use the status endpoint which includes metrics
        return self.get_processor_status()

    def get_processor_real_time_stats(self):
        """Get real-time statistics from the stream processor service"""
        # This would use the status endpoint which includes real-time stats
        return self.get_processor_status()

    def start_processor_stream(self):
        """Start the stream in the processor service"""
        result = self._call_stream_processor_api('PUT', '/api/external/streams/{stream_id}/start', stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Stream {self.source_id} started in processor service")
            return result['data']
        else:
            logger.error(f"Error starting stream {self.source_id} in processor service: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error')
            }

    def stop_processor_stream(self):
        """Stop the stream in the processor service"""
        result = self._call_stream_processor_api('PUT', '/api/external/streams/{stream_id}/stop', stream_id=str(self.source_id))
        
        if result['success']:
            logger.info(f"Stream {self.source_id} stopped in processor service")
            return result['data']
        else:
            logger.error(f"Error stopping stream {self.source_id} in processor service: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error')
            }

    def get_stream_info(self):
        """Get stream-specific information"""
        return {
            'url': self.stream_url,
            'protocol': self.stream_protocol,
            'quality': self.stream_quality,
            'resolution_width': self.stream_resolution_width,
            'resolution_height': self.stream_resolution_height,
            'fps': self.stream_fps,
            'bitrate': self.stream_bitrate,
            'codec': self.stream_codec,
            'audio_codec': self.stream_audio_codec,
            'audio_channels': self.stream_audio_channels,
            'audio_sample_rate': self.stream_audio_sample_rate,
            'audio_bitrate': self.stream_audio_bitrate,
            'buffer_size': self.stream_buffer_size,
            'timeout': self.stream_timeout,
            'retry_attempts': self.stream_retry_attempts,
            'keepalive': self.stream_keepalive,
            'parameters': self.stream_parameters,
            'authentication': self.stream_authentication,
            'headers': self.stream_headers,
            'zone': self.zone,
            'is_active': self.is_active,
            'configuration': self.configuration,
            'topic_name': self.topic_name,
            'topic_suffix': self.topic_suffix,
        }

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('source_management:stream_detail', kwargs={'source_id': self.source_id})

class VideoProcessingJob(models.Model):
    """Model to track video processing jobs sent to external services"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    job_id = models.CharField(max_length=100, unique=True, help_text="External service job ID")
    source = models.ForeignKey(FileSource, on_delete=models.CASCADE, related_name='processing_jobs')
    external_job_id = models.CharField(max_length=100, blank=True, help_text="Job ID returned by external service")
    
    # Processing parameters
    target_fps = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(120)], help_text="Target frame rate")
    target_resolution = models.CharField(max_length=20, help_text="Target resolution (e.g., 640x480)")
    
    # Job status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # External service communication
    external_service_url = models.URLField(help_text="URL of the external processing service")
    callback_url = models.URLField(null=True, blank=True, help_text="Callback URL for external service (optional for pull-based status checking)")
    access_token = models.CharField(max_length=64, help_text="Access token for external service")
    
    # Response tracking
    external_response = models.JSONField(default=dict, blank=True, help_text="Response from external service")
    error_message = models.TextField(blank=True, help_text="Error message if job failed")
    
    # Processing results
    processed_video_url = models.URLField(blank=True, help_text="URL to processed video")
    processing_metadata = models.JSONField(default=dict, blank=True, help_text="Additional processing metadata")
    
    class Meta:
        verbose_name = "Video Processing Job"
        verbose_name_plural = "Video Processing Jobs"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Job {self.job_id} - {self.source.name} ({self.status})"
    
    def get_processing_params(self):
        """Get processing parameters as dict"""
        return {
            'target_fps': self.target_fps,
            'target_resolution': self.target_resolution,
        }
    
    def get_source_metadata(self):
        """Get source metadata for external service"""
        return {
            'source_id': str(self.source.source_id),
            'stream_url': self.source.stream_url or self.source.api_endpoint,
            'width': self.source.width,
            'height': self.source.height,
            'api_endpoint': self.callback_url or '',
            'access_token': self.access_token,
        }
    
    def get_external_payload(self):
        """Get the complete payload to send to external service"""
        return {
            'source_metadata': self.get_source_metadata(),
            'processing_params': self.get_processing_params(),
        }
    
    def update_status(self, new_status, **kwargs):
        """Update job status and related fields"""
        self.status = new_status
        
        if new_status == 'processing' and not self.started_at:
            self.started_at = timezone.now()
        elif new_status in ['completed', 'failed'] and not self.completed_at:
            self.completed_at = timezone.now()
        
        # Update any additional fields passed as kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.save()
        # Send notifications on status transitions
        try:
            if new_status == 'processing':
                notify.send(self.source.created_by, recipient=self.source.created_by, verb='processing_started', target=self)
            elif new_status == 'completed':
                notify.send(self.source.created_by, recipient=self.source.created_by, verb='processing_ready', target=self)
            elif new_status == 'failed':
                notify.send(self.source.created_by, recipient=self.source.created_by, verb='processing_failed', target=self)
        except Exception:
            pass
