# video_player/views.py

from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Video
from source_management.models import FileSource, CameraSource, StreamSource
import json
import asyncio
from asgiref.sync import sync_to_async
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import os
import re
from urllib.parse import unquote

# Global storage for real-time data
video_streams_data = {}
detection_events_data = []
data_lock = threading.Lock()

@login_required
def video_detail(request, video_id):
    video = get_object_or_404(Video, pk=video_id)
    chapters = video.chapters.order_by('start_time')
    return render(request, 'video_detail.html', {
        'video': video,
        'chapters': chapters
    })

def zm_live_stream(request, monitor_id):
    zm_url = f"http://zoneminder-host/zm/cgi-bin/nph-zms?mode=jpeg&monitor={monitor_id}&scale=100&maxfps=30"
    return HttpResponseRedirect(zm_url)

# API Endpoint to receive video streams data
@csrf_exempt
@require_http_methods(["POST"])
def api_receive_video_streams(request):
    """
    API endpoint to receive video streams data from external services
    Expected JSON format:
    {
        "camera_id": {
            "name": "Camera Name",
            "liveUrl": "https://...",
            "archiveUrl": "https://...",
            "status": "live|recorded|warning",
            "location": "Location",
            "last_detection": "time ago",
            "duration": seconds,
            "timeTags": [...],
            "bookmarks": [...]
        }
    }
    """
    try:
        data = json.loads(request.body)
        
        with data_lock:
            global video_streams_data
            video_streams_data.update(data)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Received {len(data)} video streams',
            'timestamp': time.time()
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON format'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# API Endpoint to receive detection events
@csrf_exempt
@require_http_methods(["POST"])
def api_receive_detection_events(request):
    """
    API endpoint to receive detection events from external services
    Expected JSON format:
    [
        {
            "id": "detection_id",
            "camera_id": "camera_id",
            "camera_name": "Camera Name",
            "thumbnail": "https://...",
            "time_ago": "time ago",
            "status": "live|recorded|warning",
            "location": "Location",
            "timestamp": seconds,
            "time_label": "MM:SS"
        }
    ]
    """
    try:
        data = json.loads(request.body)
        
        if not isinstance(data, list):
            return JsonResponse({
                'status': 'error',
                'message': 'Data must be a list of detection events'
            }, status=400)
        
        with data_lock:
            global detection_events_data
            detection_events_data = data
        
        return JsonResponse({
            'status': 'success',
            'message': f'Received {len(data)} detection events',
            'timestamp': time.time()
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON format'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# API Endpoint to get current video streams data
@require_http_methods(["GET"])
def api_get_video_streams(request):
    """
    API endpoint to retrieve current video streams data
    """
    with data_lock:
        return JsonResponse({
            'status': 'success',
            'data': video_streams_data,
            'timestamp': time.time()
        })

# API Endpoint to get current detection events
@require_http_methods(["GET"])
def api_get_detection_events(request):
    """
    API endpoint to retrieve current detection events
    """
    with data_lock:
        return JsonResponse({
            'status': 'success',
            'data': detection_events_data,
            'timestamp': time.time()
        })

# API Endpoint to update specific camera data
@csrf_exempt
@require_http_methods(["PUT"])
def api_update_camera(request, camera_id):
    """
    API endpoint to update specific camera data
    """
    try:
        data = json.loads(request.body)
        
        with data_lock:
            global video_streams_data
            if camera_id in video_streams_data:
                video_streams_data[camera_id].update(data)
            else:
                video_streams_data[camera_id] = data
        
        return JsonResponse({
            'status': 'success',
            'message': f'Updated camera {camera_id}',
            'timestamp': time.time()
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON format'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# API Endpoint to add single detection event
@csrf_exempt
@require_http_methods(["POST"])
def api_add_detection_event(request):
    """
    API endpoint to add a single detection event
    """
    try:
        data = json.loads(request.body)
        
        with data_lock:
            global detection_events_data
            detection_events_data.append(data)
            
            # Keep only last 50 events to prevent memory issues
            if len(detection_events_data) > 50:
                detection_events_data = detection_events_data[-50:]
        
        return JsonResponse({
            'status': 'success',
            'message': 'Detection event added',
            'timestamp': time.time()
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON format'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# API Endpoint to clear all data
@csrf_exempt
@require_http_methods(["DELETE"])
def api_clear_data(request):
    """
    API endpoint to clear all video streams and detection events
    """
    with data_lock:
        global video_streams_data, detection_events_data
        video_streams_data.clear()
        detection_events_data.clear()
    
    return JsonResponse({
        'status': 'success',
        'message': 'All data cleared',
        'timestamp': time.time()
    })

@login_required
def source_video_list(request):
    """List all video sources from source management"""
    # Get all video sources
    file_sources = FileSource.objects.filter(status='ready').order_by('-created_at')
    camera_sources = CameraSource.objects.filter(is_active=True).order_by('-created_at')
    stream_sources = StreamSource.objects.all().order_by('-created_at')
    
    # Debug logging
    print(f"DEBUG: Found {file_sources.count()} file sources with status='ready'")
    print(f"DEBUG: Found {camera_sources.count()} active camera sources")
    print(f"DEBUG: Found {stream_sources.count()} stream sources")
    
    # For debugging, also check all file sources regardless of status
    all_file_sources = FileSource.objects.all()
    print(f"DEBUG: Total file sources (all statuses): {all_file_sources.count()}")
    for fs in all_file_sources:
        print(f"DEBUG: File source {fs.source_id}: {fs.name} - status: {fs.status}")
    
    # Convert to format expected by video player
    video_streams = {}
    
    # Add file sources
    for idx, source in enumerate(file_sources):
        camera_id = f"file_{source.source_id}"
        # Use correct streaming URL that matches the stream_video view
        stream_url = f"/video/stream/{source.source_id}/"
        
        video_streams[camera_id] = {
            'id': str(source.source_id),
            'name': source.name,
            'type': 'file',
            'liveUrl': stream_url,
            'archiveUrl': stream_url,
            'status': 'recorded',
            'location': source.location or 'Unknown',
            'last_detection': 'File source',
            'duration': source.duration or 0,
            'resolution': f"{source.width}x{source.height}" if source.width and source.height else "Unknown",
            'file_size': source.get_file_size_display() if hasattr(source, 'get_file_size_display') else 'Unknown',
            'created_at': source.created_at.isoformat(),
            'access_token': source.access_token,
            'timeTags': [],
            'bookmarks': []
        }
    
    # Add camera sources
    for idx, source in enumerate(camera_sources):
        camera_id = f"camera_{source.source_id}"
        # Construct RTSP URL for camera sources
        if source.camera_protocol == 'rtsp':
            live_url = f"rtsp://{source.camera_username}:{source.camera_password}@{source.camera_ip}:{source.camera_port}/stream"
        else:
            live_url = f"{source.camera_protocol}://{source.camera_ip}:{source.camera_port}/stream"
        
        video_streams[camera_id] = {
            'id': str(source.source_id),
            'name': source.name,
            'type': 'camera',
            'liveUrl': live_url,
            'archiveUrl': live_url,
            'status': 'live' if source.is_active else 'inactive',
            'location': source.location or 'Unknown',
            'last_detection': 'Live camera',
            'duration': 0,
            'resolution': source.camera_resolution or 'Unknown',
            'camera_ip': source.camera_ip,
            'camera_port': source.camera_port,
            'created_at': source.created_at.isoformat(),
            'timeTags': [],
            'bookmarks': []
        }
    
    # Add stream sources
    for idx, source in enumerate(stream_sources):
        camera_id = f"stream_{source.source_id}"
        video_streams[camera_id] = {
            'id': str(source.source_id),
            'name': source.name,
            'type': 'stream',
            'liveUrl': source.stream_url,
            'archiveUrl': source.stream_url,
            'status': 'live',
            'location': source.location or 'Unknown',
            'last_detection': 'Live stream',
            'duration': 0,
            'resolution': source.stream_quality or 'Unknown',
            'stream_protocol': source.stream_protocol,
            'created_at': source.created_at.isoformat(),
            'timeTags': [],
            'bookmarks': []
        }
    
    # Set default camera
    current_camera = list(video_streams.keys())[0] if video_streams else 'no_camera'
    
    # Empty detection events for now
    detection_events = []
    
    context = {
        'video_streams': json.dumps(video_streams),
        'detection_events': detection_events,
        'current_camera': current_camera,
        'sources_count': len(video_streams)
    }
    
    return render(request, 'video_detail.html', context)

@login_required
def source_video_detail(request, source_id):
    """View specific video source"""
    
    source = None
    source_type = None
    
    # Try to find the source
    try:
        source = FileSource.objects.get(source_id=source_id)
        source_type = 'file'
    except FileSource.DoesNotExist:
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
        except CameraSource.DoesNotExist:
            try:
                source = StreamSource.objects.get(source_id=source_id)
                source_type = 'stream'
            except StreamSource.DoesNotExist:
                pass
    
    if not source:
        from django.contrib import messages
        messages.error(request, 'Video source not found.')
        return render(request, 'video_detail.html', {
            'video_streams': json.dumps({}),
            'detection_events': [],
            'current_camera': 'no_camera',
            'sources_count': 0,
            'error_message': 'Video source not found.'
        })
    
    # Convert to video player format
    camera_id = f"{source_type}_{source.source_id}"
    video_streams = {
        camera_id: {
            'id': str(source.source_id),
            'name': source.name,
            'type': source_type,
            'status': getattr(source, 'status', 'active'),
            'location': source.location or 'Unknown',
            'created_at': source.created_at.isoformat(),
            'timeTags': [],
            'bookmarks': []
        }
    }
    
    # Add type-specific data
    if source_type == 'file':
        if source.status != 'ready':
            from django.contrib import messages
            messages.error(request, f'Video not ready. Status: {source.status}')
            return render(request, 'video_detail.html', {
                'video_streams': json.dumps({}),
                'detection_events': [],
                'current_camera': 'no_camera',
                'sources_count': 0,
                'error_message': f'Video not ready. Status: {source.status}'
            })
        
        # Use the correct streaming URL that matches the stream_video view
        stream_url = f"/video/stream/{source.source_id}/"
        
        video_streams[camera_id].update({
            'liveUrl': stream_url,
            'archiveUrl': stream_url,
            'status': 'recorded',
            'duration': source.duration or 0,
            'resolution': f"{source.width}x{source.height}" if source.width and source.height else "Unknown",
            'file_size': source.get_file_size_display() if hasattr(source, 'get_file_size_display') else 'Unknown',
            'access_token': source.access_token,
        })
    elif source_type == 'camera':
        video_streams[camera_id].update({
            'liveUrl': source.get_stream_url() if hasattr(source, 'get_stream_url') else '',
            'archiveUrl': source.get_stream_url() if hasattr(source, 'get_stream_url') else '',
            'status': 'live' if source.is_active else 'inactive',
            'resolution': source.camera_resolution or 'Unknown',
            'camera_ip': source.camera_ip,
            'camera_port': source.camera_port,
        })
    elif source_type == 'stream':
        video_streams[camera_id].update({
            'liveUrl': source.stream_url,
            'archiveUrl': source.stream_url,
            'status': 'live',
            'resolution': source.stream_quality or 'Unknown',
            'stream_protocol': source.stream_protocol,
        })
    
    context = {
        'video_streams': json.dumps(video_streams),
        'detection_events': [],
        'current_camera': camera_id,
        'source': source,
        'source_type': source_type,
        'sources_count': len(video_streams)
    }
    
    return render(request, 'video_detail.html', context)

@login_required
def stream_video(request, source_id):
    """Stream video file from source management"""
    
    try:
        source = FileSource.objects.get(source_id=source_id)
        
        # For debugging, allow all statuses temporarily
        if source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        file_path = video_file.path
        
        if not os.path.exists(file_path):
            return JsonResponse({'error': 'Video file not found on disk'}, status=404)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Handle range requests for streaming
        range_header = request.META.get('HTTP_RANGE', '').strip()
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            if start >= file_size:
                return HttpResponse(status=416)
            
            # Read the requested range
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)
            
            response = HttpResponse(data, content_type='video/mp4')
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = len(data)
            response.status_code = 206
            
            return response
        else:
            # Return full file
            response = StreamingHttpResponse(
                open(file_path, 'rb'),
                content_type='video/mp4'
            )
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = file_size
            
            return response
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video source not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def play_from_url(request):
    """Play a single video by direct URL (for integrations like search results).

    Query params:
    - url: required, the media URL to play (mp4, webm, m3u8, etc.)
    - name: optional, display name (default: "External Video")
    - t: optional, initial seek seconds (float or int)
    """
    try:
        url = request.GET.get('url')
        if not url:
            return JsonResponse({'error': 'Missing url parameter'}, status=400)

        # Decode if URL-encoded
        url = unquote(url)
        name = request.GET.get('name') or 'External Video'

        # Initial seek time
        t_param = request.GET.get('t')
        try:
            initial_seek = float(t_param) if t_param not in (None, '') else 0
        except ValueError:
            initial_seek = 0

        camera_id = 'external_1'
        video_streams = {
            camera_id: {
                'id': camera_id,
                'name': name,
                'type': 'external',
                'liveUrl': url,
                'archiveUrl': url,
                'status': 'recorded',
                'location': 'External',
                'last_detection': '',
                'duration': 0,
                'timeTags': [],
                'bookmarks': []
            }
        }

        context = {
            'video_streams': json.dumps(video_streams),
            'detection_events': [],
            'current_camera': camera_id,
            'sources_count': 1,
            'initial_seek': initial_seek,
        }

        return render(request, 'video_detail.html', context)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def source_streaming_integration(request):
    """Integration page for streaming source management sources."""
    from source_management.models import FileSource, CameraSource, StreamSource
    
    # Get all available sources
    sources = []
    
    # Add file sources
    file_sources = FileSource.objects.filter(status='ready')
    for source in file_sources:
        source.source_type = 'file'
        sources.append(source)
    
    # Add camera sources
    camera_sources = CameraSource.objects.filter(is_active=True)
    for source in camera_sources:
        source.source_type = 'camera'
        sources.append(source)
    
    # Add stream sources
    stream_sources = StreamSource.objects.filter(is_active=True)
    for source in stream_sources:
        source.source_type = 'stream'
        sources.append(source)
    
    return render(request, 'source_streaming_integration.html', {
        'sources': sources
    })


@csrf_exempt
def rtsp_proxy(request):
    """Proxy endpoint to convert RTSP streams to HTTP streams."""
    try:
        rtsp_url = request.GET.get('url')
        if not rtsp_url:
            return JsonResponse({'error': 'Missing RTSP URL'}, status=400)
        
        # For now, return a message about RTSP support
        # In production, you would implement actual RTSP to HTTP conversion
        return JsonResponse({
            'message': 'RTSP proxy endpoint - implement conversion logic',
            'rtsp_url': rtsp_url,
            'note': 'This endpoint should convert RTSP to HTTP using FFmpeg or similar'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def rtmp_proxy(request):
    """Proxy endpoint to convert RTMP streams to HTTP streams."""
    try:
        rtmp_url = request.GET.get('url')
        if not rtmp_url:
            return JsonResponse({'error': 'Missing RTMP URL'}, status=400)
        
        # For now, return a message about RTMP support
        # In production, you would implement actual RTMP to HTTP conversion
        return JsonResponse({
            'message': 'RTMP proxy endpoint - implement conversion logic',
            'rtmp_url': rtmp_url,
            'note': 'This endpoint should convert RTMP to HTTP using FFmpeg or similar'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
