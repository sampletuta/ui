import os
"""
Data Ingestion Service Views Module
Handles video processing via the data ingestion service (replaces FastPublisher)
"""

import re
import logging
from django.http import JsonResponse
from django.utils import timezone
from .utils import _range_streaming_response
from ..models import FileSource

logger = logging.getLogger(__name__)


def fastpublisher_status_check(request, source_id):
    """Simple status endpoint for data ingestion service to check job status"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        file_source = FileSource.objects.get(source_id=source_id)
        
        from ..models import VideoProcessingJob
        latest_job = VideoProcessingJob.objects.filter(source=file_source).order_by('-submitted_at').first()
        
        if not latest_job:
            return JsonResponse({
                'status': 'not_found',
                'message': 'No processing jobs found for this source'
            }, status=404)
        
        return JsonResponse({
            'source_id': str(source_id),
            'job_id': latest_job.job_id,
            'status': latest_job.status,
            'message': latest_job.error_message if latest_job.error_message else 'Job is processing normally',
            'processed_video_url': latest_job.processed_video_url if latest_job.processed_video_url else None
        })
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'error': 'Internal server error',
            'message': str(e)
        }, status=500)


def fastpublisher_video_access(request, source_id):
    """Unauthenticated video access endpoint for data ingestion service"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        file_source = FileSource.objects.get(source_id=source_id)
        
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


def fastpublisher_submit_video(request, source_id):
    """Unauthenticated video submission endpoint for data ingestion service"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        file_source = FileSource.objects.get(source_id=source_id)
        
        if file_source.status != 'ready':
            return JsonResponse({
                'error': 'Video not ready for processing',
                'status': file_source.status
            }, status=400)
        
        target_fps = request.POST.get('target_fps')
        target_resolution = request.POST.get('target_resolution')
        
        if not target_fps or not target_resolution:
            return JsonResponse({
                'error': 'Missing required parameters: target_fps and target_resolution'
            }, status=400)
        
        try:
            target_fps = int(target_fps)
            if not (1 <= target_fps <= 5):
                return JsonResponse({
                    'error': 'target_fps must be between 1 and 5'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'error': 'target_fps must be a valid integer'
            }, status=400)
        
        if not re.match(r'^\d+x\d+$', target_resolution):
            return JsonResponse({
                'error': 'target_resolution must be in format "widthxheight" (e.g., "640x480")'
            }, status=400)
        
        from ..services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        service_health = processing_service.health()
        result = processing_service.submit_video_processing(
            file_source, target_fps, target_resolution
        )
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': 'Video processing job submitted successfully',
                'job_id': result['job_id'],
                'external_job_id': result.get('external_job_id'),
                'estimated_completion_time': 'Calculating...',
                'processing_started_at': timezone.now().isoformat(),
                'external_service_url': result.get('external_service_url'),
                'external_service_health': service_health
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error'],
                'details': result.get('details', ''),
                'external_service_url': result.get('external_service_url'),
                'external_service_health': service_health
            }, status=500)
            
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


def fastpublisher_video_metadata(request, source_id):
    """Unauthenticated video metadata endpoint for data ingestion service"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        file_source = FileSource.objects.get(source_id=source_id)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        metadata = {
            'source_id': str(file_source.source_id),
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
            'stream_url': f"/source-management/api/public/video/{file_source.access_token}/stream/",
            'access_token': file_source.access_token,
        }
        
        return JsonResponse(metadata)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def fastpublisher_health(request):
    """Proxy health check for data ingestion service so frontend avoids CORS."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        from ..services import VideoProcessingService
        service = VideoProcessingService()
        health = service.health()
        return JsonResponse({
            'ok': health.get('ok', False),
            'url': health.get('url'),
            'status_code': health.get('status_code'),
            'error': health.get('error'),
            'response': health.get('response')
        }, status=200 if health.get('ok') else 503)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
