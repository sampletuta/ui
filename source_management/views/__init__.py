# Source Management Views Package
# This package organizes views into logical modules for better maintainability

# Import all view functions to maintain backward compatibility
from .base_views import (
    source_list,
    source_create,
    source_detail,
    source_update,
    source_delete,
)

from .api_views import (
    api_source_metadata,
    api_video_access,
    api_video_metadata,
    api_video_download,
    api_video_stream,
)

from .video_processing_views import (
    submit_video_processing,
    get_processing_status,
    cancel_processing_job,
    list_processing_jobs,
)

from .fastpublisher_views import (
    fastpublisher_status_check,
    fastpublisher_video_access,
    fastpublisher_submit_video,
    fastpublisher_video_metadata,
    fastpublisher_health,
)

from .health_views import (
    data_ingestion_health,
    data_ingestion_source_status,
)

from .callback_views import (
    processing_callback,
)

# Export all views for backward compatibility
__all__ = [
    # Base views
    'source_list',
    'source_create', 
    'source_detail',
    'source_update',
    'source_delete',
    
    # API views
    'api_source_metadata',
    'api_video_access',
    'api_video_metadata',
    'api_video_download',
    'api_video_stream',
    
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
    
    # Callback views
    'processing_callback',
]
