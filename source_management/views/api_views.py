"""
API Views Module
Handles API endpoints for source metadata and video access
"""

import os
import logging
from django.http import JsonResponse
from .decorators import login_required_source_list
from .utils import _range_streaming_response
from ..models import CameraSource, FileSource, StreamSource

logger = logging.getLogger(__name__)


@login_required_source_list
def api_source_metadata(request, source_id):
    """API endpoint to get source metadata"""
    try:
        source = None
        source_type = None
        
        try:
            source = FileSource.objects.get(source_id=source_id)
            source_type = 'file'
        except FileSource.DoesNotExist:
            pass
        
        if not source:
            try:
                source = CameraSource.objects.get(source_id=source_id)
                source_type = 'camera'
            except CameraSource.DoesNotExist:
                pass
        
        if not source:
            try:
                source = StreamSource.objects.get(source_id=source_id)
                source_type = 'stream'
            except StreamSource.DoesNotExist:
                pass
        
        if not source:
            return JsonResponse({'error': 'Source not found'}, status=404)
        
        metadata = {
            'id': str(source.source_id),
            'name': source.name,
            'type': source_type,
            'description': source.description,
            'location': source.location,
            'created_at': source.created_at.isoformat(),
            'updated_at': source.updated_at.isoformat(),
        }
        
        if source_type == 'file':
            metadata.update({
                'status': source.status,
                'file_size': source.file_size,
                'duration': source.duration,
                'resolution': f"{source.width}x{source.height}" if source.width and source.height else None,
                'fps': source.fps,
                'codec': source.codec,
                'access_token': source.access_token,
                'api_endpoint': source.api_endpoint,
                'stream_url': source.stream_url,
                'thumbnail_url': source.thumbnail_url,
            })
        elif source_type == 'camera':
            metadata.update({
                'camera_ip': source.camera_ip,
                'camera_port': source.camera_port,
                'camera_protocol': source.camera_protocol,
                'is_active': source.is_active,
            })
        elif source_type == 'stream':
            metadata.update({
                'stream_url': source.stream_url,
                'stream_protocol': source.stream_protocol,
                'stream_quality': source.stream_quality,
            })
        
        return JsonResponse(metadata)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required_source_list
def api_video_access(request, access_token):
    """API endpoint for video access using access token (authenticated)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({
                'error': 'Video not ready',
                'status': file_source.status
            }, status=400)
        
        response_data = {
            'id': str(file_source.source_id),
            'name': file_source.name,
            'description': file_source.description,
            'status': file_source.status,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'resolution': f"{file_source.width}x{file_source.height}" if file_source.width and file_source.height else None,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'bitrate': file_source.bitrate,
            'created_at': file_source.created_at.isoformat(),
            'download_url': f"/source-management/api/video/{access_token}/download/",
            'stream_url': f"/source-management/api/video/{access_token}/stream/",
            'thumbnail_url': f"/source-management/api/video/{access_token}/thumbnail/",
        }
        
        return JsonResponse(response_data)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_video_access_public(request, access_token):
    """Public API endpoint for video access using access token (no authentication required)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({
                'error': 'Video not ready',
                'status': file_source.status
            }, status=400)
        
        response_data = {
            'id': str(file_source.source_id),
            'name': file_source.name,
            'description': file_source.description,
            'status': file_source.status,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'resolution': f"{file_source.width}x{file_source.height}" if file_source.width and file_source.height else None,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'bitrate': file_source.bitrate,
            'created_at': file_source.created_at.isoformat(),
            'download_url': f"/source-management/api/video/{access_token}/download/",
            'stream_url': f"/source-management/api/video/{access_token}/stream/",
            'thumbnail_url': f"/source-management/api/video/{access_token}/thumbnail/",
        }
        
        return JsonResponse(response_data)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required_source_list
def api_video_metadata(request, access_token):
    """API endpoint for video metadata (authenticated)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        metadata = {
            'id': str(file_source.source_id),
            'name': file_source.name,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'width': file_source.width,
            'height': file_source.height,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'audio_channels': file_source.audio_channels,
            'audio_sample_rate': file_source.audio_sample_rate,
            'bitrate': file_source.bitrate,
            'file_format': file_source.file_format,
            'status': file_source.status,
        }
        
        return JsonResponse(metadata)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_video_metadata_public(request, access_token):
    """Public API endpoint for video metadata (no authentication required)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        metadata = {
            'id': str(file_source.source_id),
            'name': file_source.name,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'width': file_source.width,
            'height': file_source.height,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'audio_channels': file_source.audio_channels,
            'audio_sample_rate': file_source.audio_sample_rate,
            'bitrate': file_source.bitrate,
            'file_format': file_source.file_format,
            'status': file_source.status,
        }
        
        return JsonResponse(metadata)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required_source_list
def api_video_download(request, access_token):
    """API endpoint for video download (authenticated)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        from django.http import FileResponse
        response = FileResponse(video_file.open('rb'), as_attachment=True, filename=os.path.basename(video_file.name), content_type='video/mp4')
        return response
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_video_download_public(request, access_token):
    """Public API endpoint for video download (no authentication required)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        from django.http import FileResponse
        response = FileResponse(video_file.open('rb'), as_attachment=True, filename=os.path.basename(video_file.name), content_type='video/mp4')
        return response
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required_source_list
def api_video_stream(request, access_token):
    """API endpoint for video streaming (authenticated)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        file_path = video_file.path
        
        if not os.path.exists(file_path):
            return JsonResponse({'error': 'Video file not found on disk'}, status=404)
        
        return _range_streaming_response(request, file_path, content_type='video/mp4')
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_video_stream_public(request, access_token):
    """Public API endpoint for video streaming (no authentication required)"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        file_path = video_file.path
        
        if not os.path.exists(file_path):
            return JsonResponse({'error': 'Video file not found on disk'}, status=404)
        
        return _range_streaming_response(request, file_path, content_type='video/mp4')
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
