"""
Stream Control Views Module
Handles stream processor service operations (start/stop/status)
"""

import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..models import CameraSource, StreamSource
from .decorators import login_required_source_list

logger = logging.getLogger(__name__)


@login_required_source_list
def stream_create(request, source_id):
    """Create/register stream in processor service for a camera or stream source"""
    try:
        # Find the source
        source = None
        try:
            source = CameraSource.objects.get(source_id=source_id)
        except CameraSource.DoesNotExist:
            try:
                source = StreamSource.objects.get(source_id=source_id)
            except StreamSource.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Source not found'}, status=404)
        
        if not source.is_active:
            return JsonResponse({'success': False, 'error': 'Source is not active'}, status=400)
        
        # Create the stream in the processor service
        source._create_in_stream_processor()
        
        return JsonResponse({
            'success': True, 
            'message': f'Stream registered successfully for {source.name}'
        })
            
    except Exception as e:
        logger.error(f"Error creating stream for source {source_id}: {e}")
        return JsonResponse({
            'success': False, 
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@login_required_source_list
def stream_submit(request, source_id):
    """Submit stream data to processor service for ingestion"""
    try:
        # Find the source
        source = None
        try:
            source = CameraSource.objects.get(source_id=source_id)
        except CameraSource.DoesNotExist:
            try:
                source = StreamSource.objects.get(source_id=source_id)
            except StreamSource.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Source not found'}, status=404)
        
        if not source.is_active:
            return JsonResponse({'success': False, 'error': 'Source is not active'}, status=400)
        
        # Submit the stream data to the processor service
        # This will send the full stream payload to the service for ingestion
        payload = source.get_stream_processor_payload()
        result = source._call_stream_processor_api('POST', '/api/external/streams', data=payload)
        
        if result.get('success'):
            return JsonResponse({
                'success': True, 
                'message': f'Stream data submitted successfully for {source.name}',
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': result.get('error', 'Failed to submit stream data')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error submitting stream data for source {source_id}: {e}")
        return JsonResponse({
            'success': False, 
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@login_required_source_list
def stream_start(request, source_id):
    """Start stream processing for a camera or stream source"""
    try:
        # Find the source
        source = None
        try:
            source = CameraSource.objects.get(source_id=source_id)
        except CameraSource.DoesNotExist:
            try:
                source = StreamSource.objects.get(source_id=source_id)
            except StreamSource.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Source not found'}, status=404)
        
        if not source.is_active:
            return JsonResponse({'success': False, 'error': 'Source is not active'}, status=400)
        
        # Start the stream in the processor service
        result = source.start_processor_stream()
        
        if result.get('success'):
            return JsonResponse({
                'success': True, 
                'message': f'Stream started successfully for {source.name}',
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': result.get('error', 'Failed to start stream')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error starting stream for source {source_id}: {e}")
        return JsonResponse({
            'success': False, 
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@login_required_source_list
def stream_stop(request, source_id):
    """Stop stream processing for a camera or stream source"""
    try:
        # Find the source
        source = None
        try:
            source = CameraSource.objects.get(source_id=source_id)
        except CameraSource.DoesNotExist:
            try:
                source = StreamSource.objects.get(source_id=source_id)
            except StreamSource.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Source not found'}, status=404)
        
        # Stop the stream in the processor service
        result = source.stop_processor_stream()
        
        if result.get('success'):
            return JsonResponse({
                'success': True, 
                'message': f'Stream stopped successfully for {source.name}',
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': result.get('error', 'Failed to stop stream')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error stopping stream for source {source_id}: {e}")
        return JsonResponse({
            'success': False, 
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@login_required_source_list
def stream_status(request, source_id):
    """Get stream processing status for a camera or stream source"""
    try:
        # Find the source
        source = None
        try:
            source = CameraSource.objects.get(source_id=source_id)
        except CameraSource.DoesNotExist:
            try:
                source = StreamSource.objects.get(source_id=source_id)
            except StreamSource.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Source not found'}, status=404)
        
        # Get the stream status from the processor service
        result = source.get_processor_status()
        
        return JsonResponse(result)
            
    except Exception as e:
        logger.error(f"Error getting stream status for source {source_id}: {e}")
        return JsonResponse({
            'success': False, 
            'error': f'Internal server error: {str(e)}'
        }, status=500)
