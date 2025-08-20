"""
Face Verification Views Module
Handles face verification, comparison, and watchlist verification with enhanced status checking
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
import json
import requests
from typing import Dict, List, Any

from ..models import Targets_watchlist, TargetPhoto

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
def face_verification(request):
    """Face verification service to compare two images and show similarity"""
    if request.method == 'POST':
        try:
            # Check service status before processing
            status_check = FaceVerificationStatus.check_all_services()
            if not status_check['overall_status'] == 'healthy':
                messages.warning(request, f'Some services are not fully operational. Face verification may have limited functionality.')
                logger.warning(f"Face verification attempted with unhealthy services: {status_check}")
            
            # Check if we have base64 data from preview or file uploads
            image1_base64 = request.POST.get('image1_base64')
            image2_base64 = request.POST.get('image2_base64')
            threshold = float(request.POST.get('threshold', 50)) / 100  # Convert percentage to decimal
            
            # If no base64 data, process file uploads
            if not image1_base64 or not image2_base64:
                image1 = request.FILES.get('image1')
                image2 = request.FILES.get('image2')
                
                if not image1 or not image2:
                    messages.error(request, 'Please upload both images for comparison.')
                    return render(request, 'face_verification.html')
                
                # Convert images to base64 for processing and display
                import base64
                
                def image_to_base64(image_file):
                    image_file.seek(0)
                    image_data = image_file.read()
                    return base64.b64encode(image_data).decode('utf-8')
                
                # Process images
                image1_base64 = image_to_base64(image1)
                image2_base64 = image_to_base64(image2)
                image1_name = image1.name
                image2_name = image2.name
            else:
                # Use names from preview or generate generic names
                image1_name = request.POST.get('image1_name', 'Reference Image')
                image2_name = request.POST.get('image2_name', 'Query Image')
            
            # Import face AI service
            try:
                from face_ai.services.face_detection import FaceDetectionService
                face_service = FaceDetectionService()
            except ImportError as e:
                messages.error(request, f'Face detection service not available: {str(e)}')
                logger.error(f"Face detection service import failed: {e}")
                return render(request, 'face_verification.html')
            except Exception as e:
                messages.error(request, f'Failed to initialize face detection service: {str(e)}')
                logger.error(f"Face detection service initialization failed: {e}")
                return render(request, 'face_verification.html')
            
            # Detect faces in both images
            try:
                result1 = face_service.detect_faces_in_image_base64(image1_base64)
                result2 = face_service.detect_faces_in_image_base64(image2_base64)
                
                if not result1['success'] or not result2['success']:
                    error_msg = f"Face detection failed: Image 1: {result1.get('error', 'Unknown error')}, Image 2: {result2.get('error', 'Unknown error')}"
                    messages.error(request, error_msg)
                    logger.error(f"Face detection failed: {error_msg}")
                    return render(request, 'face_verification.html')
                
                if result1['faces_detected'] == 0:
                    messages.error(request, 'No faces detected in the first image.')
                    return render(request, 'face_verification.html')
                
                if result2['faces_detected'] == 0:
                    messages.error(request, 'No faces detected in the second image.')
                    return render(request, 'face_verification.html')
                
                # Get the first face from each image for comparison
                face1 = result1['faces'][0] if result1['faces'] else None
                face2 = result2['faces'][0] if result2['faces'] else None
                
                if not face1 or not face2:
                    messages.error(request, 'Failed to extract face data from images.')
                    return render(request, 'face_verification.html')
                
            except Exception as e:
                error_msg = f'Face detection processing failed: {str(e)}'
                messages.error(request, error_msg)
                logger.error(f"Face detection processing failed: {e}")
                return render(request, 'face_verification.html')
            
            # Verify faces
            try:
                verification_result = face_service.verify_faces(image1_base64, image2_base64, threshold)
                
                if not verification_result['success']:
                    error_msg = f'Face verification failed: {verification_result.get("error", "Unknown error")}'
                    messages.error(request, error_msg)
                    logger.error(f"Face verification failed: {error_msg}")
                    return render(request, 'face_verification.html')
                
                # Prepare context for results
                context = {
                    'image1_base64': image1_base64,
                    'image2_base64': image2_base64,
                    'image1_name': image1_name,
                    'image2_name': image2_name,
                    'verification_result': verification_result,
                    'face1_info': face1,
                    'face2_info': face2,
                    'threshold': threshold * 100,
                    'services_status': status_check
                }
                
                return render(request, 'face_verification.html', context)
                
            except Exception as e:
                error_msg = f'Face verification processing failed: {str(e)}'
                messages.error(request, error_msg)
                logger.error(f"Face verification processing failed: {e}")
                return render(request, 'face_verification.html')
                
        except ValueError as e:
            messages.error(request, f'Invalid input data: {str(e)}')
            logger.error(f"Invalid input data in face verification: {e}")
            return render(request, 'face_verification.html')
        except Exception as e:
            error_msg = f'Unexpected error during face verification: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Unexpected error in face verification: {e}")
            return render(request, 'face_verification.html')
    
    # GET request - show the form
    return render(request, 'face_verification.html')

@login_required
def face_verification_preview(request):
    """Preview images before face verification"""
    if request.method == 'POST':
        try:
            image1 = request.FILES.get('image1')
            image2 = request.FILES.get('image2')
            
            if not image1 or not image2:
                messages.error(request, 'Please upload both images.')
                return redirect('face_verification')
            
            # Convert images to base64 for preview
            import base64
            
            def image_to_base64(image_file):
                image_file.seek(0)
                image_data = image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
            
            # Process images
            image1_base64 = image_to_base64(image1)
            image2_base64 = image_to_base64(image2)
            
            # Check service status
            status_check = FaceVerificationStatus.check_all_services()
            
            context = {
                'image1_base64': image1_base64,
                'image2_base64': image2_base64,
                'image1_name': image1.name,
                'image2_name': image2.name,
                'services_status': status_check
            }
            
            return render(request, 'face_verification_preview.html', context)
            
        except Exception as e:
            error_msg = f'Error processing images for preview: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Image preview processing failed: {e}")
            return redirect('face_verification')
    
    return redirect('face_verification')

@login_required
def face_verification_watchlist(request):
    """Advanced watchlist verification with multiple modes and enhanced status checking"""
    # Get all watchlist targets for selection
    watchlist_targets = Targets_watchlist.objects.select_related('case').all()
    
    # Check service status
    services_status = FaceVerificationStatus.check_all_services()
    
    if request.method == 'POST':
        try:
            verification_mode = request.POST.get('verification_mode')
            threshold = float(request.POST.get('threshold', 60)) / 100
            max_results = int(request.POST.get('max_results', 5))
            
            # Validate service health before processing
            if not services_status['overall_status'] == 'healthy':
                messages.warning(request, f'Some services are not fully operational. Watchlist verification may have limited functionality.')
                logger.warning(f"Watchlist verification attempted with unhealthy services: {services_status}")
            
            if verification_mode == 'mode1':
                # Mode 1: Watchlist vs Image
                return handle_mode1_verification(request, watchlist_targets, threshold, max_results, services_status)
            elif verification_mode == 'mode2':
                # Mode 2: Watchlist vs Watchlist
                return handle_mode2_verification(request, watchlist_targets, threshold, max_results, services_status)
            else:
                messages.error(request, 'Invalid verification mode selected.')
                return render(request, 'face_verification_watchlist.html', {
                    'watchlist_targets': watchlist_targets,
                    'services_status': services_status
                })
                
        except ValueError as e:
            error_msg = f'Invalid input data: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Invalid input data in watchlist verification: {e}")
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        except Exception as e:
            error_msg = f'Error during watchlist verification: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Watchlist verification error: {e}")
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
    
    return render(request, 'face_verification_watchlist.html', {
        'watchlist_targets': watchlist_targets,
        'services_status': services_status
    })

def handle_mode1_verification(request, watchlist_targets, threshold, max_results, services_status):
    """Handle Mode 1: Verify selected watchlist targets against one image"""
    try:
        query_image = request.FILES.get('query_image')
        target_ids = request.POST.getlist('target_ids')
        
        if not query_image:
            messages.error(request, 'Please upload an image for verification.')
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        if not target_ids:
            messages.error(request, 'Please select at least one watchlist target.')
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Import services with error handling
        try:
            from face_ai.services.face_detection import FaceDetectionService
            from face_ai.services.milvus_service import MilvusService
            
            face_service = FaceDetectionService()
            milvus_service = MilvusService()
        except ImportError as e:
            error_msg = f'Required services not available: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Service import failed: {e}")
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Convert image to base64 for processing
        import base64
        
        def image_to_base64(image_file):
            image_file.seek(0)
            image_data = image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
        
        # Process query image
        query_base64 = image_to_base64(query_image)
        
        # Validate face detection in query image
        try:
            query_validation = face_service.detect_faces_in_image_base64(query_base64)
            if not query_validation['success']:
                messages.error(request, f'Face detection failed: {query_validation["error"]}')
                return render(request, 'face_verification_watchlist.html', {
                    'watchlist_targets': watchlist_targets,
                    'services_status': services_status
                })
            
            if query_validation['faces_detected'] == 0:
                messages.error(request, 'No faces detected in the uploaded image.')
                return render(request, 'face_verification_watchlist.html', {
                    'watchlist_targets': watchlist_targets,
                    'services_status': services_status
                })
            
            query_face = query_validation['faces'][0] if query_validation['faces'] else None
            if not query_face:
                messages.error(request, 'Failed to extract face data from uploaded image.')
                return render(request, 'face_verification_watchlist.html', {
                    'watchlist_targets': watchlist_targets,
                    'services_status': services_status
                })
                
        except Exception as e:
            error_msg = f'Face detection processing failed: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Face detection processing failed: {e}")
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Process verification against targets
        verification_results = []
        total_targets = len(target_ids)
        
        for target_id in target_ids:
            try:
                target = Targets_watchlist.objects.get(id=target_id)
                
                # Get target photos
                target_photos = TargetPhoto.objects.filter(person=target)
                
                for photo in target_photos:
                    try:
                        # Convert photo to base64 for comparison
                        photo_base64 = face_service.image_to_base64(photo.image)
                        
                        # Compare faces
                        result = face_service.verify_faces(query_base64, photo_base64, threshold)
                        
                        if result['success'] and result['faces_match']:
                            verification_results.append({
                                'target': target,
                                'photo': photo,
                                'similarity': result['similarity_score'] * 100,
                                'confidence': query_face['confidence']
                            })
                    except Exception as e:
                        logger.error(f"Error processing photo {photo.id}: {e}")
                        continue
                        
            except Targets_watchlist.DoesNotExist:
                continue
        
        # Sort by similarity (highest first)
        verification_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Limit results per target
        if max_results > 0:
            verification_results = verification_results[:max_results * total_targets]
        
        # Prepare context
        context = {
            'watchlist_targets': watchlist_targets,
            'verification_results': verification_results,
            'query_image_base64': query_base64,
            'query_image_name': query_image.name,
            'threshold': threshold * 100,
            'max_results': max_results,
            'verification_mode': 'mode1',
            'services_status': services_status
        }
        
        return render(request, 'face_verification_watchlist.html', context)
        
    except Exception as e:
        error_msg = f'Mode 1 verification processing failed: {str(e)}'
        messages.error(request, error_msg)
        logger.error(f"Mode 1 verification failed: {e}")
        return render(request, 'face_verification_watchlist.html', {
            'watchlist_targets': watchlist_targets,
            'services_status': services_status
        })

def handle_mode2_verification(request, watchlist_targets, threshold, max_results, services_status):
    """Handle Mode 2: Compare watchlist targets against each other using Milvus embeddings"""
    try:
        source_target_id = request.POST.get('source_target_id')
        target_ids = request.POST.getlist('target_ids')
        
        if not source_target_id:
            messages.error(request, 'Please select a source target.')
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        if not target_ids:
            messages.error(request, 'Please select at least one target to compare.')
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Import services with error handling
        try:
            from face_ai.services.milvus_service import MilvusService
            
            milvus_service = MilvusService()
        except ImportError as e:
            error_msg = f'Milvus service not available: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"Milvus service import failed: {e}")
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Check Milvus collection status first
        try:
            collection_status = milvus_service.check_collection_status()
            if collection_status['status'] == 'error':
                error_msg = f'Milvus collection error: {collection_status["message"]}'
                logger.error(f"Milvus collection error: {collection_status['message']}")
                messages.error(request, error_msg)
                return render(request, 'face_verification_watchlist.html', {
                    'watchlist_targets': watchlist_targets,
                    'services_status': services_status
                })
            elif collection_status['status'] == 'warning':
                warning_msg = f'Milvus collection has issues, attempting to continue with limited functionality: {collection_status["message"]}'
                logger.warning(f"Milvus collection has issues: {collection_status['message']}")
                messages.warning(request, warning_msg)
                # Continue with limited functionality instead of failing completely
            else:
                logger.info(f"Milvus collection status: {collection_status}")
        except Exception as e:
            error_msg = f'Failed to check Milvus collection status: {str(e)}'
            logger.error(f"Milvus status check failed: {e}")
            messages.error(request, error_msg)
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Get source target
        try:
            source_target = Targets_watchlist.objects.get(id=source_target_id)
        except Targets_watchlist.DoesNotExist:
            messages.error(request, 'Selected source target not found.')
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
        
        # Process verification using Milvus
        verification_results = []
        
        try:
            for target_id in target_ids:
                if target_id == source_target_id:
                    continue  # Skip comparing target with itself
                
                try:
                    target = Targets_watchlist.objects.get(id=target_id)
                    
                    # Use Milvus service to compare embeddings
                    comparison_result = milvus_service.compare_target_embeddings(
                        source_target_id, target_id, threshold
                    )
                    
                    if comparison_result['success'] and comparison_result['similarity'] > threshold:
                        verification_results.append({
                            'source_target': source_target,
                            'target': target,
                            'similarity': comparison_result['similarity'] * 100,
                            'method': 'Milvus Embeddings'
                        })
                        
                except Targets_watchlist.DoesNotExist:
                    continue
                except Exception as e:
                    logger.error(f"Error comparing target {target_id}: {e}")
                    continue
            
            # Sort by similarity (highest first)
            verification_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Limit results
            if max_results > 0:
                verification_results = verification_results[:max_results]
            
            # Prepare context
            context = {
                'watchlist_targets': watchlist_targets,
                'verification_results': verification_results,
                'source_target': source_target,
                'threshold': threshold * 100,
                'max_results': max_results,
                'verification_mode': 'mode2',
                'services_status': services_status
            }
            
            return render(request, 'face_verification_watchlist.html', context)
            
        except Exception as e:
            error_msg = f'Milvus comparison processing failed: {str(e)}'
            logger.error(f"Milvus comparison failed: {e}")
            messages.error(request, error_msg)
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'services_status': services_status
            })
            
    except Exception as e:
        error_msg = f'Mode 2 verification processing failed: {str(e)}'
        messages.error(request, error_msg)
        logger.error(f"Mode 2 verification failed: {e}")
        return render(request, 'face_verification_watchlist.html', {
            'watchlist_targets': watchlist_targets,
            'services_status': services_status
        })

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
