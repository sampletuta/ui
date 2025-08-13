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
    
    # Convert to format expected by video player
    video_streams = {}
    
    # Add file sources
    for idx, source in enumerate(file_sources):
        camera_id = f"file_{source.source_id}"
        # Use relative URL for streaming (works better in Docker/production)
        stream_url = f"/source-management/api/video/{source.access_token}/stream/"
        
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
        video_streams[camera_id] = {
            'id': str(source.source_id),
            'name': source.name,
            'type': 'camera',
            'liveUrl': source.get_stream_url() if hasattr(source, 'get_stream_url') else '',
            'archiveUrl': source.get_stream_url() if hasattr(source, 'get_stream_url') else '',
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
        
        # Use the correct streaming URL from source management (relative path works better)
        stream_url = f"/source-management/api/video/{source.access_token}/stream/"
        
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
        'source_type': source_type
    }
    
    return render(request, 'video_detail.html', context)

@login_required
def stream_video(request, source_id):
    """Stream video file from source management"""
    try:
        source = FileSource.objects.get(source_id=source_id)
        
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

def sample_view(request):
    # Use real-time data if available, otherwise fallback to sample data
    with data_lock:
        if video_streams_data:
            streams = video_streams_data
        else:
            # Fallback to sample data
            streams = {
                'camera_1': {
                    'name': 'Camera 1 - Main Entrance',
                    'liveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
                    'archiveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
                    'status': 'live',
                    'location': 'Main Entrance',
                    'last_detection': '2 min ago',
                    'duration': 596,  # 9:56 in seconds
                    'timeTags': [
                        {'id': 'tag_1_1', 'time': 30, 'label': 'Person detected', 'type': 'detection', 'color': '#ef4444'},
                        {'id': 'tag_1_2', 'time': 120, 'label': 'Vehicle entry', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_1_3', 'time': 240, 'label': 'Suspicious activity', 'type': 'alert', 'color': '#f59e0b'},
                        {'id': 'tag_1_4', 'time': 360, 'label': 'Door opened', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_1_5', 'time': 480, 'label': 'Motion detected', 'type': 'detection', 'color': '#ef4444'}
                    ],
                    'bookmarks': [
                        {'id': 'bookmark_1_1', 'time': 60, 'label': 'Morning shift start', 'description': 'Security guard arrives'},
                        {'id': 'bookmark_1_2', 'time': 300, 'label': 'Lunch break', 'description': 'High traffic period'},
                        {'id': 'bookmark_1_3', 'time': 450, 'label': 'Evening shift', 'description': 'Shift change time'}
                    ]
                },
                'camera_2': {
                    'name': 'Camera 2 - Parking Lot',
                    'liveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
                    'archiveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
                    'status': 'recorded',
                    'location': 'Parking Lot',
                    'last_detection': '5 min ago',
                    'duration': 653,  # 10:53 in seconds
                    'timeTags': [
                        {'id': 'tag_2_1', 'time': 45, 'label': 'Car parked', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_2_2', 'time': 180, 'label': 'Person walking', 'type': 'detection', 'color': '#ef4444'},
                        {'id': 'tag_2_3', 'time': 320, 'label': 'Vehicle exit', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_2_4', 'time': 450, 'label': 'Suspicious loitering', 'type': 'alert', 'color': '#f59e0b'},
                        {'id': 'tag_2_5', 'time': 580, 'label': 'Security check', 'type': 'event', 'color': '#10b981'}
                    ],
                    'bookmarks': [
                        {'id': 'bookmark_2_1', 'time': 90, 'label': 'Peak parking', 'description': 'Most cars arrive'},
                        {'id': 'bookmark_2_2', 'time': 400, 'label': 'Quiet period', 'description': 'Low activity'},
                        {'id': 'bookmark_2_3', 'time': 550, 'label': 'Evening exit', 'description': 'Cars leaving'}
                    ]
                },
                'camera_3': {
                    'name': 'Camera 3 - Security Gate',
                    'liveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
                    'archiveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
                    'status': 'live',
                    'location': 'Security Gate',
                    'last_detection': '1 min ago',
                    'duration': 720,  # 12:00 in seconds
                    'timeTags': [
                        {'id': 'tag_3_1', 'time': 60, 'label': 'Gate opened', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_3_2', 'time': 150, 'label': 'Unauthorized access', 'type': 'alert', 'color': '#f59e0b'},
                        {'id': 'tag_3_3', 'time': 280, 'label': 'Security breach', 'type': 'alert', 'color': '#ef4444'},
                        {'id': 'tag_3_4', 'time': 420, 'label': 'Guard response', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_3_5', 'time': 550, 'label': 'System reset', 'type': 'event', 'color': '#10b981'}
                    ],
                    'bookmarks': [
                        {'id': 'bookmark_3_1', 'time': 120, 'label': 'Morning rush', 'description': 'High traffic period'},
                        {'id': 'bookmark_3_2', 'time': 350, 'label': 'Incident report', 'description': 'Security event'},
                        {'id': 'bookmark_3_3', 'time': 600, 'label': 'Evening closure', 'description': 'Gate closing'}
                    ]
                },
                'camera_4': {
                    'name': 'Camera 4 - Loading Dock',
                    'liveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
                    'archiveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
                    'status': 'warning',
                    'location': 'Loading Dock',
                    'last_detection': '3 min ago',
                    'duration': 600,  # 10:00 in seconds
                    'timeTags': [
                        {'id': 'tag_4_1', 'time': 80, 'label': 'Truck arrival', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_4_2', 'time': 200, 'label': 'Loading started', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_4_3', 'time': 350, 'label': 'Equipment malfunction', 'type': 'alert', 'color': '#f59e0b'},
                        {'id': 'tag_4_4', 'time': 450, 'label': 'Safety violation', 'type': 'alert', 'color': '#ef4444'},
                        {'id': 'tag_4_5', 'time': 520, 'label': 'Truck departure', 'type': 'event', 'color': '#10b981'}
                    ],
                    'bookmarks': [
                        {'id': 'bookmark_4_1', 'time': 150, 'label': 'Loading peak', 'description': 'Maximum activity'},
                        {'id': 'bookmark_4_2', 'time': 380, 'label': 'Safety check', 'description': 'Protocol review'},
                        {'id': 'bookmark_4_3', 'time': 500, 'label': 'Cleanup time', 'description': 'Area preparation'}
                    ]
                },
                'camera_5': {
                    'name': 'Camera 5 - Office Area',
                    'liveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
                    'archiveUrl': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
                    'status': 'recorded',
                    'location': 'Office Area',
                    'last_detection': '8 min ago',
                    'duration': 480,  # 8:00 in seconds
                    'timeTags': [
                        {'id': 'tag_5_1', 'time': 40, 'label': 'Employee entry', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_5_2', 'time': 120, 'label': 'Meeting room activity', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_5_3', 'time': 240, 'label': 'Unauthorized access', 'type': 'alert', 'color': '#f59e0b'},
                        {'id': 'tag_5_4', 'time': 320, 'label': 'Security check', 'type': 'event', 'color': '#10b981'},
                        {'id': 'tag_5_5', 'time': 400, 'label': 'Employee exit', 'type': 'event', 'color': '#10b981'}
                    ],
                    'bookmarks': [
                        {'id': 'bookmark_5_1', 'time': 100, 'label': 'Morning meeting', 'description': 'Daily briefing'},
                        {'id': 'bookmark_5_2', 'time': 280, 'label': 'Lunch break', 'description': 'Office quiet'},
                        {'id': 'bookmark_5_3', 'time': 420, 'label': 'End of day', 'description': 'Closing procedures'}
                    ]
                }
            }
        
        if detection_events_data:
            events = detection_events_data
        else:
            # Fallback to sample detection events
            events = [
                {
                    'id': 'detection_1',
                    'camera_id': 'camera_1',
                    'camera_name': 'Camera 1 - Main Entrance',
                    'thumbnail': 'https://i.imgur.com/xVwYpWi.jpeg',
                    'time_ago': '1 min ago',
                    'status': 'live',
                    'location': 'Main Entrance',
                    'timestamp': 30,  # seconds from start
                    'time_label': '00:30'
                },
                {
                    'id': 'detection_2',
                    'camera_id': 'camera_2',
                    'camera_name': 'Camera 2 - Parking Lot',
                    'thumbnail': 'https://i.imgur.com/39N24qU.jpeg',
                    'time_ago': '2 min ago',
                    'status': 'recorded',
                    'location': 'Parking Lot',
                    'timestamp': 180,  # seconds from start
                    'time_label': '03:00'
                },
                {
                    'id': 'detection_3',
                    'camera_id': 'camera_3',
                    'camera_name': 'Camera 3 - Security Gate',
                    'thumbnail': 'https://i.imgur.com/KzXGmh4.jpeg',
                    'time_ago': '3 min ago',
                    'status': 'live',
                    'location': 'Security Gate',
                    'timestamp': 280,  # seconds from start
                    'time_label': '04:40'
                },
                {
                    'id': 'detection_4',
                    'camera_id': 'camera_4',
                    'camera_name': 'Camera 4 - Loading Dock',
                    'thumbnail': 'https://i.imgur.com/i4aYwzB.jpeg',
                    'time_ago': '4 min ago',
                    'status': 'warning',
                    'location': 'Loading Dock',
                    'timestamp': 350,  # seconds from start
                    'time_label': '05:50'
                },
                {
                    'id': 'detection_5',
                    'camera_id': 'camera_5',
                    'camera_name': 'Camera 5 - Office Area',
                    'thumbnail': 'https://i.imgur.com/fPbnMo9.jpeg',
                    'time_ago': '5 min ago',
                    'status': 'recorded',
                    'location': 'Office Area',
                    'timestamp': 240,  # seconds from start
                    'time_label': '04:00'
                },
                {
                    'id': 'detection_6',
                    'camera_id': 'camera_1',
                    'camera_name': 'Camera 1 - Main Entrance',
                    'thumbnail': 'https://i.imgur.com/yvL8hJ9.jpeg',
                    'time_ago': '8 min ago',
                    'status': 'recorded',
                    'location': 'Main Entrance',
                    'timestamp': 480,  # seconds from start
                    'time_label': '08:00'
                }
            ]
    
    return render(request, 'video_detail.html', {
        'video_streams': json.dumps(streams),
        'detection_events': events,
        'current_camera': 'camera_3'  # Default camera
    })

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
