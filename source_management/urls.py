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
    
    # API endpoints
    path('api/source/<uuid:source_id>/', views.api_source_metadata, name='api_source_metadata'),
    path('api/video/<str:access_token>/', views.api_video_access, name='api_video_access'),
    path('api/video/<str:access_token>/metadata/', views.api_video_metadata, name='api_video_metadata'),
    path('api/video/<str:access_token>/download/', views.api_video_download, name='api_video_download'),
    path('api/video/<str:access_token>/stream/', views.api_video_stream, name='api_video_stream'),
    
    # FastPublisher integration endpoints
    path('api/processing-callback/<str:access_token>/', views.processing_callback, name='processing_callback'),
    path('api/processing-jobs/<uuid:source_id>/', views.list_processing_jobs, name='list_processing_jobs'),
    path('api/fastpublisher-status/<uuid:source_id>/', views.fastpublisher_status_check, name='fastpublisher_status_check'),
    path('api/fastpublisher-video/<uuid:source_id>/', views.fastpublisher_video_access, name='fastpublisher_video_access'),
    path('api/fastpublisher-submit/<uuid:source_id>/', views.fastpublisher_submit_video, name='fastpublisher_submit_video'),
    path('api/fastpublisher-metadata/<uuid:source_id>/', views.fastpublisher_video_metadata, name='fastpublisher_video_metadata'),
    path('api/fastpublisher-health/', views.fastpublisher_health, name='fastpublisher_health'),
    
    # Video Processing endpoints
    path('api/process-video/<uuid:source_id>/', views.submit_video_processing, name='submit_video_processing'),
    path('api/processing-status/<str:job_id>/', views.get_processing_status, name='get_processing_status'),
    path('api/cancel-processing/<str:job_id>/', views.cancel_processing_job, name='cancel_processing_job'),
    path('api/processing-callback/<str:access_token>/', views.processing_callback, name='processing_callback'),
    path('api/processing-jobs/<uuid:source_id>/', views.list_processing_jobs, name='list_processing_jobs'),
] 