"""
ASGI config for backend project.

This module enables async/await support and parallel processing for the Django application.
"""

import os
import django
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Initialize Django
django.setup()

# Get Django ASGI application
django_asgi_app = get_asgi_application()

# Import face-ai async views for routing
try:
    from face_ai import async_views
    from face_ai.asgi_config import get_config
    
    # Get configuration
    config = get_config()
    
    # Define async URL patterns for face-ai
    async_urlpatterns = [
        # Core Face AI APIs - Async versions
        path('api/face/detect/async/', 
             async_views.AsyncFaceDetectionView.as_view(), name='async_face_detection'),
        
        path('api/face/embedding/async/', 
             async_views.AsyncFaceEmbeddingView.as_view(), name='async_face_embedding'),
        
        path('api/face/verify/async/', 
             async_views.AsyncFaceVerificationView.as_view(), name='async_face_verification'),
        
        # Utility APIs - Async versions
        path('api/face/milvus/status/async/', 
             async_views.AsyncMilvusStatusView.as_view(), name='async_milvus_status'),
        
        path('api/face/delete/async/', 
             async_views.AsyncDeleteFaceEmbeddingsView.as_view(), name='async_delete_face_embeddings'),
        
        # Batch processing APIs
        path('api/face/batch/detect/', 
             async_views.BatchFaceDetectionView.as_view(), name='batch_face_detection'),
        
        path('api/face/batch/embedding/', 
             async_views.BatchFaceEmbeddingView.as_view(), name='batch_face_embedding'),
        
        path('api/face/batch/verify/', 
             async_views.BatchFaceVerificationView.as_view(), name='batch_face_verification'),
        
        # Real-time processing APIs
        path('api/face/realtime/detect/', 
             async_views.RealtimeFaceDetectionView.as_view(), name='realtime_face_detection'),
        
        path('api/face/realtime/verify/', 
             async_views.RealtimeFaceVerificationView.as_view(), name='realtime_face_verification'),
    ]
    
    # Create the ASGI application with async routing
    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(async_urlpatterns)
        ),
    })
    
    print(f"✅ ASGI application initialized with {len(async_urlpatterns)} async endpoints")
    print(f"✅ Parallel processing enabled with {config['PARALLEL']['MAX_WORKERS']} workers")
    
except ImportError as e:
    print(f"⚠️ Face AI async views not available: {e}")
    print("⚠️ Using standard Django ASGI application")
    
    # Fallback to standard Django ASGI
    application = django_asgi_app
    
except Exception as e:
    print(f"❌ Error initializing ASGI application: {e}")
    print("❌ Using standard Django ASGI application")
    
    # Fallback to standard Django ASGI
    application = django_asgi_app
