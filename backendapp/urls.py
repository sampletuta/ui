from django.urls import path
from . import views
from .views import face_verification_status, background_server_status
from .views.detection_api_views import api_create_detection, api_create_detection_batch, api_get_detection_stats, api_get_detection_timeline
from .views.face_verification_views import face_verification_whitelist
from .views.media_views import serve_media
from .views.whitelist_views import (
    list_whitelist, whitelist_profile, add_whitelist, edit_whitelist,
    delete_whitelist, add_whitelist_images, delete_whitelist_image,
    approve_whitelist, suspend_whitelist
)

# Import new API views
from .views.search_api_views import api_submit_search, api_get_search_results, api_get_search_status
from .views.watchlist_api_views import api_submit_detection, api_submit_batch_detections, api_get_watchlist_targets, api_get_detection_stats
from .views.source_api_views import (
    api_register_camera, api_register_stream, api_register_file,
    api_get_source_status, api_list_sources, api_update_source, api_delete_source
)

urlpatterns = [
    # Dashboard and main views
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Authentication URLs
    path('login/', views.login, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='signout'),
    
    # User management URLs
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_form'),
    path('users/<uuid:pk>/', views.user_profile, name='user_detail'),
    path('users/<uuid:pk>/edit/', views.user_update, name='user_edit'),
    path('users/<uuid:pk>/delete/', views.user_delete, name='user_confirm_delete'),
    path('users/<uuid:pk>/unlock/', views.user_unlock, name='user_confirm_unlock'),
    path('profile/', views.profile, name='profile'),
    path('profile/<uuid:pk>/', views.user_profile, name='user_profile'),
    
    # Case management URLs
    path('cases/', views.case_list, name='case_list'),
    path('cases/add/', views.case_create, name='case_form'),
    path('cases/<uuid:pk>/', views.case_detail, name='case_detail'),
    path('cases/<uuid:pk>/edit/', views.case_edit, name='case_edit'),
    path('cases/<uuid:pk>/delete/', views.case_delete, name='case_confirm_delete'),
    path('cases/<uuid:case_pk>/add-target/', views.add_target_to_case,
         name='add_target_to_case'),
    
    # Face Verification Service
    path('face-verification/', views.face_verification, name='face_verification'),
    path('face-verification/preview/', views.face_verification_preview, name='face_verification_preview'),
    path('face-verification/watchlist/', views.face_verification_watchlist, name='face_verification_watchlist'),
    path('face-verification/whitelist/', face_verification_whitelist, name='face_verification_whitelist'),
    
    # Face Verification Status Checking
    path('face-verification/status/', face_verification_status.face_verification_status_api, name='face_verification_status'),
    path('face-verification/health/', face_verification_status.face_verification_health_check, name='face_verification_health'),
    
    # Background Server Status Checking
    path('background/status/', background_server_status.background_server_status_api, name='background_server_status'),
    path('background/health/', background_server_status.background_server_health_check, name='background_server_health'),
    path('background/celery/', background_server_status.celery_worker_status, name='celery_worker_status'),
    
    # Advanced Search URLs
    path('search/advanced/', views.advanced_search, name='advanced_search'),
    path('search/quick/', views.quick_search, name='quick_search'),
    path('search/milvus/', views.milvus_search, name='milvus_search'),
    path('search/results/<uuid:search_id>/', views.search_results_advanced, name='search_results_advanced'),
    path('search/history/', views.search_history, name='search_history'),
    
    # Legacy Search URLs (for backward compatibility)
    path('milvus-search/', views.milvus_search_legacy, name='milvus_search_legacy'),
    path('video-face-search/', views.video_face_search, name='video_face_search'),
    path('start-video-face-search/', views.start_video_face_search, name='start_video_face_search'),
    path('search-status/', views.search_status, name='search_status'),
    path('upload-chunk/', views.upload_chunk, name='upload_chunk'),
    path('search-results/<uuid:search_id>/', views.search_results, name='search_results'),
    
    # Settings route (using existing settings view)
    path('settings/', views.settings_view, name='settings'),

    # Notifications utilities
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('notifications/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    
    # Legacy Detection API endpoints (for backward compatibility)
    path('api/detections/create/', api_create_detection, name='api_create_detection'),
    path('api/detections/batch-create/', api_create_detection_batch, name='api_create_detection_batch'),
    path('api/detections/stats/', api_get_detection_stats, name='api_get_detection_stats'),
    path('api/detections/timeline/', api_get_detection_timeline, name='api_get_detection_timeline'),
    
    # New Separated API Endpoints
    
    # 1. Search API
    path('api/search/submit/', api_submit_search, name='api_submit_search'),
    path('api/search/results/<str:search_id>/', api_get_search_results, name='api_get_search_results'),
    path('api/search/status/<str:search_id>/', api_get_search_status, name='api_get_search_status'),
    
    # 2. Watchlist Monitoring API
    path('api/watchlist/detection/', api_submit_detection, name='api_submit_detection'),
    path('api/watchlist/detection/batch/', api_submit_batch_detections, name='api_submit_batch_detections'),
    path('api/watchlist/targets/', api_get_watchlist_targets, name='api_get_watchlist_targets'),
    path('api/watchlist/stats/', api_get_detection_stats, name='api_get_watchlist_stats'),
    
    # 3. Source Management API
    path('api/sources/camera/register/', api_register_camera, name='api_register_camera'),
    path('api/sources/stream/register/', api_register_stream, name='api_register_stream'),
    path('api/sources/file/register/', api_register_file, name='api_register_file'),
    path('api/sources/<str:source_id>/status/', api_get_source_status, name='api_get_source_status'),
    path('api/sources/list/', api_list_sources, name='api_list_sources'),
    path('api/sources/<str:source_id>/update/', api_update_source, name='api_update_source'),
    path('api/sources/<str:source_id>/delete/', api_delete_source, name='api_delete_source'),
    
    # Target management URLs
    path('targets/<uuid:pk>/', views.target_profile, name='target_profile'),
    path('targets/<uuid:pk>/edit/', views.edit_target, name='edit_target'),
    path('targets/<uuid:pk>/delete/', views.delete_target, name='delete_target'),
    path('targets/<uuid:pk>/add-images/', views.add_images, name='add_images'),
    path('targets/<uuid:pk>/delete-image/<int:image_id>/', views.delete_image, name='delete_image'),
    
    # Watchlist management URLs
    path('watchlist/', views.list_watchlist, name='list_watchlist'),
    path('watchlist/add/', views.backend, name='add_watchlist'),

    # Whitelist management URLs
    path('whitelist/', list_whitelist, name='list_whitelist'),
    path('whitelist/add/', add_whitelist, name='add_whitelist'),
    path('whitelist/<uuid:pk>/', whitelist_profile, name='whitelist_profile'),
    path('whitelist/<uuid:pk>/edit/', edit_whitelist, name='edit_whitelist'),
    path('whitelist/<uuid:pk>/delete/', delete_whitelist, name='delete_whitelist'),
    path('whitelist/<uuid:pk>/add-images/', add_whitelist_images, name='add_whitelist_images'),
    path('whitelist/<uuid:pk>/delete-image/<int:image_id>/', delete_whitelist_image, name='delete_whitelist_image'),
    path('whitelist/<uuid:pk>/approve/', approve_whitelist, name='approve_whitelist'),
    path('whitelist/<uuid:pk>/suspend/', suspend_whitelist, name='suspend_whitelist'),
    
    # Media serving for production (when DEBUG=False)
    path('media/<path:path>', serve_media, name='serve_media'),
] 