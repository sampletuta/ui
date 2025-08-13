# video_player/urls.py

from django.urls import path
from . import views

app_name = 'video_player'

urlpatterns = [
    # Original video player views
    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    path('zm/live/<int:monitor_id>/', views.zm_live_stream, name='zm_live_stream'),
    path('sample/', views.sample_view, name='sample_view'),
    path('play/', views.play_from_url, name='play_from_url'),
    
    # Source management integration
    path('', views.source_video_list, name='source_video_list'),
    path('sources/', views.source_video_list, name='source_video_list'),
    path('source/<uuid:source_id>/', views.source_video_detail, name='source_video_detail'),
    path('stream/<uuid:source_id>/', views.stream_video, name='stream_video'),
    
    # API Endpoints for real-time data
    path('api/video-streams/', views.api_receive_video_streams, name='api_receive_video_streams'),
    path('api/detection-events/', views.api_receive_detection_events, name='api_receive_detection_events'),
    path('api/video-streams/get/', views.api_get_video_streams, name='api_get_video_streams'),
    path('api/detection-events/get/', views.api_get_detection_events, name='api_get_detection_events'),
    path('api/camera/<str:camera_id>/', views.api_update_camera, name='api_update_camera'),
    path('api/detection-event/add/', views.api_add_detection_event, name='api_add_detection_event'),
    path('api/clear-data/', views.api_clear_data, name='api_clear_data'),
]
