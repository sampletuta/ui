"""
Source CRUD Views Module
Handles Create, Read, Update, Delete operations for sources
"""

import os
import uuid
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .decorators import login_required_source_list
from ..models import CameraSource, FileSource, StreamSource
from ..forms import CameraSourceForm, FileSourceForm, StreamSourceForm

logger = logging.getLogger(__name__)


@login_required_source_list
def source_create(request):
    """Create a new source"""
    if request.method == 'POST':
        source_type = request.POST.get('source_type', 'file')
        logger.info(f"Form submitted for source type: {source_type}")
        logger.info(f"POST data: {request.POST}")
        
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
                    source = form.save(commit=False)
                    source.source_id = uuid.uuid4()
                    source.created_by = request.user
                    
                    if source_type == 'file':
                        file_source = source
                        chunked_upload_id = request.POST.get('chunked_upload_id') or form.cleaned_data.get('chunked_upload_id')
                        chunked_original_filename = request.POST.get('chunked_original_filename') or form.cleaned_data.get('chunked_original_filename')
                        
                        if chunked_upload_id and chunked_original_filename and not request.FILES.get('video_file'):
                            from django.core.files import File
                            final_dir = os.path.join(settings.MEDIA_ROOT, 'search_videos')
                            assembled_path = os.path.join(final_dir, f'{chunked_upload_id}_{chunked_original_filename}')
                            if not os.path.exists(assembled_path):
                                raise Exception('Assembled upload not found. Please retry upload.')
                            
                            videos_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
                            os.makedirs(videos_dir, exist_ok=True)
                            target_path = os.path.join(videos_dir, chunked_original_filename)
                            os.replace(assembled_path, target_path)
                            
                            with open(target_path, 'rb') as f:
                                file_source.video_file.save(os.path.basename(target_path), File(f), save=False)
                            try:
                                os.remove(target_path)
                            except OSError:
                                pass

                        file_source.access_token = uuid.uuid4().hex
                        file_source.api_endpoint = f"{request.scheme}://{request.get_host()}/source-management/api/video/{file_source.access_token}/"
                        file_source.stream_url = f"{request.scheme}://{request.get_host()}/source-management/api/video/{file_source.access_token}/stream/"
                        file_source.thumbnail_url = f"{request.scheme}://{request.get_host()}/source-management/api/video/{file_source.access_token}/thumbnail/"
                        
                        file_source.status = 'uploading'
                        file_source.processing_started_at = timezone.now()
                        
                        if file_source.video_file:
                            file_source.file_format = os.path.splitext(file_source.video_file.name)[1][1:].lower()
                            file_source.file_size = file_source.video_file.size
                        
                        file_source.save()
                        
                        # Extract video metadata before proceeding
                        if file_source.video_file:
                            try:
                                logger.info(f"Extracting metadata for file source {file_source.source_id}")
                                if file_source.extract_video_metadata():
                                    file_source.status = 'ready'
                                    file_source.processing_completed_at = timezone.now()
                                    logger.info(f"Successfully extracted metadata for file source {file_source.source_id}")
                                else:
                                    logger.warning(f"Failed to extract metadata for file source {file_source.source_id}")
                                    file_source.status = 'failed'
                                    file_source.processing_error = "Failed to extract video metadata"
                                    file_source.processing_completed_at = timezone.now()
                                
                                file_source.save()
                                
                                # Only proceed with data ingestion if metadata extraction was successful
                                if file_source.status == 'ready':
                                    def _notify_data_ingestion():
                                        try:
                                            from ..services import DataIngestionService
                                            ingestion_service = DataIngestionService()
                                            result = ingestion_service.notify_new_source(file_source)
                                            
                                            if result['success']:
                                                file_source.ingestion_notified = True
                                                file_source.ingestion_notified_at = timezone.now()
                                                file_source.ingestion_response = result.get('response', {})
                                            else:
                                                logger.warning(f"Failed to notify data ingestion service: {result.get('error', 'Unknown error')}")
                                            
                                            file_source.save()
                                            
                                        except Exception as e:
                                            logger.error(f"Error notifying data ingestion service: {e}")
                                            file_source.save()
                                    
                                    transaction.on_commit(_notify_data_ingestion)
                                else:
                                    messages.warning(request, f'File source "{file_source.name}" created but metadata extraction failed. Please check the file and try again.')
                                    return redirect('source_management:file_detail', source_id=file_source.source_id)
                                    
                            except Exception as e:
                                logger.error(f"Error during metadata extraction for file source {file_source.source_id}: {e}")
                                file_source.status = 'failed'
                                file_source.processing_error = str(e)
                                file_source.processing_completed_at = timezone.now()
                                file_source.save()
                                messages.error(request, f'Error extracting metadata: {str(e)}')
                                return redirect('source_management:file_detail', source_id=file_source.source_id)
                        else:
                            # No video file to process
                            file_source.status = 'ready'
                            file_source.processing_completed_at = timezone.now()
                            file_source.save()
                            
                            def _notify_data_ingestion():
                                try:
                                    from ..services import DataIngestionService
                                    ingestion_service = DataIngestionService()
                                    result = ingestion_service.notify_new_source(file_source)
                                    
                                    if result['success']:
                                        file_source.ingestion_notified = True
                                        file_source.ingestion_notified_at = timezone.now()
                                        file_source.ingestion_response = result.get('response', {})
                                    else:
                                        logger.warning(f"Failed to notify data ingestion service: {result.get('error', 'Unknown error')}")
                                    
                                    file_source.save()
                                    
                                except Exception as e:
                                    logger.error(f"Error notifying data ingestion service: {e}")
                                    file_source.save()
                            
                            transaction.on_commit(_notify_data_ingestion)
                        
                        messages.success(request, f'File source "{file_source.name}" created successfully. Notifying data ingestion service...')
                        return redirect('source_management:file_detail', source_id=file_source.source_id)
                    
                    else:
                        # For camera and stream sources
                        logger.info(f"Creating {source_type} source: {source.name}")
                        source.save()
                        
                        # Check if stream processor integration was successful
                        try:
                            if source_type in ['camera', 'stream'] and source.is_active:
                                # Test the integration by getting processor status
                                processor_status = source.get_processor_status()
                                if processor_status.get('success', False):
                                    messages.success(request, f'{source_type.title()} source "{source.name}" created successfully and integrated with stream processor service.')
                                else:
                                    messages.warning(request, f'{source_type.title()} source "{source.name}" created but stream processor integration failed: {processor_status.get("error", "Unknown error")}')
                            else:
                                messages.success(request, f'{source_type.title()} source "{source.name}" created successfully.')
                        except Exception as e:
                            logger.error(f"Error checking stream processor integration for {source_type} source {source.source_id}: {e}")
                            messages.warning(request, f'{source_type.title()} source "{source.name}" created but there was an issue with stream processor integration.')
                        
                        return redirect('source_management:' + source_type + '_detail', source_id=source.source_id)
                        
            except Exception as e:
                messages.error(request, f'Error creating {source_type} source: {str(e)}')
                return redirect('source_management:source_list')
        else:
            # Form validation failed - log the errors for debugging
            logger.error(f"Form validation failed for {source_type} source. Errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            messages.error(request, 'Please correct the errors below.')
    else:
        source_type = request.GET.get('type', 'file')
        logger.info(f"Creating form for source type: {source_type}")
        # Validate source_type parameter
        if source_type not in ['file', 'camera', 'stream']:
            messages.error(request, 'Invalid source type specified.')
            return redirect('source_management:source_list')
            
        if source_type == 'file':
            form = FileSourceForm(instance=None)
        elif source_type == 'camera':
            form = CameraSourceForm(instance=None)
        elif source_type == 'stream':
            form = StreamSourceForm(instance=None)
        else:
            form = FileSourceForm(instance=None)
    
    context = {
        'form': form,
        'source_type': source_type,
        'is_edit': False,  # Explicitly set this for add operations
    }
    
    try:
        if source_type == 'file':
            context['chunk_threshold'] = getattr(settings, 'CHUNKED_UPLOAD_THRESHOLD', 100 * 1024 * 1024)
            context['chunk_size'] = getattr(settings, 'CHUNK_SIZE', 1024 * 1024)
    except Exception:
        pass
    
    return render(request, 'source_management/source_form.html', context)


@login_required_source_list
def source_detail(request, source_id):
    """View source details"""
    source = None
    source_type = None
    
    try:
        source = FileSource.objects.get(source_id=source_id)
        source_type = 'file'
    except FileSource.DoesNotExist:
        pass
    
    if not source:
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
        except CameraSource.DoesNotExist:
            pass
    
    if not source:
        try:
            source = StreamSource.objects.get(source_id=source_id)
            source_type = 'stream'
        except StreamSource.DoesNotExist:
            pass
    
    if not source:
        messages.error(request, 'Source not found.')
        return redirect('source_management:source_list')
    
    context = {
        'source': source,
        'source_type': source_type,
    }
    
    # Add stream processor service status for camera and stream sources
    if source_type in ['camera', 'stream'] and source.is_active:
        try:
            processor_status = source.get_processor_status()
            context['processor_status'] = processor_status
        except Exception as e:
            logger.error(f"Error getting processor status for {source_type} source {source.source_id}: {e}")
            context['processor_status'] = {'success': False, 'error': str(e)}
    
    return render(request, 'source_management/source_detail.html', context)


@login_required_source_list
def source_update(request, source_id):
    """Update source details"""
    source = None
    source_type = None
    form_class = None
    
    try:
        source = FileSource.objects.get(source_id=source_id)
        source_type = 'file'
        form_class = FileSourceForm
    except FileSource.DoesNotExist:
        pass
    
    if not source:
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
            form_class = CameraSourceForm
        except CameraSource.DoesNotExist:
            pass
    
    if not source:
        try:
            source = StreamSource.objects.get(source_id=source_id)
            source_type = 'stream'
            form_class = StreamSourceForm
        except StreamSource.DoesNotExist:
            pass
    
    if not source:
        messages.error(request, 'Source not found.')
        return redirect('source_management:source_list')
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=source)
        if form.is_valid():
            form.save()
            
            # Check if stream processor integration was successful for camera/stream sources
            try:
                if source_type in ['camera', 'stream'] and source.is_active:
                    # Test the integration by getting processor status
                    processor_status = source.get_processor_status()
                    if processor_status.get('success', False):
                        messages.success(request, f'{source_type.title()} source "{source.name}" updated successfully and stream processor service updated.')
                    else:
                        messages.warning(request, f'{source_type.title()} source "{source.name}" updated but stream processor integration failed: {processor_status.get("error", "Unknown error")}')
                else:
                    messages.success(request, f'{source_type.title()} source "{source.name}" updated successfully.')
            except Exception as e:
                logger.error(f"Error checking stream processor integration for {source_type} source {source.source_id}: {e}")
                messages.warning(request, f'{source_type.title()} source "{source.name}" updated but there was an issue with stream processor integration.')
            
            return redirect('source_management:' + source_type + '_detail', source_id=source.source_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = form_class(instance=source)
    
    context = {
        'form': form,
        'source': source,
        'source_type': source_type,
        'is_edit': True,  # Explicitly set this for edit operations
    }
    return render(request, 'source_management/source_form.html', context)


@login_required_source_list
def source_delete(request, source_id):
    """Delete a source"""
    source = None
    source_type = None
    
    try:
        source = FileSource.objects.get(source_id=source_id)
        source_type = 'file'
    except FileSource.DoesNotExist:
        pass
    
    if not source:
        try:
            source = CameraSource.objects.get(source_id=source_id)
            source_type = 'camera'
        except CameraSource.DoesNotExist:
            pass
    
    if not source:
        try:
            source = StreamSource.objects.get(source_id=source_id)
            source_type = 'stream'
        except StreamSource.DoesNotExist:
            pass
    
    if not source:
        messages.error(request, 'Source not found.')
        return redirect('source_management:source_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                source_name = source.name
                
                # For camera and stream sources, delete from stream processor service first
                if source_type in ['camera', 'stream']:
                    try:
                        # Call the delete method which will handle stream processor deletion
                        source.delete()
                        messages.success(request, f'{source_type.title()} source "{source_name}" deleted successfully from both database and stream processor service.')
                    except Exception as e:
                        logger.error(f"Error deleting {source_type} source {source_id} from stream processor: {e}")
                        # Even if stream processor deletion fails, delete from database
                        source.delete()
                        messages.warning(request, f'{source_type.title()} source "{source_name}" deleted from database but there was an issue with stream processor service cleanup.')
                else:
                    # For file sources, just delete from database
                    source.delete()
                    messages.success(request, f'{source_type.title()} source "{source_name}" deleted successfully.')
                    
        except Exception as e:
            messages.error(request, f'Error deleting {source_type} source: {str(e)}')
        
        return redirect('source_management:source_list')
    
    context = {
        'source': source,
        'source_type': source_type,
    }
    return render(request, 'source_management/source_confirm_delete.html', context)
