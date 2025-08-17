from django.urls import path
from . import views, async_views

app_name = 'face_ai'

urlpatterns = [
    # Core Face AI APIs (Synchronous)
    path('api/face/detect/', 
         views.face_detection_api, name='face_detection'),
    
    path('api/face/embedding/', 
         views.face_embedding_api, name='face_embedding'),
    
    path('api/face/verify/', 
         views.face_verification_api, name='face_verification'),
    
    # Utility APIs (Synchronous)
    path('api/face/milvus/status/', 
         views.milvus_status_api, name='milvus_status'),
    
    path('api/face/delete/', 
         views.delete_face_embeddings_api, name='delete_face_embeddings'),
    
    # Class-based view endpoints (Synchronous)
    path('api/face/detect/v2/', 
         views.FaceDetectionView.as_view(), name='face_detection_v2'),
    
    path('api/face/embedding/v2/', 
         views.FaceEmbeddingView.as_view(), name='face_embedding_v2'),
    
    path('api/face/verify/v2/', 
         views.FaceVerificationView.as_view(), name='face_verification_v2'),
    
    path('api/face/milvus/status/v2/', 
         views.MilvusStatusView.as_view(), name='milvus_status_v2'),
    
    path('api/face/delete/v2/', 
         views.DeleteFaceEmbeddingsView.as_view(), name='delete_face_embeddings_v2'),
    
    # Async Face AI APIs (Parallel Processing)
    path('api/face/detect/async/', 
         async_views.AsyncFaceDetectionView.as_view(), name='async_face_detection'),
    
    path('api/face/embedding/async/', 
         async_views.AsyncFaceEmbeddingView.as_view(), name='async_face_embedding'),
    
    path('api/face/verify/async/', 
         async_views.AsyncFaceVerificationView.as_view(), name='async_face_verification'),
    
    # Async Utility APIs
    path('api/face/milvus/status/async/', 
         async_views.AsyncMilvusStatusView.as_view(), name='async_milvus_status'),
    
    path('api/face/delete/async/', 
         async_views.AsyncDeleteFaceEmbeddingsView.as_view(), name='async_delete_face_embeddings'),
    
    # Batch Processing APIs
    path('api/face/batch/detect/', 
         async_views.BatchFaceDetectionView.as_view(), name='batch_face_detection'),
    
    path('api/face/batch/embedding/', 
         async_views.BatchFaceEmbeddingView.as_view(), name='batch_face_embedding'),
    
    path('api/face/batch/verify/', 
         async_views.BatchFaceVerificationView.as_view(), name='batch_face_verification'),
    
    # Real-time Processing APIs
    path('api/face/realtime/detect/', 
         async_views.RealtimeFaceDetectionView.as_view(), name='realtime_face_detection'),
    
    path('api/face/realtime/verify/', 
         async_views.RealtimeFaceVerificationView.as_view(), name='realtime_face_verification'),
]
