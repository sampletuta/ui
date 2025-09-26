"""
Source CRUD Views Module
Handles Create, Read, Update, Delete operations for sources using the Source Management Service
"""

import os
import uuid
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from .decorators import login_required_source_list
from ..services import SourceManagementService, VideoProcessingService
from ..forms import CameraSourceForm, FileSourceForm, StreamSourceForm

logger = logging.getLogger(__name__)

@login_required_source_list
def source_create(request):
    """Create a new source using the Source Management Service"""
    source_service = SourceManagementService()

    if request.method == 'POST':
        source_type = request.POST.get('source_type', 'file')
        logger.info(f"Form submitted for source type: {source_type}")

        # Validate form data
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
                # Prepare source data for API
                source_data = {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data.get('description', ''),
                    'location': form.cleaned_data.get('location', ''),
                    'latitude': form.cleaned_data.get('latitude'),
                    'longitude': form.cleaned_data.get('longitude'),
                    'type': source_type,
                    'is_active': True,
                    'tags': form.cleaned_data.get('tags', [])
                }

                # Add type-specific fields
                if source_type == 'camera':
                    source_data.update({
                        'camera_ip': form.cleaned_data['camera_ip'],
                        'camera_port': form.cleaned_data['camera_port'],
                        'camera_username': form.cleaned_data.get('camera_username', ''),
                        'camera_password': form.cleaned_data.get('camera_password', ''),
                        'camera_protocol': form.cleaned_data['camera_protocol'],
                        'camera_type': form.cleaned_data['camera_type'],
                        'camera_resolution_width': form.cleaned_data.get('camera_resolution_width'),
                        'camera_resolution_height': form.cleaned_data.get('camera_resolution_height'),
                        'camera_fps': form.cleaned_data.get('camera_fps'),
                        'camera_bitrate': form.cleaned_data.get('camera_bitrate'),
                        'camera_codec': form.cleaned_data.get('camera_codec', ''),
                        'camera_audio_enabled': form.cleaned_data.get('camera_audio_enabled', False),
                        'camera_audio_codec': form.cleaned_data.get('camera_audio_codec', ''),
                        'camera_audio_channels': form.cleaned_data.get('camera_audio_channels'),
                        'camera_audio_sample_rate': form.cleaned_data.get('camera_audio_sample_rate'),
                        'camera_buffer_size': form.cleaned_data.get('camera_buffer_size'),
                        'camera_timeout': form.cleaned_data.get('camera_timeout'),
                        'camera_keepalive': form.cleaned_data.get('camera_keepalive', True),
                        'camera_retry_attempts': form.cleaned_data.get('camera_retry_attempts', 3),
                        'zone': form.cleaned_data.get('zone', ''),
                        'configuration': form.cleaned_data.get('configuration', {}),
                        'topic_suffix': form.cleaned_data.get('topic_suffix', '')
                    })

                elif source_type == 'file':
                    # Handle file upload
                    if request.FILES.get('video_file'):
                        # For now, we'll create the source without the file
                        # The file upload will be handled in a separate step
                        source_data.update({
                            'file_format': form.cleaned_data.get('file_format', ''),
                            'file_size': form.cleaned_data.get('file_size'),
                            'configuration': form.cleaned_data.get('configuration', {})
                        })
                    else:
                        messages.error(request, 'No video file provided')
                        return render(request, 'source_management/source_form.html', {
                            'form': form,
                            'source_type': source_type,
                            'title': f'Create {source_type.title()} Source'
                        })

                elif source_type == 'stream':
                    source_data.update({
                        'stream_url': form.cleaned_data['stream_url'],
                        'stream_protocol': form.cleaned_data['stream_protocol'],
                        'stream_quality': form.cleaned_data.get('stream_quality', ''),
                        'stream_resolution_width': form.cleaned_data.get('stream_resolution_width'),
                        'stream_resolution_height': form.cleaned_data.get('stream_resolution_height'),
                        'stream_fps': form.cleaned_data.get('stream_fps'),
                        'stream_bitrate': form.cleaned_data.get('stream_bitrate'),
                        'stream_codec': form.cleaned_data.get('stream_codec', ''),
                        'stream_audio_codec': form.cleaned_data.get('stream_audio_codec', ''),
                        'stream_audio_channels': form.cleaned_data.get('stream_audio_channels'),
                        'stream_audio_sample_rate': form.cleaned_data.get('stream_audio_sample_rate'),
                        'stream_audio_bitrate': form.cleaned_data.get('stream_audio_bitrate'),
                        'stream_buffer_size': form.cleaned_data.get('stream_buffer_size'),
                        'stream_timeout': form.cleaned_data.get('stream_timeout'),
                        'stream_retry_attempts': form.cleaned_data.get('stream_retry_attempts', 3),
                        'stream_keepalive': form.cleaned_data.get('stream_keepalive', True),
                        'stream_parameters': form.cleaned_data.get('stream_parameters', {}),
                        'stream_headers': form.cleaned_data.get('stream_headers', {}),
                        'zone': form.cleaned_data.get('zone', ''),
                        'configuration': form.cleaned_data.get('configuration', {}),
                        'topic_suffix': form.cleaned_data.get('topic_suffix', '')
                    })

                # Create source via API
                result = source_service.create_source(source_data)

                if result['success']:
                    source_data = result['data']
                    source_id = source_data['source_id']

                    messages.success(request, f'{source_type.title()} source created successfully!')

                    # Handle file upload for file sources
                    if source_type == 'file' and request.FILES.get('video_file'):
                        # This would normally be handled by a separate upload process
                        # For now, we'll redirect to detail view
                        pass

                    return redirect('source_management:source_detail', source_id=source_id)
                else:
                    logger.error(f"Error creating source via API: {result.get('error')}")
                    messages.error(request, f'Error creating source: {result.get("error")}')

            except Exception as e:
                logger.error(f"Error creating {source_type} source: {e}")
                messages.error(request, f'Error creating {source_type} source: {str(e)}')
                return redirect('source_management:source_list')
        else:
            logger.error(f"Form validation errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
            return render(request, 'source_management/source_form.html', {
                'form': form,
                'source_type': source_type,
                'title': f'Create {source_type.title()} Source'
            })

    # GET request - show form
    source_type = request.GET.get('type', 'file')
    if source_type == 'file':
        form = FileSourceForm()
    elif source_type == 'camera':
        form = CameraSourceForm()
    elif source_type == 'stream':
        form = StreamSourceForm()
    else:
        source_type = 'file'
        form = FileSourceForm()

    return render(request, 'source_management/source_form.html', {
        'form': form,
        'source_type': source_type,
        'title': f'Create {source_type.title()} Source'
    })

@login_required_source_list
def source_detail(request, source_id):
    """Display source details using the Source Management Service"""
    source_service = SourceManagementService()

    try:
        # Get source data from API
        result = source_service.get_source(source_id)

        if result['success']:
            source = result['data']

            # Get additional data if needed
            context = {
                'source': source,
                'source_type': source.get('type', 'unknown'),
                'title': f"Source: {source.get('name', 'Unknown')}"
            }

            # Add type-specific context
            if source.get('type') == 'file':
                # Get video files if any
                files_result = source_service.get_video_files(source_id)
                if files_result['success']:
                    context['video_files'] = files_result['data']

            return render(request, 'source_management/source_detail.html', context)
        else:
            messages.error(request, f'Error retrieving source: {result.get("error")}')
            return redirect('source_management:source_list')

    except Exception as e:
        logger.error(f"Error getting source detail {source_id}: {e}")
        messages.error(request, f'Error retrieving source: {str(e)}')
        return redirect('source_management:source_list')

@login_required_source_list
def source_update(request, source_id):
    """Update a source using the Source Management Service"""
    source_service = SourceManagementService()

    try:
        # Get existing source data
        result = source_service.get_source(source_id)

        if not result['success']:
            messages.error(request, f'Error retrieving source: {result.get("error")}')
            return redirect('source_management:source_list')

        source = result['data']

        if request.method == 'POST':
            source_type = source.get('type', 'file')

            # Validate form data
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
                    # Prepare update data
                    update_data = {
                        'name': form.cleaned_data['name'],
                        'description': form.cleaned_data.get('description', ''),
                        'location': form.cleaned_data.get('location', ''),
                        'latitude': form.cleaned_data.get('latitude'),
                        'longitude': form.cleaned_data.get('longitude'),
                        'is_active': form.cleaned_data.get('is_active', source.get('is_active', True)),
                        'tags': form.cleaned_data.get('tags', [])
                    }

                    # Add type-specific fields
                    if source_type == 'camera':
                        update_data.update({
                            'camera_ip': form.cleaned_data['camera_ip'],
                            'camera_port': form.cleaned_data['camera_port'],
                            'camera_username': form.cleaned_data.get('camera_username', ''),
                            'camera_password': form.cleaned_data.get('camera_password', ''),
                            'camera_protocol': form.cleaned_data['camera_protocol'],
                            'camera_type': form.cleaned_data['camera_type'],
                            'camera_resolution_width': form.cleaned_data.get('camera_resolution_width'),
                            'camera_resolution_height': form.cleaned_data.get('camera_resolution_height'),
                            'camera_fps': form.cleaned_data.get('camera_fps'),
                            'camera_bitrate': form.cleaned_data.get('camera_bitrate'),
                            'camera_codec': form.cleaned_data.get('camera_codec', ''),
                            'camera_audio_enabled': form.cleaned_data.get('camera_audio_enabled', False),
                            'camera_audio_codec': form.cleaned_data.get('camera_audio_codec', ''),
                            'camera_audio_channels': form.cleaned_data.get('camera_audio_channels'),
                            'camera_audio_sample_rate': form.cleaned_data.get('camera_audio_sample_rate'),
                            'camera_buffer_size': form.cleaned_data.get('camera_buffer_size'),
                            'camera_timeout': form.cleaned_data.get('camera_timeout'),
                            'camera_keepalive': form.cleaned_data.get('camera_keepalive', True),
                            'camera_retry_attempts': form.cleaned_data.get('camera_retry_attempts', 3),
                            'zone': form.cleaned_data.get('zone', ''),
                            'configuration': form.cleaned_data.get('configuration', {}),
                            'topic_suffix': form.cleaned_data.get('topic_suffix', '')
                        })

                    elif source_type == 'stream':
                        update_data.update({
                            'stream_url': form.cleaned_data['stream_url'],
                            'stream_protocol': form.cleaned_data['stream_protocol'],
                            'stream_quality': form.cleaned_data.get('stream_quality', ''),
                            'stream_resolution_width': form.cleaned_data.get('stream_resolution_width'),
                            'stream_resolution_height': form.cleaned_data.get('stream_resolution_height'),
                            'stream_fps': form.cleaned_data.get('stream_fps'),
                            'stream_bitrate': form.cleaned_data.get('stream_bitrate'),
                            'stream_codec': form.cleaned_data.get('stream_codec', ''),
                            'stream_audio_codec': form.cleaned_data.get('stream_audio_codec', ''),
                            'stream_audio_channels': form.cleaned_data.get('stream_audio_channels'),
                            'stream_audio_sample_rate': form.cleaned_data.get('stream_audio_sample_rate'),
                            'stream_audio_bitrate': form.cleaned_data.get('stream_audio_bitrate'),
                            'stream_buffer_size': form.cleaned_data.get('stream_buffer_size'),
                            'stream_timeout': form.cleaned_data.get('stream_timeout'),
                            'stream_retry_attempts': form.cleaned_data.get('stream_retry_attempts', 3),
                            'stream_keepalive': form.cleaned_data.get('stream_keepalive', True),
                            'stream_parameters': form.cleaned_data.get('stream_parameters', {}),
                            'stream_headers': form.cleaned_data.get('stream_headers', {}),
                            'zone': form.cleaned_data.get('zone', ''),
                            'configuration': form.cleaned_data.get('configuration', {}),
                            'topic_suffix': form.cleaned_data.get('topic_suffix', '')
                        })

                    # Update source via API
                    result = source_service.update_source(source_id, update_data)

                    if result['success']:
                        messages.success(request, f'{source_type.title()} source updated successfully!')
                        return redirect('source_management:source_detail', source_id=source_id)
                    else:
                        logger.error(f"Error updating source via API: {result.get('error')}")
                        messages.error(request, f'Error updating source: {result.get("error")}')

                except Exception as e:
                    logger.error(f"Error updating {source_type} source: {e}")
                    messages.error(request, f'Error updating {source_type} source: {str(e)}')
                    return redirect('source_management:source_list')
            else:
                logger.error(f"Form validation errors: {form.errors}")
                messages.error(request, 'Please correct the errors below.')

        else:
            # GET request - populate form with existing data
            source_type = source.get('type', 'file')

            # Convert source data back to form format
            form_data = {
                'name': source.get('name', ''),
                'description': source.get('description', ''),
                'location': source.get('location', ''),
                'latitude': source.get('latitude'),
                'longitude': source.get('longitude'),
                'tags': source.get('tags', [])
            }

            # Add type-specific fields
            if source_type == 'camera':
                camera_data = source.get('configuration', {})
                form_data.update({
                    'camera_ip': camera_data.get('camera_ip', ''),
                    'camera_port': camera_data.get('camera_port', 554),
                    'camera_username': camera_data.get('camera_username', ''),
                    'camera_password': camera_data.get('camera_password', ''),
                    'camera_protocol': camera_data.get('camera_protocol', 'rtsp'),
                    'camera_type': camera_data.get('camera_type', 'ip'),
                    'camera_resolution_width': camera_data.get('camera_resolution_width'),
                    'camera_resolution_height': camera_data.get('camera_resolution_height'),
                    'camera_fps': camera_data.get('camera_fps'),
                    'camera_bitrate': camera_data.get('camera_bitrate'),
                    'camera_codec': camera_data.get('camera_codec', ''),
                    'camera_audio_enabled': camera_data.get('camera_audio_enabled', False),
                    'camera_audio_codec': camera_data.get('camera_audio_codec', ''),
                    'camera_audio_channels': camera_data.get('camera_audio_channels'),
                    'camera_audio_sample_rate': camera_data.get('camera_audio_sample_rate'),
                    'camera_buffer_size': camera_data.get('camera_buffer_size'),
                    'camera_timeout': camera_data.get('camera_timeout'),
                    'camera_keepalive': camera_data.get('camera_keepalive', True),
                    'camera_retry_attempts': camera_data.get('camera_retry_attempts', 3),
                    'zone': camera_data.get('zone', ''),
                    'configuration': camera_data.get('configuration', {}),
                    'topic_suffix': camera_data.get('topic_suffix', '')
                })
                form = CameraSourceForm(form_data)

            elif source_type == 'stream':
                stream_data = source.get('configuration', {})
                form_data.update({
                    'stream_url': stream_data.get('stream_url', ''),
                    'stream_protocol': stream_data.get('stream_protocol', 'rtsp'),
                    'stream_quality': stream_data.get('stream_quality', ''),
                    'stream_resolution_width': stream_data.get('stream_resolution_width'),
                    'stream_resolution_height': stream_data.get('stream_resolution_height'),
                    'stream_fps': stream_data.get('stream_fps'),
                    'stream_bitrate': stream_data.get('stream_bitrate'),
                    'stream_codec': stream_data.get('stream_codec', ''),
                    'stream_audio_codec': stream_data.get('stream_audio_codec', ''),
                    'stream_audio_channels': stream_data.get('stream_audio_channels'),
                    'stream_audio_sample_rate': stream_data.get('stream_audio_sample_rate'),
                    'stream_audio_bitrate': stream_data.get('stream_audio_bitrate'),
                    'stream_buffer_size': stream_data.get('stream_buffer_size'),
                    'stream_timeout': stream_data.get('stream_timeout'),
                    'stream_retry_attempts': stream_data.get('stream_retry_attempts', 3),
                    'stream_keepalive': stream_data.get('stream_keepalive', True),
                    'stream_parameters': stream_data.get('stream_parameters', {}),
                    'stream_headers': stream_data.get('stream_headers', {}),
                    'zone': stream_data.get('zone', ''),
                    'configuration': stream_data.get('configuration', {}),
                    'topic_suffix': stream_data.get('topic_suffix', '')
                })
                form = StreamSourceForm(form_data)

            else:
                # File source
                file_data = source.get('configuration', {})
                form_data.update({
                    'configuration': file_data.get('configuration', {})
                })
                form = FileSourceForm(form_data)

        # Render form
        return render(request, 'source_management/source_form.html', {
            'form': form,
            'source': source,
            'source_type': source_type,
            'title': f'Update {source_type.title()} Source'
        })

    except Exception as e:
        logger.error(f"Error in source update {source_id}: {e}")
        messages.error(request, f'Error retrieving source: {str(e)}')
        return redirect('source_management:source_list')

@login_required_source_list
def source_delete(request, source_id):
    """Delete a source using the Source Management Service"""
    source_service = SourceManagementService()

    if request.method == 'POST':
        try:
            # Delete source via API
            result = source_service.delete_source(source_id)

            if result['success']:
                messages.success(request, 'Source deleted successfully!')
                return redirect('source_management:source_list')
            else:
                logger.error(f"Error deleting source via API: {result.get('error')}")
                messages.error(request, f'Error deleting source: {result.get("error")}')

        except Exception as e:
            logger.error(f"Error deleting source {source_id}: {e}")
            messages.error(request, f'Error deleting source: {str(e)}')

    # GET request - show confirmation
    try:
        result = source_service.get_source(source_id)

        if result['success']:
            source = result['data']
            return render(request, 'source_management/source_confirm_delete.html', {
                'source': source,
                'source_type': source.get('type', 'unknown'),
                'title': f'Delete {source.get("name", "Unknown")}'
            })
        else:
            messages.error(request, f'Error retrieving source: {result.get("error")}')
            return redirect('source_management:source_list')

    except Exception as e:
        logger.error(f"Error getting source for deletion {source_id}: {e}")
        messages.error(request, f'Error retrieving source: {str(e)}')
        return redirect('source_management:source_list')
