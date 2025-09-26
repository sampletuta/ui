"""
Search API Views
Handles user-initiated searches against video sources
"""

import json
import logging
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.models import User
from django.utils import timezone
from backendapp.models import SearchQuery, SearchResult, Targets_watchlist
from source_management.models import CameraSource, FileSource, StreamSource

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def api_submit_search(request):
    """
    Submit a search request for a specific person in video sources
    
    Expected POST data:
    {
        "search_type": "image_search",
        "target_image_url": "https://example.com/target.jpg",
        "source_ids": ["550e8400-e29b-41d4-a716-446655440001"],
        "search_parameters": {
            "confidence_threshold": 0.8,
            "max_results": 10,
            "time_range_hours": 24
        },
        "user_id": "user_123"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Required fields
        required_fields = ['search_type', 'target_image_url', 'source_ids', 'user_id']
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
        
        # Validate source IDs
        source_ids = data['source_ids']
        if not isinstance(source_ids, list) or not source_ids:
            return JsonResponse({'error': 'source_ids must be a non-empty list'}, status=400)
        
        # Check if sources exist
        valid_sources = []
        for source_id in source_ids:
            source = None
            try:
                source = CameraSource.objects.get(source_id=source_id)
            except CameraSource.DoesNotExist:
                try:
                    source = FileSource.objects.get(source_id=source_id)
                except FileSource.DoesNotExist:
                    try:
                        source = StreamSource.objects.get(source_id=source_id)
                    except StreamSource.DoesNotExist:
                        return JsonResponse({'error': f'Source not found: {source_id}'}, status=404)
            
            if source and source.is_active:
                valid_sources.append(source)
            else:
                return JsonResponse({'error': f'Source is inactive: {source_id}'}, status=400)
        
        # Create search query
        search_parameters = data.get('search_parameters', {})
        search_query = SearchQuery.objects.create(
            user=user,
            query_type=data['search_type'],
            description=f"Search for person in {len(valid_sources)} sources",
            search_parameters=search_parameters,
            status='queued'
        )
        
        # Generate search ID
        search_id = str(search_query.id)
        
        # Estimate completion time (rough calculation)
        estimated_minutes = len(valid_sources) * 5  # 5 minutes per source
        estimated_completion = timezone.now() + timezone.timedelta(minutes=estimated_minutes)
        
        return JsonResponse({
            'success': True,
            'search_id': search_id,
            'status': 'queued',
            'estimated_completion': estimated_completion.isoformat(),
            'message': 'Search request submitted successfully'
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error submitting search: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_get_search_results(request, search_id):
    """
    Retrieve results for a completed search
    
    GET /api/search/results/<search_id>/
    """
    try:
        # Validate search ID format
        try:
            search_uuid = uuid.UUID(search_id)
        except ValueError:
            return JsonResponse({'error': 'Invalid search ID format'}, status=400)
        
        # Get search query
        try:
            search_query = SearchQuery.objects.get(id=search_uuid)
        except SearchQuery.DoesNotExist:
            return JsonResponse({'error': 'Search not found'}, status=404)
        
        # Check if search is completed
        if search_query.status != 'completed':
            return JsonResponse({
                'error': 'Search not completed yet',
                'status': search_query.status
            }, status=202)
        
        # Get search results
        search_results = SearchResult.objects.filter(
            search_query=search_query
        ).select_related('target', 'search_query__user')
        
        # Build results data
        results = []
        for result in search_results:
            result_data = {
                'result_id': str(result.id),
                'source_id': result.camera_id,  # Using camera_id as source_id
                'source_name': result.camera_name,
                'timestamp': result.timestamp,
                'confidence': result.confidence,
                'bounding_box': result.bounding_box or {},
                'face_image_url': result.face_image.url if result.face_image else None,
                'source_video_url': result.source_video_url,
                'source_video_timestamp': result.source_video_timestamp,
                'target_name': result.target.target_name,
                'target_id': str(result.target.id),
                'latitude': result.latitude,
                'longitude': result.longitude
            }
            results.append(result_data)
        
        # Get search metadata
        search_metadata = {
            'started_at': search_query.created_at.isoformat(),
            'completed_at': search_query.updated_at.isoformat(),
            'sources_searched': len(set(r.camera_id for r in search_results)),
            'total_frames_processed': search_query.search_parameters.get('total_frames_processed', 0)
        }
        
        return JsonResponse({
            'success': True,
            'search_id': search_id,
            'status': 'completed',
            'total_results': len(results),
            'results': results,
            'search_metadata': search_metadata
        })
        
    except Exception as e:
        logger.error(f"Error getting search results: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_get_search_status(request, search_id):
    """
    Check the status of a search request
    
    GET /api/search/status/<search_id>/
    """
    try:
        # Validate search ID format
        try:
            search_uuid = uuid.UUID(search_id)
        except ValueError:
            return JsonResponse({'error': 'Invalid search ID format'}, status=400)
        
        # Get search query
        try:
            search_query = SearchQuery.objects.get(id=search_uuid)
        except SearchQuery.DoesNotExist:
            return JsonResponse({'error': 'Search not found'}, status=404)
        
        # Calculate progress based on status
        progress = 0
        current_source = None
        estimated_completion = None
        
        if search_query.status == 'queued':
            progress = 0
        elif search_query.status == 'processing':
            progress = 50  # Rough estimate
            current_source = "Processing sources..."
        elif search_query.status == 'completed':
            progress = 100
        elif search_query.status == 'failed':
            progress = 0
        
        # Estimate completion time
        if search_query.status in ['queued', 'processing']:
            estimated_minutes = 10  # Default estimate
            estimated_completion = timezone.now() + timezone.timedelta(minutes=estimated_minutes)
        
        return JsonResponse({
            'success': True,
            'search_id': search_id,
            'status': search_query.status,
            'progress': progress,
            'current_source': current_source,
            'estimated_completion': estimated_completion.isoformat() if estimated_completion else None
        })
        
    except Exception as e:
        logger.error(f"Error getting search status: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)

