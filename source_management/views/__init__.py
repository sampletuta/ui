# Views package initialization
# Export all views from organized modules

from .source_list_views import source_list
from .source_crud_views import (
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
    api_video_access_public,
    api_video_metadata_public,
    api_video_download_public,
    api_video_stream_public,
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
from .callback_views import processing_callback
from .stream_control_views import (
    stream_create,
    stream_submit,
    stream_start,
    stream_stop,
    stream_status,
)

__all__ = [
    'source_list',
    'source_create', 
    'source_detail',
    'source_update',
    'source_delete',
    'api_source_metadata',
    'api_video_access',
    'api_video_metadata',
    'api_video_download',
    'api_video_stream',
    'api_video_access_public',
    'api_video_metadata_public',
    'api_video_download_public',
    'api_video_stream_public',
    'submit_video_processing',
    'get_processing_status',
    'cancel_processing_job',
    'list_processing_jobs',
    'fastpublisher_status_check',
    'fastpublisher_video_access',
    'fastpublisher_submit_video',
    'fastpublisher_video_metadata',
    'fastpublisher_health',
    'data_ingestion_health',
    'data_ingestion_source_status',
    'processing_callback',
    'stream_create',
    'stream_submit',
    'stream_start',
    'stream_stop',
    'stream_status',
]
