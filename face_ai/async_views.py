"""
Async views for face-ai application.

This module provides async-compatible views for parallel processing of face recognition operations.
"""

import logging
import json
import asyncio
from typing import List, Dict, Any
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
from django.views.decorators.cache import cache_page
from asgiref.sync import sync_to_async
import numpy as np

from .services.async_face_detection import AsyncFaceDetectionService
from .services.async_milvus_service import AsyncMilvusService

User = get_user_model()
logger = logging.getLogger(__name__)

class AsyncFaceProcessingView(View):
    """Base async view for face processing operations"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.face_detection_service = AsyncFaceDetectionService()
        self.milvus_service = AsyncMilvusService()

@method_decorator(login_required, name='dispatch')
class AsyncFaceDetectionView(AsyncFaceProcessingView):
    """Async API: Detect faces in an image with parallel processing"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image_path = data.get('image_path')
            enable_parallel = data.get('enable_parallel', True)
            
            if not image_path:
                return JsonResponse({
                    'success': False,
                    'error': 'image_path is required'
                }, status=400)
            
            # Detect faces in the image asynchronously
            if enable_parallel:
                result = await self.face_detection_service.detect_faces_in_image_async(image_path)
            else:
                result = await self.face_detection_service.detect_faces_in_image_sync(image_path)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'async_parallel' if enable_parallel else 'async_sequential'
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
            logger.error(f"Error in async face detection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class AsyncFaceEmbeddingView(AsyncFaceProcessingView):
    """Async API: Generate face embeddings for multiple images with parallel processing"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image_paths = data.get('image_paths', [])
            batch_size = data.get('batch_size', 10)
            enable_parallel = data.get('enable_parallel', True)
            
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
            
            # Generate face embeddings asynchronously
            if enable_parallel:
                result = await self.face_detection_service.generate_face_embeddings_parallel(
                    image_paths, batch_size
                )
            else:
                result = await self.face_detection_service.generate_face_embeddings_sequential(
                    image_paths
                )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'async_parallel' if enable_parallel else 'async_sequential'
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
            logger.error(f"Error in async face embedding generation: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class AsyncFaceVerificationView(AsyncFaceProcessingView):
    """Async API: Face verification with parallel processing"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image1_base64 = data.get('image1_base64')
            image2_base64 = data.get('image2_base64')
            confidence_threshold = data.get('confidence_threshold', 50.0)
            enable_parallel = data.get('enable_parallel', True)
            
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
            
            # Verify faces asynchronously
            if enable_parallel:
                result = await self.face_detection_service.verify_faces_parallel(
                    image1_base64, 
                    image2_base64, 
                    confidence_threshold
                )
            else:
                result = await self.face_detection_service.verify_faces_sequential(
                    image1_base64, 
                    image2_base64, 
                    confidence_threshold
                )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'async_parallel' if enable_parallel else 'async_sequential'
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
            logger.error(f"Error in async face verification: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class AsyncMilvusStatusView(AsyncFaceProcessingView):
    """Async API: Get Milvus connection and collection status"""
    
    async def get(self, request):
        try:
            # Get collection stats asynchronously
            collection_stats = await self.milvus_service.get_collection_stats_async()
            
            return JsonResponse({
                'success': True,
                'data': {
                    'milvus': collection_stats
                },
                'processing_mode': 'async'
            })
            
        except Exception as e:
            logger.error(f"Error getting async Milvus status: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class AsyncDeleteFaceEmbeddingsView(AsyncFaceProcessingView):
    """Async API: Delete face embeddings from Milvus by vector IDs"""
    
    async def delete(self, request):
        try:
            data = json.loads(request.body)
            vector_ids = data.get('vector_ids', [])
            enable_parallel = data.get('enable_parallel', True)
            
            if not vector_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'Vector IDs are required'
                }, status=400)
            
            # Delete from Milvus asynchronously
            if enable_parallel:
                deleted_count = await self.milvus_service.delete_face_embeddings_parallel(vector_ids)
            else:
                deleted_count = await self.milvus_service.delete_face_embeddings_sequential(vector_ids)
            
            return JsonResponse({
                'success': True,
                'message': f"Deleted {deleted_count} face embeddings from Milvus",
                'processing_mode': 'async_parallel' if enable_parallel else 'async_sequential'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error deleting face embeddings asynchronously: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class BatchFaceDetectionView(AsyncFaceProcessingView):
    """Batch API: Process multiple images for face detection in parallel"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image_paths = data.get('image_paths', [])
            max_workers = data.get('max_workers', 4)
            
            if not image_paths:
                return JsonResponse({
                    'success': False,
                    'error': 'image_paths array is required'
                }, status=400)
            
            # Process images in batches asynchronously
            result = await self.face_detection_service.batch_detect_faces(
                image_paths, max_workers
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'batch_parallel',
                    'max_workers': max_workers
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Batch face detection failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in batch face detection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class BatchFaceEmbeddingView(AsyncFaceProcessingView):
    """Batch API: Generate embeddings for multiple images in parallel"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image_paths = data.get('image_paths', [])
            max_workers = data.get('max_workers', 4)
            batch_size = data.get('batch_size', 10)
            
            if not image_paths:
                return JsonResponse({
                    'success': False,
                    'error': 'image_paths array is required'
                }, status=400)
            
            # Process embeddings in batches asynchronously
            result = await self.face_detection_service.batch_generate_embeddings(
                image_paths, max_workers, batch_size
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'batch_parallel',
                    'max_workers': max_workers,
                    'batch_size': batch_size
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Batch embedding generation failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in batch embedding generation: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class BatchFaceVerificationView(AsyncFaceProcessingView):
    """Batch API: Verify multiple face pairs in parallel"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            face_pairs = data.get('face_pairs', [])
            max_workers = data.get('max_workers', 4)
            confidence_threshold = data.get('confidence_threshold', 50.0)
            
            if not face_pairs:
                return JsonResponse({
                    'success': False,
                    'error': 'face_pairs array is required'
                }, status=400)
            
            # Process verification in batches asynchronously
            result = await self.face_detection_service.batch_verify_faces(
                face_pairs, max_workers, confidence_threshold
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'batch_parallel',
                    'max_workers': max_workers
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Batch face verification failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in batch face verification: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class RealtimeFaceDetectionView(AsyncFaceProcessingView):
    """Real-time API: Stream face detection results"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image_path = data.get('image_path')
            stream_mode = data.get('stream_mode', 'single')
            
            if not image_path:
                return JsonResponse({
                    'success': False,
                    'error': 'image_path is required'
                }, status=400)
            
            # Real-time face detection
            result = await self.face_detection_service.realtime_detect_faces(
                image_path, stream_mode
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'realtime_stream',
                    'stream_mode': stream_mode
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Real-time face detection failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in real-time face detection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(login_required, name='dispatch')
class RealtimeFaceVerificationView(AsyncFaceProcessingView):
    """Real-time API: Stream face verification results"""
    
    async def post(self, request):
        try:
            data = json.loads(request.body)
            image1_base64 = data.get('image1_base64')
            image2_base64 = data.get('image2_base64')
            confidence_threshold = data.get('confidence_threshold', 50.0)
            stream_mode = data.get('stream_mode', 'single')
            
            if not image1_base64 or not image2_base64:
                return JsonResponse({
                    'success': False,
                    'error': 'Both image1_base64 and image2_base64 are required'
                }, status=400)
            
            # Real-time face verification
            result = await self.face_detection_service.realtime_verify_faces(
                image1_base64, 
                image2_base64, 
                confidence_threshold,
                stream_mode
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result,
                    'processing_mode': 'realtime_stream',
                    'stream_mode': stream_mode
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Real-time face verification failed')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in real-time face verification: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
