"""
Base Views Module
Contains core CRUD operations for sources (file, camera, stream)
"""

import os
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .decorators import login_required_source_list
from ..models import CameraSource, FileSource, StreamSource
from ..forms import CameraSourceForm, FileSourceForm, StreamSourceForm

logger = logging.getLogger(__name__)


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


@login_required_source_list
def source_create(request):
    """Create a new source"""
    if request.method == 'POST':
        source_type = request.POST.get('source_type', 'file')
        
        if source_type == 'file':
            form = FileSourceForm(request.POST, request.FILES)
        elif source_type == 'camera':
            form = CameraSourceForm(request.POST)
        elif source_type == 'stream':
            form = StreamSourceForm(request.POST)
        else:
            messages.error(request, 'Invalid source type')
            return redirect('source_management:source_list')
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the source object
                    source = form.save(commit=False)
                    source.source_id = uuid.uuid4()
                    source.created_by = request.user
                    
                    # For file sources, handle file upload and metadata extraction
                    if source_type == 'file':
                        file_source = source
                        # If uploaded via chunked path, assemble final file path from existing file
                        chunked_upload_id = request.POST.get('chunked_upload_id') or form.cleaned_data.get('chunked_upload_id')
                        chunked_original_filename = request.POST.get('chunked_original_filename') or form.cleaned_data.get('chunked_original_filename')
                        if chunked_upload_id and chunked_original_filename and not request.FILES.get('video_file'):
                            # Move/rename the pre-assembled chunked upload into videos storage
                            from django.core.files import File
                            final_dir = os.path.join(settings.MEDIA_ROOT, 'search_videos')
                            assembled_path = os.path.join(final_dir, f'{chunked_upload_id}_{chunked_original_filename}')
                            if not os.path.exists(assembled_path):
                                raise Exception('Assembled upload not found. Please retry upload.')
                            # Ensure videos directory exists
                            videos_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
                            os.makedirs(videos_dir, exist_ok=True)
                            target_path = os.path.join(videos_dir, chunked_original_filename)
                            # Move the file
                            os.replace(assembled_path, target_path)
                            # Attach to model FileField
                            with open(target_path, 'rb') as f:
                                file_source.video_file.save(os.path.basename(target_path), File(f), save=False)
                                # Remove the temp file after saving into storage backend
                            try:
                                os.remove(target_path)
                            except OSError:
                                pass

                        # Generate access token and API endpoint
                        file_source.access_token = uuid.uuid4().hex
                        file_source.api_endpoint = f"{request.scheme}://{request.get_host()}/source-management/api/video/{file_source.access_token}/"
                        file_source.stream_url = f"{request.scheme}://{request.get_host()}/source-management/api/video/{file_source.access_token}/stream/"
                        file_source.thumbnail_url = f"{request.scheme}://{request.get_host()}/source-management/api/video/{file_source.access_token}/thumbnail/"
                        
                        # Set initial status and extract basic metadata
                        file_source.status = 'uploading'
                        file_source.processing_started_at = timezone.now()
                        
                        # Extract basic file metadata
                        if file_source.video_file:
                            file_source.file_format = os.path.splitext(file_source.video_file.name)[1][1:].lower()
                            file_source.file_size = file_source.video_file.size
                        
                        # Save the file source
                        file_source.save()
                        
                        # Notify data ingestion service about new source
                        def _notify_data_ingestion():
                            try:
                                from ..services import DataIngestionService
                                ingestion_service = DataIngestionService()
                                result = ingestion_service.notify_new_source(file_source)
                                
                                # Update file source with notification status
                                if result['success']:
                                    file_source.ingestion_notified = True
                                    file_source.ingestion_notified_at = timezone.now()
                                    file_source.ingestion_response = result.get('response', {})
                                    file_source.status = 'ready'
                                    file_source.processing_completed_at = timezone.now()
                                else:
                                    # Log error but don't fail the source creation
                                    logger.warning(f"Failed to notify data ingestion service: {result.get('error', 'Unknown error')}")
                                    file_source.status = 'ready'  # Still mark as ready
                                    file_source.processing_completed_at = timezone.now()
                                
                                file_source.save()
                                
                            except Exception as e:
                                logger.error(f"Error notifying data ingestion service: {e}")
                                # Don't fail the source creation, just mark as ready
                                file_source.status = 'ready'
                                file_source.processing_completed_at = timezone.now()
                                file_source.save()

                        # Run notification in background thread
                        transaction.on_commit(_notify_data_ingestion)
                        
                        messages.success(request, f'File source created successfully. Please wait for the file to be processed.')
                        return redirect('source_management:source_list')
        else:
            messages.error(request, 'Invalid form submission')
            return redirect('source_management:source_list')
    else:
        form = FileSourceForm()
        return render(request, 'source_management/source_form.html', {'form': form})