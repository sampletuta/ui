from django.urls import path
from . import views
from .views import face_verification_status, background_server_status

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
    
    # Target management URLs
    path('targets/<uuid:pk>/', views.target_profile, name='target_profile'),
    path('targets/<uuid:pk>/edit/', views.edit_target, name='edit_target'),
    path('targets/<uuid:pk>/delete/', views.delete_target, name='delete_target'),
    path('targets/<uuid:pk>/add-images/', views.add_images, name='add_images'),
    path('targets/<uuid:pk>/delete-image/<int:image_id>/', views.delete_image, name='delete_image'),
    
    # Watchlist management URLs
    path('watchlist/', views.list_watchlist, name='list_watchlist'),
    path('watchlist/add/', views.backend, name='add_watchlist'),
    
    # Video player URLs - TODO: Implement video_detail view
    # path('video/<uuid:video_id>/', views.video_detail, name='video_detail'),
    
    # Table view URLs - TODO: Implement table_view
    # path('table/', views.table_view, name='table_view'),
] 