from django.urls import path
from . import views

app_name = 'source_management'

urlpatterns = [
    # Dashboard
    path('', views.source_list, name='source_list'),
    path('dashboard/', views.source_list, name='dashboard'),
    
    # Source creation
    path('add/', views.source_create, name='source_create'),
    
    # File sources
    path('file/<uuid:source_id>/', views.source_detail, name='file_detail'),
    path('file/<uuid:source_id>/edit/', views.source_update, name='file_update'),
    path('file/<uuid:source_id>/delete/', views.source_delete, name='file_delete'),
    
    # Camera sources
    path('camera/<uuid:source_id>/', views.source_detail, name='camera_detail'),
    path('camera/<uuid:source_id>/edit/', views.source_update, name='camera_update'),
    path('camera/<uuid:source_id>/delete/', views.source_delete, name='camera_delete'),
    
    # Stream sources
    path('stream/<uuid:source_id>/', views.source_detail, name='stream_detail'),
    path('stream/<uuid:source_id>/edit/', views.source_update, name='stream_update'),
    path('stream/<uuid:source_id>/delete/', views.source_delete, name='stream_delete'),
    
    # Video management
    path('video/upload/', views.source_create, name='video_upload'),
    path('video/list/', views.source_list, name='video_list'),
    path('video/<int:video_id>/', views.source_detail, name='video_detail'),
    path('video/<int:video_id>/delete/', views.source_delete, name='video_delete'),
    path('video/<int:video_id>/send-to-face-detection/', views.source_detail, name='send_to_face_detection'),
    
    # Job management
    path('job/<int:job_id>/', views.source_detail, name='job_detail'),
    
    # API endpoints (authenticated)
    path('api/source/<uuid:source_id>/', views.api_source_metadata, name='api_source_metadata'),
    path('api/video/<str:access_token>/', views.api_video_access, name='api_video_access'),
    path('api/video/<str:access_token>/metadata/', views.api_video_metadata, name='api_video_metadata'),
    path('api/video/<str:access_token>/download/', views.api_video_download, name='api_video_download'),
    path('api/video/<str:access_token>/stream/', views.api_video_stream, name='api_video_stream'),
    
    # Public API endpoints (no authentication required - for data ingestion service)
    path('api/public/video/<str:access_token>/', views.api_video_access_public, name='api_video_access_public'),
    path('api/public/video/<str:access_token>/metadata/', views.api_video_metadata_public, name='api_video_metadata_public'),
    path('api/public/video/<str:access_token>/download/', views.api_video_download_public, name='api_video_download_public'),
    path('api/public/video/<str:access_token>/stream/', views.api_video_stream_public, name='api_video_stream_public'),
    
    # Video Processing endpoints (authenticated)
    path('api/process-video/<uuid:source_id>/', views.submit_video_processing, name='submit_video_processing'),
    path('api/processing-status/<str:job_id>/', views.get_processing_status, name='get_processing_status'),
    path('api/cancel-processing/<str:job_id>/', views.cancel_processing_job, name='cancel_processing_job'),
    path('api/processing-jobs/<uuid:source_id>/', views.list_processing_jobs, name='list_processing_jobs'),
    
    # Processing callback endpoint
    path('api/processing-callback/<str:access_token>/', views.processing_callback, name='processing_callback'),
    
    # Data Ingestion Service endpoints
    path('api/data-ingestion/health/', views.data_ingestion_health, name='data_ingestion_health'),
    path('api/data-ingestion/status/<uuid:source_id>/', views.data_ingestion_source_status, name='data_ingestion_source_status'),
    
    # FastPublisher endpoints (aliases for template compatibility)
    path('api/fastpublisher/health/', views.fastpublisher_health, name='fastpublisher_health'),
    path('api/fastpublisher/submit-video/<uuid:source_id>/', views.fastpublisher_submit_video, name='fastpublisher_submit_video'),
] 