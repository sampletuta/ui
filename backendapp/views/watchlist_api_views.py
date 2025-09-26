"""
Watchlist Monitoring API Views
Handles external services monitoring watchlists and submitting detections
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.models import User
from django.utils import timezone
from backendapp.models import SearchResult, SearchQuery, Targets_watchlist
from backendapp.utils.enhanced_deduplication import enhanced_deduplication_service
from source_management.models import CameraSource, FileSource, StreamSource

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def api_submit_detection(request):
    """
    Submit face detection results from external AI services monitoring watchlists
    
    Expected POST data:
    {
        "detection_id": "ext_det_123",
        "target_id": "target_789",
        "source_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": 1640995200.0,
        "confidence": 0.95,
        "bounding_box": {"x": 100, "y": 150, "w": 80, "h": 100},
        "face_image_url": "https://example.com/face.jpg",
        "source_video_timestamp": 120.5,
        "milvus_vector_id": "vec_456",
        "milvus_distance": 0.12
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Required fields
        required_fields = ['target_id', 'source_id', 'timestamp', 'confidence']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate target exists
        try:
            target = Targets_watchlist.objects.get(id=data['target_id'])
        except Targets_watchlist.DoesNotExist:
            return JsonResponse({'error': 'Target not found'}, status=404)
        
        # Validate source exists and get source information
        source = None
        try:
            # Try to find the source in any of the source models
            source = CameraSource.objects.get(source_id=data['source_id'])
        except CameraSource.DoesNotExist:
            try:
                source = FileSource.objects.get(source_id=data['source_id'])
            except FileSource.DoesNotExist:
                try:
                    source = StreamSource.objects.get(source_id=data['source_id'])
                except StreamSource.DoesNotExist:
                    return JsonResponse({'error': 'Source not found'}, status=404)
        
        # Check if source is active
        if not source.is_active:
            return JsonResponse({'error': 'Source is inactive'}, status=400)
        
        # Get user from source ownership
        user = source.created_by
        
        # Get or create search query for watchlist monitoring
        search_query, created = SearchQuery.objects.get_or_create(
            user=user,
            query_type='watchlist_monitoring',
            defaults={
                'description': f'Watchlist monitoring for {target.target_name}',
                'status': 'active'
            }
        )
        
        # Get source information for SearchResult
        source_info = source.get_source_info()
        
        # Determine camera_id and camera_name based on source type
        if isinstance(source, CameraSource):
            camera_id = str(source.source_id)
            camera_name = source.name
            source_video_url = source.get_camera_url()
        elif isinstance(source, FileSource):
            camera_id = str(source.source_id)
            camera_name = source.name
            source_video_url = source.stream_url or source.api_endpoint
        elif isinstance(source, StreamSource):
            camera_id = str(source.source_id)
            camera_name = source.name
            source_video_url = source.stream_url
        else:
            camera_id = str(source.source_id)
            camera_name = source.name
            source_video_url = None
        
        # Create SearchResult
        search_result = SearchResult.objects.create(
            search_query=search_query,
            target=target,
            timestamp=data['timestamp'],
            confidence=data['confidence'],
            bounding_box=data.get('bounding_box', {}),
            latitude=source_info.get('latitude'),
            longitude=source_info.get('longitude'),
            camera_id=camera_id,
            camera_name=camera_name,
            source_video_url=source_video_url,
            source_video_timestamp=data.get('source_video_timestamp'),
            milvus_vector_id=data.get('milvus_vector_id'),
            milvus_distance=data.get('milvus_distance'),
            external_detection_id=data.get('detection_id'),
            detection_source='external'
        )
        
        # Prepare response
        response_data = {
            'success': True,
            'detection_id': str(search_result.id),
            'stored': not search_result.is_duplicate,
            'is_duplicate': search_result.is_duplicate,
            'alert_created': search_result.alert_created,
            'deduplication_info': {
                'storage_reason': search_result.deduplication_reason or 'new_detection',
                'alert_reason': 'alert_created' if search_result.alert_created else 'deduplicated'
            }
        }
        
        # Add additional info if duplicate
        if search_result.is_duplicate and search_result.duplicate_of:
            response_data['duplicate_info'] = {
                'original_detection_id': str(search_result.duplicate_of.id),
                'original_timestamp': search_result.duplicate_of.timestamp
            }
        
        return JsonResponse(response_data, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating detection: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_POST
def api_submit_batch_detections(request):
    """
    Submit multiple detections in a single request
    
    Expected POST data:
    {
        "detections": [
            {
                "detection_id": "ext_det_123",
                "target_id": "target_789",
                "source_id": "550e8400-e29b-41d4-a716-446655440001",
                "timestamp": 1640995200.0,
                "confidence": 0.95
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        detections = data.get('detections', [])
        
        if not isinstance(detections, list):
            return JsonResponse({'error': 'Detections must be a list'}, status=400)
        
        if len(detections) > 100:  # Limit batch size
            return JsonResponse({'error': 'Batch size too large (max 100)'}, status=400)
        
        results = []
        errors = []
        
        for i, detection_data in enumerate(detections):
            try:
                # Create individual detection
                individual_request = type('Request', (), {'body': json.dumps(detection_data)})()
                response = api_submit_detection(individual_request)
                
                if response.status_code == 201:
                    results.append(json.loads(response.content))
                else:
                    errors.append({
                        'index': i,
                        'error': json.loads(response.content)['error']
                    })
                    
            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'total_processed': len(detections),
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error processing batch detections: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_get_watchlist_targets(request):
    """
    Get list of watchlist targets for external services
    
    GET /api/watchlist/targets/
    """
    try:
        # Get all active watchlist targets
        targets = Targets_watchlist.objects.select_related('case', 'created_by').prefetch_related('images').filter(
            is_active=True
        )
        
        # Build targets data
        targets_data = []
        for target in targets:
            target_data = {
                'target_id': str(target.id),
                'target_name': target.target_name,
                'target_images': [
                    image.image.url for image in target.images.all()
                ],
                'case_id': str(target.case.id) if target.case else None,
                'case_name': target.case.case_name if target.case else None,
                'created_at': target.created_at.isoformat(),
                'is_active': target.is_active,
                'target_text': target.target_text,
                'target_email': target.target_email,
                'target_phone': target.target_phone
            }
            targets_data.append(target_data)
        
        return JsonResponse({
            'success': True,
            'targets': targets_data,
            'total_targets': len(targets_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting watchlist targets: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_get_detection_stats(request):
    """
    Get detection statistics for a target or user
    
    GET /api/watchlist/stats/
    Query Parameters:
    - target_id: Filter by target ID
    - user_id: Filter by user ID
    - time_range_hours: Time range in hours (default 24)
    """
    try:
        target_id = request.GET.get('target_id')
        user_id = request.GET.get('user_id')
        time_range_hours = int(request.GET.get('time_range_hours', 24))
        
        # Build query
        query = SearchResult.objects.filter(detection_source='external')
        
        if target_id:
            query = query.filter(target_id=target_id)
        
        if user_id:
            query = query.filter(search_query__user_id=user_id)
        
        # Time range filter
        if time_range_hours:
            from datetime import timedelta
            time_threshold = timezone.now() - timedelta(hours=time_range_hours)
            query = query.filter(created_at__gte=time_threshold)
        
        # Get statistics
        total_detections = query.count()
        unique_detections = query.filter(is_duplicate=False).count()
        duplicate_detections = query.filter(is_duplicate=True).count()
        alerts_created = query.filter(alert_created=True).count()
        
        # Get deduplication stats
        deduplication_stats = enhanced_deduplication_service.get_deduplication_stats()
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'total_detections': total_detections,
                'unique_detections': unique_detections,
                'duplicate_detections': duplicate_detections,
                'alerts_created': alerts_created,
                'duplicate_rate': (duplicate_detections / total_detections * 100) if total_detections > 0 else 0,
                'alert_rate': (alerts_created / total_detections * 100) if total_detections > 0 else 0
            },
            'deduplication_config': deduplication_stats,
            'time_range_hours': time_range_hours
        })
        
    except Exception as e:
        logger.error(f"Error getting detection stats: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)

