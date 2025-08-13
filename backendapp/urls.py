from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication - Using custom views
    path('login/', views.login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    
    # User Management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_update, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:user_id>/unlock/', views.user_unlock, name='user_unlock'),
    path('profile/', views.user_profile, name='profile'),
    
    # API endpoints
    path('api/users/<int:user_id>/status/', views.api_user_status, name='api_user_status'),
    
    # Main app routes
    path('', views.dashboard, name='dashboard'),  # Root URL for dashboard
    path('backend/', views.backend, name='backend'),
    path('watchlist/', views.list_watchlist, name='list_watchlist'),
    path('watchlist/<uuid:pk>/', views.target_profile, name='target_profile'),
    path('watchlist/<uuid:pk>/edit/', views.edit_target, name='edit_target'),
    path('watchlist/<uuid:pk>/delete/', views.delete_target, name='delete_target'),
    path('watchlist/<uuid:pk>/add-images/', views.add_images, name='add_images'),
    path('watchlist/<uuid:pk>/delete-image/<int:image_id>/', views.delete_image, name='delete_image'),
    
    # Case Management URLs
    path('cases/', views.case_list, name='case_list'),
    path('cases/create/', views.case_create, name='case_create'),
    path('cases/<uuid:pk>/', views.case_detail, name='case_detail'),
    path('cases/<uuid:pk>/edit/', views.case_edit, name='case_edit'),
    path('cases/<uuid:pk>/delete/', views.case_delete, name='case_delete'),
    path('cases/<uuid:case_pk>/add-target/', views.add_target_to_case, name='add_target_to_case'),
    
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
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    
    # Commented out routes that need to be re-implemented
    # path('table/', views.table, name='table'),
] 