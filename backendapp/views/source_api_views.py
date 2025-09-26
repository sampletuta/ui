"""
Source Management API Views
Handles registration and management of video sources (cameras, streams, files)
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.models import User
from django.utils import timezone
from source_management.models import CameraSource, FileSource, StreamSource

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def api_register_camera(request):
    """
    Register a new camera source for monitoring
    
    Expected POST data:
    {
        "name": "Main Entrance Camera",
        "description": "Primary entrance monitoring camera",
        "location": "Main Building Entrance",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "camera_ip": "192.168.1.100",
        "camera_port": 554,
        "camera_username": "admin",
        "camera_password": "password123",
        "camera_protocol": "rtsp",
        "camera_type": "ip",
        "camera_resolution_width": 1920,
        "camera_resolution_height": 1080,
        "camera_fps": 30,
        "zone": "entrance",
        "user_id": "user_123"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Required fields
        required_fields = ['name', 'camera_ip', 'camera_port', 'camera_protocol', 'user_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate user exists
        try:
            user = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Create camera source
        camera_source = CameraSource.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            location=data.get('location', ''),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            camera_ip=data['camera_ip'],
            camera_port=data['camera_port'],
            camera_username=data.get('camera_username', ''),
            camera_password=data.get('camera_password', ''),
            camera_protocol=data['camera_protocol'],
            camera_type=data.get('camera_type', 'ip'),
            camera_resolution_width=data.get('camera_resolution_width'),
            camera_resolution_height=data.get('camera_resolution_height'),
            camera_fps=data.get('camera_fps'),
            zone=data.get('zone', ''),
            created_by=user
        )
        
        return JsonResponse({
            'success': True,
            'source_id': str(camera_source.source_id),
            'source_type': 'camera',
            'status': 'registered',
            'stream_url': camera_source.get_camera_url(),
            'topic_name': camera_source.topic_name,
            'message': 'Camera source registered successfully'
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error registering camera: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def api_register_stream(request):
    """
    Register a new stream source for monitoring
    
    Expected POST data:
    {
        "name": "Live Stream Camera",
        "description": "Public live stream",
        "location": "Public Area",
        "stream_url": "https://stream.example.com/live",
        "stream_protocol": "https",
        "stream_quality": "1080p",
        "stream_fps": 25,
        "zone": "public",
        "user_id": "user_123"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Required fields
        required_fields = ['name', 'stream_url', 'stream_protocol', 'user_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate user exists
        try:
            user = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Create stream source
        stream_source = StreamSource.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            location=data.get('location', ''),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            stream_url=data['stream_url'],
            stream_protocol=data['stream_protocol'],
            stream_quality=data.get('stream_quality', ''),
            stream_fps=data.get('stream_fps'),
            zone=data.get('zone', ''),
            created_by=user
        )
        
        return JsonResponse({
            'success': True,
            'source_id': str(stream_source.source_id),
            'source_type': 'stream',
            'status': 'registered',
            'topic_name': stream_source.topic_name,
            'message': 'Stream source registered successfully'
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error registering stream: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def api_register_file(request):
    """
    Register a new file source for processing
    
    Expected POST data:
    {
        "name": "Security Footage",
        "description": "Uploaded security footage",
        "location": "Archive",
        "video_file_url": "https://example.com/video.mp4",
        "file_format": "mp4",
        "duration": 3600,
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "user_id": "user_123"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Required fields
        required_fields = ['name', 'video_file_url', 'user_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate user exists
        try:
            user = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Create file source
        file_source = FileSource.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            location=data.get('location', ''),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            file_format=data.get('file_format', ''),
            duration=data.get('duration'),
            width=data.get('width'),
            height=data.get('height'),
            fps=data.get('fps'),
            status='ready',  # Assume ready for external files
            created_by=user
        )
        
        return JsonResponse({
            'success': True,
            'source_id': str(file_source.source_id),
            'source_type': 'file',
            'status': 'registered',
            'access_token': file_source.access_token,
            'api_endpoint': file_source.api_endpoint,
            'message': 'File source registered successfully'
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error registering file: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_get_source_status(request, source_id):
    """
    Get the current status of a registered source
    
    GET /api/sources/<source_id>/status/
    """
    try:
        # Try to find the source in any of the source models
        source = None
        source_type = None
        
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
        except CameraSource.DoesNotExist:
            try:
                source = FileSource.objects.get(source_id=source_id)
                source_type = 'file'
            except FileSource.DoesNotExist:
                try:
                    source = StreamSource.objects.get(source_id=source_id)
                    source_type = 'stream'
                except StreamSource.DoesNotExist:
                    return JsonResponse({'error': 'Source not found'}, status=404)
        
        # Get source metadata
        metadata = {
            'location': source.location,
            'zone': getattr(source, 'zone', ''),
            'created_at': source.created_at.isoformat(),
            'updated_at': source.updated_at.isoformat()
        }
        
        # Add type-specific metadata
        if source_type == 'camera':
            metadata.update({
                'resolution': f"{source.camera_resolution_width}x{source.camera_resolution_height}" if source.camera_resolution_width and source.camera_resolution_height else None,
                'fps': source.camera_fps,
                'protocol': source.camera_protocol,
                'ip': source.camera_ip,
                'port': source.camera_port
            })
        elif source_type == 'stream':
            metadata.update({
                'resolution': f"{source.stream_resolution_width}x{source.stream_resolution_height}" if source.stream_resolution_width and source.stream_resolution_height else None,
                'fps': source.stream_fps,
                'protocol': source.stream_protocol,
                'quality': source.stream_quality
            })
        elif source_type == 'file':
            metadata.update({
                'resolution': f"{source.width}x{source.height}" if source.width and source.height else None,
                'fps': source.fps,
                'duration': source.duration,
                'format': source.file_format,
                'status': source.status
            })
        
        return JsonResponse({
            'success': True,
            'source_id': str(source.source_id),
            'source_type': source_type,
            'name': source.name,
            'status': 'active' if source.is_active else 'inactive',
            'is_active': source.is_active,
            'last_heartbeat': timezone.now().isoformat(),  # Placeholder
            'stream_status': 'live' if source.is_active else 'offline',
            'processing_status': 'monitoring' if source.is_active else 'stopped',
            'metadata': metadata
        })
        
    except Exception as e:
        logger.error(f"Error getting source status: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_list_sources(request):
    """
    Get list of all registered sources
    
    GET /api/sources/list/
    Query Parameters:
    - source_type: Filter by source type (camera, stream, file)
    - zone: Filter by zone
    - status: Filter by status (active, inactive)
    - user_id: Filter by user
    """
    try:
        # Get query parameters
        source_type = request.GET.get('source_type')
        zone = request.GET.get('zone')
        status = request.GET.get('status')
        user_id = request.GET.get('user_id')
        
        # Build sources list
        sources = []
        
        # Get camera sources
        if not source_type or source_type == 'camera':
            camera_sources = CameraSource.objects.all()
            if zone:
                camera_sources = camera_sources.filter(zone=zone)
            if user_id:
                camera_sources = camera_sources.filter(created_by_id=user_id)
            if status == 'active':
                camera_sources = camera_sources.filter(is_active=True)
            elif status == 'inactive':
                camera_sources = camera_sources.filter(is_active=False)
            
            for source in camera_sources:
                sources.append({
                    'source_id': str(source.source_id),
                    'source_type': 'camera',
                    'name': source.name,
                    'status': 'active' if source.is_active else 'inactive',
                    'location': source.location,
                    'zone': source.zone,
                    'created_at': source.created_at.isoformat()
                })
        
        # Get stream sources
        if not source_type or source_type == 'stream':
            stream_sources = StreamSource.objects.all()
            if zone:
                stream_sources = stream_sources.filter(zone=zone)
            if user_id:
                stream_sources = stream_sources.filter(created_by_id=user_id)
            if status == 'active':
                stream_sources = stream_sources.filter(is_active=True)
            elif status == 'inactive':
                stream_sources = stream_sources.filter(is_active=False)
            
            for source in stream_sources:
                sources.append({
                    'source_id': str(source.source_id),
                    'source_type': 'stream',
                    'name': source.name,
                    'status': 'active' if source.is_active else 'inactive',
                    'location': source.location,
                    'zone': source.zone,
                    'created_at': source.created_at.isoformat()
                })
        
        # Get file sources
        if not source_type or source_type == 'file':
            file_sources = FileSource.objects.all()
            if zone:
                file_sources = file_sources.filter(zone=zone)
            if user_id:
                file_sources = file_sources.filter(created_by_id=user_id)
            if status == 'active':
                file_sources = file_sources.filter(is_active=True)
            elif status == 'inactive':
                file_sources = file_sources.filter(is_active=False)
            
            for source in file_sources:
                sources.append({
                    'source_id': str(source.source_id),
                    'source_type': 'file',
                    'name': source.name,
                    'status': 'active' if source.is_active else 'inactive',
                    'location': source.location,
                    'zone': getattr(source, 'zone', ''),
                    'created_at': source.created_at.isoformat()
                })
        
        return JsonResponse({
            'success': True,
            'sources': sources,
            'total_sources': len(sources)
        })
        
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def api_update_source(request, source_id):
    """
    Update source configuration
    
    POST /api/sources/<source_id>/update/
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Try to find the source in any of the source models
        source = None
        source_type = None
        
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
        except CameraSource.DoesNotExist:
            try:
                source = FileSource.objects.get(source_id=source_id)
                source_type = 'file'
            except FileSource.DoesNotExist:
                try:
                    source = StreamSource.objects.get(source_id=source_id)
                    source_type = 'stream'
                except StreamSource.DoesNotExist:
                    return JsonResponse({'error': 'Source not found'}, status=404)
        
        # Update fields
        if 'name' in data:
            source.name = data['name']
        if 'description' in data:
            source.description = data['description']
        if 'is_active' in data:
            source.is_active = data['is_active']
        if 'zone' in data:
            source.zone = data['zone']
        
        # Type-specific updates
        if source_type == 'camera':
            if 'camera_fps' in data:
                source.camera_fps = data['camera_fps']
            if 'camera_resolution_width' in data:
                source.camera_resolution_width = data['camera_resolution_width']
            if 'camera_resolution_height' in data:
                source.camera_resolution_height = data['camera_resolution_height']
        elif source_type == 'stream':
            if 'stream_fps' in data:
                source.stream_fps = data['stream_fps']
            if 'stream_resolution_width' in data:
                source.stream_resolution_width = data['stream_resolution_width']
            if 'stream_resolution_height' in data:
                source.stream_resolution_height = data['stream_resolution_height']
        
        source.save()
        
        return JsonResponse({
            'success': True,
            'source_id': str(source.source_id),
            'message': 'Source updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating source: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def api_delete_source(request, source_id):
    """
    Delete a registered source
    
    POST /api/sources/<source_id>/delete/
    """
    try:
        # Try to find the source in any of the source models
        source = None
        source_type = None
        
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
        except CameraSource.DoesNotExist:
            try:
                source = FileSource.objects.get(source_id=source_id)
                source_type = 'file'
            except FileSource.DoesNotExist:
                try:
                    source = StreamSource.objects.get(source_id=source_id)
                    source_type = 'stream'
                except StreamSource.DoesNotExist:
                    return JsonResponse({'error': 'Source not found'}, status=404)
        
        # Delete the source
        source.delete()
        
        return JsonResponse({
            'success': True,
            'source_id': str(source_id),
            'message': 'Source deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)

