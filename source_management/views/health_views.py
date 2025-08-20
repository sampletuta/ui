"""
Health Views Module
Handles health checks for external services
"""

from django.http import JsonResponse
from ..services import DataIngestionService


def data_ingestion_health(request):
    """Check data ingestion service health."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        service = DataIngestionService()
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


def data_ingestion_source_status(request, source_id):
    """Get the processing status of a source from the data ingestion service."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        service = DataIngestionService()
        status_result = service.get_source_status(source_id)
        
        if status_result['success']:
            return JsonResponse(status_result['status'])
        else:
            return JsonResponse({
                'error': status_result['error'],
                'details': status_result.get('details', ''),
                'external_service_url': status_result.get('external_service_url')
            }, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
