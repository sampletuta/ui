from django.contrib import admin
from .models import CameraSource, FileSource, StreamSource, VideoProcessingJob

@admin.register(CameraSource)
class CameraSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'camera_ip', 'camera_protocol', 'location', 'zone', 'is_active', 'created_at']
    list_filter = ['camera_type', 'camera_protocol', 'zone', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'location', 'camera_ip']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location', 'latitude', 'longitude', 'tags')
        }),
        ('Camera Configuration', {
            'fields': ('camera_ip', 'camera_port', 'camera_username', 'camera_password', 
                      'camera_protocol', 'camera_type', 'camera_resolution', 'camera_fps')
        }),
        ('Zone & Status', {
            'fields': ('zone', 'is_active', 'configuration')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(FileSource)
class FileSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'file_size', 'duration', 'created_at']
    list_filter = ['status', 'file_format', 'created_at']
    search_fields = ['name', 'description', 'location']
    readonly_fields = ['source_id', 'access_token', 'api_endpoint', 'stream_url', 'thumbnail_url', 
                      'created_at', 'updated_at', 'processing_started_at', 'processing_completed_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location', 'latitude', 'longitude', 'tags')
        }),
        ('Video File', {
            'fields': ('video_file', 'file_format', 'file_size', 'status')
        }),
        ('Video Metadata', {
            'fields': ('duration', 'width', 'height', 'fps', 'bitrate', 'codec', 
                      'audio_codec', 'audio_channels', 'audio_sample_rate')
        }),
        ('Access & URLs', {
            'fields': ('access_token', 'api_endpoint', 'stream_url', 'thumbnail_url'),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processing_started_at', 'processing_completed_at', 'processing_error'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('recording_date', 'camera_info', 'scene_info'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StreamSource)
class StreamSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'stream_protocol', 'location', 'created_at', 'created_by']
    list_filter = ['stream_protocol', 'created_at', 'created_by']
    search_fields = ['name', 'description', 'location', 'stream_url']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location', 'latitude', 'longitude', 'tags')
        }),
        ('Stream Configuration', {
            'fields': ('stream_url', 'stream_protocol', 'stream_quality', 'stream_parameters')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VideoProcessingJob)
class VideoProcessingJobAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'source', 'status', 'target_fps', 'target_resolution', 'submitted_at', 'external_job_id']
    list_filter = ['status', 'submitted_at', 'target_fps']
    search_fields = ['job_id', 'source__name', 'external_job_id']
    readonly_fields = ['job_id', 'submitted_at', 'started_at', 'completed_at', 'external_response']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_id', 'external_job_id', 'source', 'status')
        }),
        ('Processing Parameters', {
            'fields': ('target_fps', 'target_resolution')
        }),
        ('Timing', {
            'fields': ('submitted_at', 'started_at', 'completed_at')
        }),
        ('External Service', {
            'fields': ('external_service_url', 'callback_url', 'access_token')
        }),
        ('Results', {
            'fields': ('processed_video_url', 'processing_metadata', 'error_message'),
            'classes': ('collapse',)
        }),
        ('External Response', {
            'fields': ('external_response',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of processing jobs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow editing of processing jobs"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of processing jobs"""
        return True
