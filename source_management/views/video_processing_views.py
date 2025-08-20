"""
Video Processing Views Module
Handles video processing operations and job management
"""

import re
import logging
from django.http import JsonResponse
from django.utils import timezone
from .decorators import login_required_source_list
from ..models import FileSource

logger = logging.getLogger(__name__)


@login_required_source_list
def submit_video_processing(request, source_id):
    """Submit a video for processing to external service"""
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
                'processing_started_at': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error'],
                'details': result.get('details', '')
            }, status=500)
            
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required_source_list
def get_processing_status(request, job_id):
    """Get the status of a processing job"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from ..services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        result = processing_service.get_job_status(job_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'job_id': result['job_id'],
                'external_job_id': result['external_job_id'],
                'current_status': result['status'],
                'external_status': result['external_status'],
                'response': result['response']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error']
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required_source_list
def cancel_processing_job(request, job_id):
    """Cancel a processing job"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from ..services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        result = processing_service.cancel_job(job_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required_source_list
def list_processing_jobs(request, source_id):
    """List all processing jobs for a specific source"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        file_source = FileSource.objects.get(source_id=source_id)
        
        from ..models import VideoProcessingJob
        jobs = VideoProcessingJob.objects.filter(source=file_source).order_by('-submitted_at')
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'job_id': job.job_id,
                'external_job_id': job.external_job_id,
                'status': job.status,
                'target_fps': job.target_fps,
                'target_resolution': job.target_resolution,
                'submitted_at': job.submitted_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message,
                'processed_video_url': job.processed_video_url,
            })
        
        return JsonResponse({
            'status': 'success',
            'source_id': str(source_id),
            'source_name': file_source.name,
            'jobs': jobs_data,
            'total_jobs': len(jobs_data)
        })
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)
