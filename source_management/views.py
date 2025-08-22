"""
Source Management Views
Main views file that Django expects - imports from organized modules
"""

# Import all views from organized modules
from .views.source_list_views import source_list
from .views.source_crud_views import (
    source_create,
    source_detail,
    source_update,
    source_delete,
)
from .views.api_views import (
    api_source_metadata,
    api_video_access,
    api_video_metadata,
    api_video_download,
    api_video_stream,
    api_video_access_public,
    api_video_metadata_public,
    api_video_download_public,
    api_video_stream_public,
)
from .views.video_processing_views import (
    submit_video_processing,
    get_processing_status,
    cancel_processing_job,
    list_processing_jobs,
)
from .views.fastpublisher_views import (
    fastpublisher_status_check,
    fastpublisher_video_access,
    fastpublisher_submit_video,
    fastpublisher_video_metadata,
    fastpublisher_health,
)
from .views.health_views import (
    data_ingestion_health,
    data_ingestion_source_status,
)
from .views.callback_views import processing_callback
from .views.stream_control_views import (
    stream_create,
    stream_submit,
    stream_start,
    stream_stop,
    stream_status,
)

# Export all views for Django to find
__all__ = [
    # Base views
    'source_list',
    'source_create', 
    'source_detail',
    'source_update',
    'source_delete',
    
    # API views (authenticated)
    'api_source_metadata',
    'api_video_access',
    'api_video_metadata',
    'api_video_download',
    'api_video_stream',
    
    # Public API views (no authentication required)
    'api_video_access_public',
    'api_video_metadata_public',
    'api_video_download_public',
    'api_video_stream_public',
    
    # Video processing views
    'submit_video_processing',
    'get_processing_status',
    'cancel_processing_job',
    'list_processing_jobs',
    
    # FastPublisher views
    'fastpublisher_status_check',
    'fastpublisher_video_access',
    'fastpublisher_submit_video',
    'fastpublisher_video_metadata',
    'fastpublisher_health',
    
    # Health views
    'data_ingestion_health',
    'data_ingestion_source_status',
    
    # Stream control views
    'stream_create',
    'stream_submit',
    'stream_start',
    'stream_stop',
    'stream_status',
    
    # Callback views
    'processing_callback',
]
