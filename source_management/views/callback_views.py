"""
Callback Views Module
Handles external service callbacks
"""

import json
import logging
from django.http import JsonResponse
from ..models import VideoProcessingJob

logger = logging.getLogger(__name__)


def processing_callback(request, access_token):
    """Callback endpoint for external processing service"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        processing_job = VideoProcessingJob.objects.get(access_token=access_token)
        
        callback_data = json.loads(request.body)
        
        new_status = callback_data.get('status', 'unknown')
        if new_status in ['completed', 'failed']:
            processing_job.update_status(
                new_status,
                external_response=callback_data,
                processed_video_url=callback_data.get('processed_video_url', ''),
                processing_metadata=callback_data.get('processing_metadata', {})
            )
        
        logger.info(f"Received callback for job {processing_job.job_id}: {new_status}")
        
        return JsonResponse({'status': 'success', 'message': 'Callback processed'})
        
    except VideoProcessingJob.DoesNotExist:
        return JsonResponse({'error': 'Invalid access token'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in callback'}, status=400)
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
