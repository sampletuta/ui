"""
Source List Views Module
Handles listing and displaying sources
"""

from django.shortcuts import render
from django.core.paginator import Paginator
from django.conf import settings
from .decorators import login_required_source_list
from ..models import CameraSource, FileSource, StreamSource


@login_required_source_list
def source_list(request):
    """List all sources"""
    sources = []
    
    # Performance: limit fields and rows fetched; compute counts separately
    limit_total = getattr(settings, 'SOURCE_LIST_MAX_ITEMS', 500)
    per_type_limit = max(1, limit_total // 3)

    file_sources_qs = (
        FileSource.objects.only('source_id', 'name', 'location', 'status', 'created_at', 'file_size', 'access_token')
        .order_by('-created_at')[:per_type_limit]
    )
    camera_sources_qs = (
        CameraSource.objects.only('source_id', 'name', 'location', 'created_at', 'zone', 'is_active', 'camera_ip', 'camera_port')
        .order_by('-created_at')[:per_type_limit]
    )
    stream_sources_qs = (
        StreamSource.objects.only('source_id', 'name', 'location', 'created_at', 'stream_protocol')
        .order_by('-created_at')[:per_type_limit]
    )
    
    # Combine and format sources
    for source in file_sources_qs:
        sources.append({
            'source_id': source.source_id,
            'name': source.name,
            'type': 'file',
            'type_display': 'Video File',
            'location': source.location,
            'status': source.status,
            'created_at': source.created_at,
            'file_size': source.file_size,
            'access_token': source.access_token[:8] + '...' if source.access_token else None,
            'zone': getattr(source, 'zone', ''),
            'is_active': getattr(source, 'is_active', True),
            'color': 'success',
            'icon': 'fa-file-video',
            'info': f'Size: {source.get_file_size_display()}' if source.file_size else 'File uploaded',
        })
    
    for source in camera_sources_qs:
        sources.append({
            'source_id': source.source_id,
            'name': source.name,
            'type': 'camera',
            'type_display': 'IP Camera',
            'location': source.location,
            'status': 'active' if source.is_active else 'inactive',
            'created_at': source.created_at,
            'zone': source.zone,
            'is_active': source.is_active,
            'color': 'primary',
            'icon': 'fa-video-camera',
            'info': f'{source.camera_ip}:{source.camera_port}' if source.camera_ip else 'Camera configured',
        })
    
    for source in stream_sources_qs:
        sources.append({
            'source_id': source.source_id,
            'name': source.name,
            'type': 'stream',
            'type_display': 'Video Stream',
            'location': source.location,
            'status': 'active',
            'created_at': source.created_at,
            'zone': getattr(source, 'zone', ''),
            'is_active': getattr(source, 'is_active', True),
            'color': 'info',
            'icon': 'fa-broadcast-tower',
            'info': f'{source.stream_protocol.upper()} stream' if hasattr(source, 'stream_protocol') else 'Stream configured',
        })
    
    # Sort by creation date (newest first)
    sources.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Pagination
    paginator = Paginator(sources, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Compute counts without loading full rows
    file_sources_count = FileSource.objects.count()
    camera_sources_count = CameraSource.objects.count()
    stream_sources_count = StreamSource.objects.count()

    context = {
        'sources': page_obj,
        'total_sources': file_sources_count + camera_sources_count + stream_sources_count,
        'file_sources_count': file_sources_count,
        'camera_sources_count': camera_sources_count,
        'stream_sources_count': stream_sources_count,
    }
    return render(request, 'source_management/source_list.html', context)
