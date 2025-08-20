"""
Face Verification Status Checking Module
Provides comprehensive status checking for all face verification services
"""

import logging
from typing import Dict, List, Any
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

class FaceVerificationStatus:
    """Class to handle face verification service status checking"""
    
    @staticmethod
    def check_milvus_status() -> Dict[str, Any]:
        """Check Milvus vector database status"""
        try:
            from face_ai.services.milvus_service import MilvusService
            milvus_service = MilvusService()
            status = milvus_service.check_collection_status()
            return {
                'service': 'Milvus Vector Database',
                'status': status.get('status', 'unknown'),
                'message': status.get('message', 'Status check failed'),
                'details': status,
                'healthy': status.get('status') == 'success'
            }
        except ImportError as e:
            return {
                'service': 'Milvus Vector Database',
                'status': 'error',
                'message': f'Milvus service not available: {str(e)}',
                'details': {'error': str(e)},
                'healthy': False
            }
        except Exception as e:
            return {
                'service': 'Milvus Vector Database',
                'status': 'error',
                'message': f'Milvus status check failed: {str(e)}',
                'details': {'error': str(e)},
                'healthy': False
            }
    
    @staticmethod
    def check_face_detection_service() -> Dict[str, Any]:
        """Check face detection service status"""
        try:
            from face_ai.services.face_detection import FaceDetectionService
            face_service = FaceDetectionService()
            
            # Try to initialize the service
            try:
                # Test with a minimal operation
                test_result = face_service.check_service_health()
                return {
                    'service': 'Face Detection Service',
                    'status': 'success',
                    'message': 'Face detection service is operational',
                    'details': test_result,
                    'healthy': True
                }
            except Exception as e:
                return {
                    'service': 'Face Detection Service',
                    'status': 'error',
                    'message': f'Face detection service health check failed: {str(e)}',
                    'details': {'error': str(e)},
                    'healthy': False
                }
                
        except ImportError as e:
            return {
                'service': 'Face Detection Service',
                'status': 'error',
                'message': f'Face detection service not available: {str(e)}',
                'details': {'error': str(e)},
                'healthy': False
            }
        except Exception as e:
            return {
                'service': 'Face Detection Service',
                'status': 'error',
                'message': f'Face detection service status check failed: {str(e)}',
                'details': {'error': str(e)},
                'healthy': False
            }
    
    @staticmethod
    def check_celery_status() -> Dict[str, Any]:
        """Check Celery background task service status"""
        try:
            from django.conf import settings
            import redis
            
            # Check Redis connection (Celery broker)
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            
            return {
                'service': 'Celery Background Tasks',
                'status': 'success',
                'message': 'Celery background task service is operational',
                'details': {'redis_url': redis_url, 'redis_status': 'connected'},
                'healthy': True
            }
        except Exception as e:
            return {
                'service': 'Celery Background Tasks',
                'status': 'error',
                'message': f'Celery background task service check failed: {str(e)}',
                'details': {'error': str(e)},
                'healthy': False
            }
    
    @staticmethod
    def check_all_services() -> Dict[str, Any]:
        """Check status of all face verification related services"""
        services = {
            'milvus': FaceVerificationStatus.check_milvus_status(),
            'face_detection': FaceVerificationStatus.check_face_detection_service(),
            'celery': FaceVerificationStatus.check_celery_status()
        }
        
        overall_healthy = all(service['healthy'] for service in services.values())
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'unhealthy',
            'services': services,
            'healthy_count': sum(1 for service in services.values() if service['healthy']),
            'total_count': len(services)
        }

@login_required
@require_http_methods(["GET"])
def face_verification_status_api(request):
    """API endpoint to check face verification service status"""
    try:
        status = FaceVerificationStatus.check_all_services()
        return JsonResponse({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Status check API failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def face_verification_health_check(request):
    """Health check endpoint for face verification services"""
    try:
        status = FaceVerificationStatus.check_all_services()
        
        # Return appropriate HTTP status based on health
        if status['overall_status'] == 'healthy':
            return JsonResponse({
                'status': 'healthy',
                'message': 'All face verification services are operational',
                'details': status
            }, status=200)
        else:
            return JsonResponse({
                'status': 'unhealthy',
                'message': 'Some face verification services are not operational',
                'details': status
            }, status=503)
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'error': str(e)
        }, status=500)
