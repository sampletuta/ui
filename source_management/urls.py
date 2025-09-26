from django.urls import path
from . import views_main as views
from .views import source_activation_views_new as activation_views
from .views import source_crud_views_new as crud_views
from .views import source_list_views_new as list_views

app_name = 'source_management'

urlpatterns = [
    # Dashboard
    path('', list_views.source_list, name='source_list'),
    path('dashboard/', list_views.dashboard, name='dashboard'),

    # Source creation
    path('add/', crud_views.source_create, name='source_create'),

    # Unified source routes (work for all source types)
    path('<uuid:source_id>/', crud_views.source_detail, name='source_detail'),
    path('<uuid:source_id>/edit/', crud_views.source_update, name='source_update'),
    path('<uuid:source_id>/delete/', crud_views.source_delete, name='source_delete'),

    # Legacy routes (keeping for backward compatibility)
    path('file/<uuid:source_id>/', crud_views.source_detail, name='file_detail'),
    path('file/<uuid:source_id>/edit/', crud_views.source_update, name='file_update'),
    path('file/<uuid:source_id>/delete/', crud_views.source_delete, name='file_delete'),

    path('camera/<uuid:source_id>/', crud_views.source_detail, name='camera_detail'),
    path('camera/<uuid:source_id>/edit/', crud_views.source_update, name='camera_update'),
    path('camera/<uuid:source_id>/delete/', crud_views.source_delete, name='camera_delete'),

    path('stream/<uuid:source_id>/', crud_views.source_detail, name='stream_detail'),
    path('stream/<uuid:source_id>/edit/', crud_views.source_update, name='stream_update'),
    path('stream/<uuid:source_id>/delete/', crud_views.source_delete, name='stream_delete'),

    # Video management
    path('video/upload/', crud_views.source_create, name='video_upload'),
    path('video/list/', list_views.source_list, name='video_list'),
    path('video/<int:video_id>/', crud_views.source_detail, name='video_detail'),
    path('video/<int:video_id>/delete/', crud_views.source_delete, name='video_delete'),
    path('video/<int:video_id>/send-to-face-detection/', crud_views.source_detail, name='send_to_face_detection'),

    # Job management
    path('job/<int:job_id>/', crud_views.source_detail, name='job_detail'),
    
    # API endpoints (authenticated)
    path('api/source/<uuid:source_id>/', views.api_source_metadata, name='api_source_metadata'),
    path('api/video/<str:access_token>/', views.api_video_access, name='api_video_access'),
    path('api/video/<str:access_token>/metadata/', views.api_video_metadata, name='api_video_metadata'),
    path('api/video/<str:access_token>/download/', views.api_video_download, name='api_video_download'),
    path('api/video/<str:access_token>/stream/', views.api_video_stream, name='api_video_stream'),

    # New API endpoints for source management
    path('api/source/<uuid:source_id>/activate/', activation_views.ActivateSourceView.as_view(), name='api_activate_source'),
    path('api/source/<uuid:source_id>/deactivate/', activation_views.DeactivateSourceView.as_view(), name='api_deactivate_source'),
    path('api/source/<uuid:source_id>/toggle/', activation_views.ToggleSourceActivationView.as_view(), name='api_toggle_source'),
    path('api/source/<str:source_type>/bulk-activation/', activation_views.BulkActivationView.as_view(), name='api_bulk_activate'),

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
    
    # Notification API endpoint for external apps
    path('api/notifications/create/', views.create_notification, name='create_notification'),
    
    # Stream Processor Service endpoints
    path('api/stream/<uuid:source_id>/create/', views.stream_create, name='stream_create'),
    path('api/stream/<uuid:source_id>/submit/', views.stream_submit, name='stream_submit'),
    path('api/stream/<uuid:source_id>/submit-comprehensive/', views.stream_submit_comprehensive, name='stream_submit_comprehensive'),
    path('api/stream/<uuid:source_id>/start/', views.stream_start, name='stream_start'),
    path('api/stream/<uuid:source_id>/stop/', views.stream_stop, name='stream_stop'),
    path('api/stream/<uuid:source_id>/status/', views.stream_status, name='stream_status'),
    
    # FastPublisher endpoints (aliases for template compatibility)
    path('api/fastpublisher/health/', views.fastpublisher_health, name='fastpublisher_health'),
    path('api/fastpublisher/submit-video/<uuid:source_id>/', views.fastpublisher_submit_video, name='fastpublisher_submit_video'),
    
    # Source Activation/Deactivation endpoints
    path('api/source/<uuid:source_id>/activate/', activation_views.ActivateSourceView.as_view(), name='activate_source'),
    path('api/source/<uuid:source_id>/deactivate/', activation_views.DeactivateSourceView.as_view(), name='deactivate_source'),
    path('api/source/<uuid:source_id>/toggle/', activation_views.ToggleSourceActivationView.as_view(), name='toggle_source'),
    path('api/source/<str:source_type>/bulk-activation/', activation_views.BulkActivationView.as_view(), name='bulk_activation'),

    # Source Activation/Deactivation confirmation pages
    path('source/<uuid:source_id>/<str:source_type>/<str:action>/confirm/', activation_views.source_activation_confirmation, name='source_activation_confirm'),
    path('source/activation/confirm/', activation_views.confirm_source_activation, name='confirm_source_activation'),
] 