import logging
import json
from typing import List, Dict
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import numpy as np

from .services.face_detection import FaceDetectionService
from .services.milvus_service import MilvusService

User = get_user_model()
logger = logging.getLogger(__name__)

class FaceProcessingView(View):
    """Base view for face processing operations"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.face_detection_service = FaceDetectionService()
        self.milvus_service = MilvusService()

@method_decorator(login_required, name='dispatch')
class FaceDetectionView(FaceProcessingView):
    """API 1: Detect faces in an image"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            image_path = data.get('image_path')
            
            if not image_path:
                return JsonResponse({
                    'success': False,
                    'error': 'image_path is required'
                }, status=400)
            
            # Detect faces in the image
            result = self.face_detection_service.detect_faces_in_image(image_path)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Face detection failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class FaceEmbeddingView(FaceProcessingView):
    """API 2: Generate face embeddings for multiple images (all must have faces)"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            image_paths = data.get('image_paths', [])
            
            if not image_paths:
                return JsonResponse({
                    'success': False,
                    'error': 'image_paths array is required'
                }, status=400)
            
            if not isinstance(image_paths, list):
                return JsonResponse({
                    'success': False,
                    'error': 'image_paths must be an array'
                }, status=400)
            
            # Generate face embeddings
            result = self.face_detection_service.generate_face_embeddings(image_paths)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Failed to generate embeddings')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in face embedding generation: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class FaceVerificationView(FaceProcessingView):
    """API 3: Face verification with age and gender estimation"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            image1_base64 = data.get('image1_base64')
            image2_base64 = data.get('image2_base64')
            confidence_threshold = data.get('confidence_threshold', 50.0)
            
            if not image1_base64 or not image2_base64:
                return JsonResponse({
                    'success': False,
                    'error': 'Both image1_base64 and image2_base64 are required'
                }, status=400)
            
            # Validate confidence threshold
            try:
                confidence_threshold = float(confidence_threshold)
                if not 0 <= confidence_threshold <= 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'confidence_threshold must be between 0 and 100'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'confidence_threshold must be a valid number'
                }, status=400)
            
            # Verify faces
            result = self.face_detection_service.verify_faces(
                image1_base64, 
                image2_base64, 
                confidence_threshold
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Face verification failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in face verification: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class MilvusStatusView(FaceProcessingView):
    """Get Milvus connection and collection status"""
    
    def get(self, request):
        try:
            # Get collection stats
            collection_stats = self.milvus_service.get_collection_stats()
            
            return JsonResponse({
                'success': True,
                'data': {
                    'milvus': collection_stats
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting Milvus status: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class DeleteFaceEmbeddingsView(FaceProcessingView):
    """Delete face embeddings from Milvus by vector IDs"""
    
    def delete(self, request):
        try:
            data = json.loads(request.body)
            vector_ids = data.get('vector_ids', [])
            
            if not vector_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'Vector IDs are required'
                }, status=400)
            
            # Delete from Milvus
            deleted_count = 0
            for vector_id in vector_ids:
                if self.milvus_service.delete_face_embedding(vector_id):
                    deleted_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f"Deleted {deleted_count} face embeddings from Milvus"
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error deleting face embeddings: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# Function-based views for backward compatibility
@login_required
@require_POST
def face_detection_api(request):
    """API endpoint for face detection"""
    view = FaceDetectionView()
    return view.post(request)

@login_required
@require_POST
def face_embedding_api(request):
    """API endpoint for face embedding generation"""
    view = FaceEmbeddingView()
    return view.post(request)

@login_required
@require_POST
def face_verification_api(request):
    """API endpoint for face verification"""
    view = FaceVerificationView()
    return view.post(request)

@login_required
@require_GET
def milvus_status_api(request):
    """API endpoint for getting Milvus status"""
    view = MilvusStatusView()
    return view.get(request)

@login_required
@require_http_methods(["DELETE"])
def delete_face_embeddings_api(request):
    """API endpoint for deleting face embeddings"""
    view = DeleteFaceEmbeddingsView()
    return view.delete(request)
