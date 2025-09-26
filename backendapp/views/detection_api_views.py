"""
API Views for External Detection Services
Single endpoint for external services to create detections with automatic deduplication
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.utils import timezone
from backendapp.models import SearchResult, SearchQuery, Targets_watchlist
from backendapp.utils.enhanced_deduplication import enhanced_deduplication_service
from source_management.models import CameraSource, FileSource, StreamSource

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def api_create_detection(request):
    """
    Single API endpoint for external detection services
    
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
        "search_query_id": "query_456",
        "milvus_vector_id": "vec_456",
        "milvus_distance": 0.12
    }
    
    Note: Camera information (name, location, GPS coordinates) and user context 
    are automatically retrieved from the registered source.
    """
    try:
        # Parse request data
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
        
        # Get user from source ownership
        user = source.created_by
        
        # Get or create search query
        search_query_id = data.get('search_query_id')
        if search_query_id:
            try:
                search_query = SearchQuery.objects.get(id=search_query_id)
            except SearchQuery.DoesNotExist:
                return JsonResponse({'error': 'Search query not found'}, status=404)
        else:
            # Create a default search query for external detections
            search_query = SearchQuery.objects.create(
                user=user,
                query_type='external_detection',
                description=f'External detection for {target.target_name}'
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
def api_create_detection_batch(request):
    """
    Batch API endpoint for multiple detections
    
    Expected POST data:
    {
        "detections": [
            {
                "detection_id": "ext_det_123",
                "target_id": "target_789",
                "source_id": "550e8400-e29b-41d4-a716-446655440001",
                "timestamp": 1640995200.0,
                "confidence": 0.95,
                "bounding_box": {"x": 100, "y": 150, "w": 80, "h": 100}
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
                response = api_create_detection(individual_request)
                
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


@require_POST
def api_get_detection_stats(request):
    """
    Get detection statistics for a target or user
    
    Expected POST data:
    {
        "target_id": "target_789",  # optional
        "user_id": "user_123",     # optional
        "time_range_hours": 24     # optional, default 24
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        target_id = data.get('target_id')
        user_id = data.get('user_id')
        time_range_hours = data.get('time_range_hours', 24)
        
        # Build query
        query = SearchResult.objects.all()
        
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
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error getting detection stats: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@require_POST
def api_get_detection_timeline(request):
    """
    Get detection timeline for video player integration
    
    Expected POST data:
    {
        "source_id": "source_789",  # optional - filter by source
        "target_id": "target_123",  # optional - filter by target
        "video_url": "https://example.com/video.mp4",  # optional - filter by video URL
        "time_range_hours": 24  # optional, default 24
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        video_url = data.get('video_url')
        time_range_hours = data.get('time_range_hours', 24)
        
        # Build query
        query = SearchResult.objects.select_related('target', 'search_query__user').all()
        
        if target_id:
            query = query.filter(target_id=target_id)
        
        if source_id:
            # Filter by source if we have source management integration
            query = query.filter(source_video_url__icontains=source_id)
        
        if video_url:
            query = query.filter(source_video_url__icontains=video_url)
        
        # Time range filter
        if time_range_hours:
            from datetime import timedelta
            time_threshold = timezone.now() - timedelta(hours=time_range_hours)
            query = query.filter(created_at__gte=time_threshold)
        
        # Order by timestamp
        detections = query.order_by('source_video_timestamp', 'timestamp')
        
        # Build timeline data
        timeline_data = []
        for detection in detections:
            timeline_item = {
                'id': str(detection.id),
                'timestamp': detection.source_video_timestamp or detection.timestamp,
                'target_name': detection.target.target_name,
                'target_id': str(detection.target.id),
                'confidence': detection.confidence,
                'bounding_box': detection.bounding_box,
                'camera_name': detection.camera_name or 'Unknown Camera',
                'camera_id': detection.camera_id,
                'is_duplicate': detection.is_duplicate,
                'alert_created': detection.alert_created,
                'deduplication_reason': detection.deduplication_reason,
                'face_image_url': detection.face_image.url if detection.face_image else None,
                'source_video_url': detection.source_video_url,
                'latitude': detection.latitude,
                'longitude': detection.longitude,
                'created_at': detection.created_at.isoformat()
            }
            
            # Add duplicate info if applicable
            if detection.is_duplicate and detection.duplicate_of:
                timeline_item['duplicate_info'] = {
                    'original_detection_id': str(detection.duplicate_of.id),
                    'original_timestamp': detection.duplicate_of.timestamp
                }
            
            timeline_data.append(timeline_item)
        
        return JsonResponse({
            'success': True,
            'timeline': timeline_data,
            'total_detections': len(timeline_data),
            'filters': {
                'source_id': source_id,
                'target_id': target_id,
                'video_url': video_url,
                'time_range_hours': time_range_hours
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error getting detection timeline: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)
