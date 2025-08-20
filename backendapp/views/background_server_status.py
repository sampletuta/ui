"""
Background Server Status Views
Provides status checking for background services used by face verification
"""

import logging
import json
from typing import Dict, Any
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings

logger = logging.getLogger(__name__)

class BackgroundServerStatusChecker:
    """Checks status of background servers and services"""
    
    @staticmethod
    def check_redis_status() -> Dict[str, Any]:
        """Check Redis connection status"""
        try:
            import redis
            
            # Get Redis URL from settings
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            redis_client = redis.from_url(redis_url)
            
            # Test connection
            redis_client.ping()
            
            # Get Redis info
            info = redis_client.info()
            
            return {
                'service': 'Redis Cache & Message Broker',
                'status': 'success',
                'message': 'Redis is operational',
                'healthy': True,
                'details': {
                    'url': redis_url,
                    'version': info.get('redis_version', 'Unknown'),
                    'used_memory': info.get('used_memory_human', 'Unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'uptime': info.get('uptime_in_seconds', 0)
                }
            }
        except ImportError as e:
            return {
                'service': 'Redis Cache & Message Broker',
                'status': 'error',
                'message': f'Redis client not available: {str(e)}',
                'healthy': False,
                'details': {'error': str(e)}
            }
        except Exception as e:
            return {
                'service': 'Redis Cache & Message Broker',
                'status': 'error',
                'message': f'Redis connection failed: {str(e)}',
                'healthy': False,
                'details': {'error': str(e)}
            }
    
    @staticmethod
    def check_celery_status() -> Dict[str, Any]:
        """Check Celery worker status"""
        try:
            from celery import current_app
            
            # Get Celery app
            app = current_app
            
            # Check if Celery is configured
            if not app.conf.broker_url:
                return {
                    'service': 'Celery Background Tasks',
                    'status': 'warning',
                    'message': 'Celery not configured with broker',
                    'healthy': False,
                    'details': {'error': 'No broker URL configured'}
                }
            
            # Try to inspect workers
            try:
                inspector = app.control.inspect()
                active_workers = inspector.active()
                registered_workers = inspector.registered()
                
                if active_workers:
                    worker_count = len(active_workers)
                    return {
                        'service': 'Celery Background Tasks',
                        'status': 'success',
                        'message': f'Celery is operational with {worker_count} active workers',
                        'healthy': True,
                        'details': {
                            'active_workers': worker_count,
                            'broker_url': app.conf.broker_url,
                            'worker_details': active_workers
                        }
                    }
                else:
                    return {
                        'service': 'Celery Background Tasks',
                        'status': 'warning',
                        'message': 'Celery is configured but no active workers found',
                        'healthy': False,
                        'details': {
                            'broker_url': app.conf.broker_url,
                            'active_workers': 0
                        }
                    }
                    
            except Exception as e:
                return {
                    'service': 'Celery Background Tasks',
                    'status': 'warning',
                    'message': f'Celery is configured but worker inspection failed: {str(e)}',
                    'healthy': False,
                    'details': {
                        'broker_url': app.conf.broker_url,
                        'error': str(e)
                    }
                }
                
        except ImportError as e:
            return {
                'service': 'Celery Background Tasks',
                'status': 'error',
                'message': f'Celery not available: {str(e)}',
                'healthy': False,
                'details': {'error': str(e)}
            }
        except Exception as e:
            return {
                'service': 'Celery Background Tasks',
                'status': 'error',
                'message': f'Celery status check failed: {str(e)}',
                'healthy': False,
                'details': {'error': str(e)}
            }
    
    @staticmethod
    def check_database_status() -> Dict[str, Any]:
        """Check database connection status"""
        try:
            from django.db import connection
            
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            if result and result[0] == 1:
                # Get database info
                db_info = {
                    'engine': settings.DATABASES['default']['ENGINE'],
                    'name': settings.DATABASES['default'].get('NAME', 'Unknown'),
                    'host': settings.DATABASES['default'].get('HOST', 'localhost'),
                    'port': settings.DATABASES['default'].get('PORT', 'default')
                }
                
                return {
                    'service': 'Database',
                    'status': 'success',
                    'message': 'Database connection is operational',
                    'healthy': True,
                    'details': db_info
                }
            else:
                return {
                    'service': 'Database',
                    'status': 'error',
                    'message': 'Database connection test failed',
                    'healthy': False,
                    'details': {'error': 'Connection test returned unexpected result'}
                }
                
        except Exception as e:
            return {
                'service': 'Database',
                'status': 'error',
                'message': f'Database connection failed: {str(e)}',
                'healthy': False,
                'details': {'error': str(e)}
            }
    
    @staticmethod
    def check_all_background_services() -> Dict[str, Any]:
        """Check status of all background services"""
        services = {
            'redis': BackgroundServerStatusChecker.check_redis_status(),
            'celery': BackgroundServerStatusChecker.check_celery_status(),
            'database': BackgroundServerStatusChecker.check_database_status()
        }
        
        overall_healthy = all(service['healthy'] for service in services.values())
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'unhealthy',
            'services': services,
            'healthy_count': sum(1 for service in services.values() if service['healthy']),
            'total_count': len(services),
            'timestamp': '2024-01-01T00:00:00Z'  # You can add proper timestamp here
        }

@login_required
@require_http_methods(["GET"])
def background_server_status_api(request):
    """API endpoint to check background server status"""
    try:
        status = BackgroundServerStatusChecker.check_all_background_services()
        return JsonResponse({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Background server status check failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def background_server_health_check(request):
    """Health check endpoint for background servers"""
    try:
        status = BackgroundServerStatusChecker.check_all_background_services()
        
        # Return appropriate HTTP status based on health
        if status['overall_status'] == 'healthy':
            return JsonResponse({
                'status': 'healthy',
                'message': 'All background services are operational',
                'details': status
            }, status=200)
        else:
            return JsonResponse({
                'status': 'unhealthy',
                'message': 'Some background services are not operational',
                'details': status
            }, status=503)
            
    except Exception as e:
        logger.error(f"Background server health check failed: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def celery_worker_status(request):
    """Get detailed Celery worker status"""
    try:
        from celery import current_app
        
        app = current_app
        inspector = app.control.inspect()
        
        # Get various worker information
        active_tasks = inspector.active()
        registered_tasks = inspector.registered()
        worker_stats = inspector.stats()
        
        worker_info = {
            'active_tasks': active_tasks or {},
            'registered_tasks': registered_tasks or {},
            'worker_stats': worker_stats or {},
            'broker_url': app.conf.broker_url,
            'result_backend': app.conf.result_backend
        }
        
        return JsonResponse({
            'success': True,
            'data': worker_info
        })
        
    except Exception as e:
        logger.error(f"Celery worker status check failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
