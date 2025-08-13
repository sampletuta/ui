import requests
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.core.paginator import Paginator
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import os
import json
import logging
import uuid
import threading
import re
import subprocess
from .models import CameraSource, FileSource, StreamSource

logger = logging.getLogger(__name__)
from .forms import CameraSourceForm, FileSourceForm, StreamSourceForm


def login_required_source_list(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return _wrapped_view

@login_required_source_list
def source_list(request):
    """List all sources"""
    sources = []
    
    # Get all source types
    file_sources = FileSource.objects.all()
    camera_sources = CameraSource.objects.all()
    stream_sources = StreamSource.objects.all()
    
    # Combine and format sources
    for source in file_sources:
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
    
    for source in camera_sources:
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
    
    for source in stream_sources:
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
    
    context = {
        'sources': page_obj,
        'total_sources': len(sources),
        'file_sources_count': file_sources.count(),
        'camera_sources_count': camera_sources.count(),
        'stream_sources_count': stream_sources.count(),
    }
    return render(request, 'source_management/source_list.html', context)

def process_video_async(file_source_id):
    """Process video file asynchronously to extract metadata"""
    try:
        # Get the file source
        file_source = FileSource.objects.get(source_id=file_source_id)
        
        # Update status to processing (idempotent)
        if file_source.status != 'processing':
            file_source.status = 'processing'
            file_source.processing_started_at = timezone.now()
            file_source.save(update_fields=['status', 'processing_started_at'])
        
        # Get the video file path
        video_file = file_source.video_file
        if not video_file:
            raise Exception("No video file found")
        
        file_path = video_file.path
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise Exception(f"Video file not found at {file_path}")
        
        # Extract metadata using ffprobe
        metadata = extract_video_metadata(file_path)
        
        # Update file source with metadata
        file_source.duration = metadata.get('duration')
        file_source.width = metadata.get('width')
        file_source.height = metadata.get('height')
        file_source.fps = metadata.get('fps')
        file_source.bitrate = metadata.get('bitrate')
        file_source.codec = metadata.get('video_codec')
        file_source.audio_codec = metadata.get('audio_codec')
        file_source.audio_channels = metadata.get('audio_channels')
        file_source.audio_sample_rate = metadata.get('audio_sample_rate')
        
        # Set file format and size
        file_source.file_format = os.path.splitext(video_file.name)[1][1:].lower()
        file_source.file_size = video_file.size
        
        # Update status to ready
        file_source.status = 'ready'
        file_source.processing_completed_at = timezone.now()
        file_source.save(update_fields=['status', 'processing_completed_at', 'duration', 'width', 'height', 'fps', 'bitrate', 'codec', 'audio_codec', 'audio_channels', 'audio_sample_rate', 'file_format', 'file_size'])
        
        print(f"Successfully processed video: {file_source.name}")

        # Auto-submit to FastPublisher once the file is ready
        try:
            from .services import VideoProcessingService
            processing_service = VideoProcessingService()
            # Submit without explicit processing params; FastPublisher applies defaults
            threading.Thread(target=processing_service.submit_video_processing, args=(file_source,), daemon=True).start()
        except Exception as submit_err:
            logger.error(f"Auto-submit to FastPublisher failed for {file_source.source_id}: {submit_err}")
        
    except FileSource.DoesNotExist:
        print(f"FileSource with ID {file_source_id} not found")
    except Exception as e:
        print(f"Error processing video {file_source_id}: {str(e)}")
        try:
            # Update status to failed
            file_source = FileSource.objects.get(source_id=file_source_id)
            file_source.status = 'failed'
            file_source.processing_error = str(e)
            file_source.processing_completed_at = timezone.now()
            file_source.save(update_fields=['status', 'processing_error', 'processing_completed_at'])
        except:
            pass

def extract_video_metadata(file_path):
    """Extract video metadata using ffprobe"""
    try:
        # Run ffprobe to get video information (ffprobe is part of ffmpeg package installed in Dockerfile)
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")
        
        data = json.loads(result.stdout)
        
        # Extract video stream info
        video_stream = None
        audio_stream = None
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream
        
        metadata = {}
        
        # Video metadata
        if video_stream:
            metadata['width'] = int(video_stream.get('width', 0))
            metadata['height'] = int(video_stream.get('height', 0))
            # Safely parse frame rate fraction
            frame_rate_str = video_stream.get('r_frame_rate', '0/1')
            try:
                numerator, denominator = frame_rate_str.split('/')
                metadata['fps'] = float(numerator) / float(denominator) if float(denominator) != 0 else 0
            except (ValueError, ZeroDivisionError):
                metadata['fps'] = 0
            metadata['video_codec'] = video_stream.get('codec_name', 'unknown')
            metadata['bitrate'] = int(video_stream.get('bit_rate', 0))
        
        # Audio metadata
        if audio_stream:
            metadata['audio_codec'] = audio_stream.get('codec_name', 'unknown')
            metadata['audio_channels'] = int(audio_stream.get('channels', 0))
            metadata['audio_sample_rate'] = int(audio_stream.get('sample_rate', 0))
        
        # Duration from format
        format_info = data.get('format', {})
        if 'duration' in format_info:
            metadata['duration'] = float(format_info['duration'])
        
        return metadata
        
    except subprocess.TimeoutExpired:
        raise Exception("ffprobe timed out - video processing took too long")
    except FileNotFoundError:
        raise Exception("ffprobe not found - FFmpeg is not installed in the container")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON output from ffprobe")
    except Exception as e:
        raise Exception(f"Error extracting metadata: {str(e)}")

#@login_required
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
                        
                        # Set initial status
                        file_source.status = 'uploading'
                        file_source.processing_started_at = timezone.now()
                        
                        # Save the file source
                        file_source.save()
                        
                        # Schedule processing after DB commit to avoid visibility issues in new thread
                        def _start_processing():
                            try:
                                thread = threading.Thread(target=process_video_async, args=(file_source.source_id,))
                                thread.daemon = True
                                thread.start()
                            except Exception as start_err:
                                print(f"Thread start failed, processing synchronously: {start_err}")
                                try:
                                    process_video_async(file_source.source_id)
                                except Exception as sync_err:
                                    print(f"Synchronous processing failed: {sync_err}")

                        transaction.on_commit(_start_processing)
                        
                        messages.success(request, f'File source "{file_source.name}" created successfully. Processing video metadata...')
                        return redirect('source_management:file_detail', source_id=file_source.source_id)
                    
                    else:
                        # For camera and stream sources
                        source.save()
                        messages.success(request, f'{source_type.title()} source "{source.name}" created successfully.')
                        return redirect('source_management:' + source_type + '_detail', source_id=source.source_id)
                        
            except Exception as e:
                # If anything fails, the transaction will be rolled back
                messages.error(request, f'Error creating {source_type} source: {str(e)}')
                return redirect('source_management:source_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # GET request - show form
        source_type = request.GET.get('type', 'file')
        if source_type == 'file':
            form = FileSourceForm()
        elif source_type == 'camera':
            form = CameraSourceForm()
        elif source_type == 'stream':
            form = StreamSourceForm()
        else:
            form = FileSourceForm()
    
    context = {
        'form': form,
        'source_type': source_type,
    }
    # Provide chunking config to template for file uploads
    try:
        if source_type == 'file':
            context['chunk_threshold'] = getattr(settings, 'CHUNKED_UPLOAD_THRESHOLD', 100 * 1024 * 1024)
            context['chunk_size'] = getattr(settings, 'CHUNK_SIZE', 1024 * 1024)
    except Exception:
        pass
    return render(request, 'source_management/source_form.html', context)

#@login_required
@login_required_source_list
def source_detail(request, source_id):
    """View source details"""
    # Try to find the source in any of the models
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
    
    return render(request, 'source_management/source_detail.html', context)

#@login_required
@login_required_source_list
def source_update(request, source_id):
    """Update source details"""
    # Try to find the source in any of the models
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
            messages.success(request, f'{source_type.title()} source "{source.name}" updated successfully.')
            return redirect('source_management:' + source_type + '_detail', source_id=source.source_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = form_class(instance=source)
    
    context = {
        'form': form,
        'source': source,
        'source_type': source_type,
    }
    return render(request, 'source_management/source_form.html', context)

#@login_required
@login_required_source_list
def source_delete(request, source_id):
    """Delete a source"""
    # Try to find the source in any of the models
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
                # Delete the source
                source_name = source.name
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

#@login_required
@login_required_source_list
def api_source_metadata(request, source_id):
    """API endpoint to get source metadata"""
    try:
        # Try to find the source in any of the models
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
            return JsonResponse({'error': 'Source not found'}, status=404)
        
        # Return metadata
        metadata = {
            'id': str(source.source_id),
            'name': source.name,
            'type': source_type,
            'description': source.description,
            'location': source.location,
            'created_at': source.created_at.isoformat(),
            'updated_at': source.updated_at.isoformat(),
        }
        
        # Add type-specific metadata
        if source_type == 'file':
            metadata.update({
                'status': source.status,
                'file_size': source.file_size,
                'duration': source.duration,
                'resolution': f"{source.width}x{source.height}" if source.width and source.height else None,
                'fps': source.fps,
                'codec': source.codec,
                'access_token': source.access_token,
                'api_endpoint': source.api_endpoint,
                'stream_url': source.stream_url,
                'thumbnail_url': source.thumbnail_url,
            })
        elif source_type == 'camera':
            metadata.update({
                'camera_ip': source.camera_ip,
                'camera_port': source.camera_port,
                'camera_protocol': source.camera_protocol,
                'is_active': source.is_active,
            })
        elif source_type == 'stream':
            metadata.update({
                'stream_url': source.stream_url,
                'stream_protocol': source.stream_protocol,
                'stream_quality': source.stream_quality,
            })
        
        return JsonResponse(metadata)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# New API endpoints for video access
@login_required_source_list
def api_video_access(request, access_token):
    """API endpoint for video access using access token"""
    try:
        # Find file source by access token
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({
                'error': 'Video not ready',
                'status': file_source.status
            }, status=400)
        
        # Return video information
        response_data = {
            'id': str(file_source.source_id),
            'name': file_source.name,
            'description': file_source.description,
            'status': file_source.status,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'resolution': f"{file_source.width}x{file_source.height}" if file_source.width and file_source.height else None,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'bitrate': file_source.bitrate,
            'created_at': file_source.created_at.isoformat(),
            'download_url': f"/source-management/api/video/{access_token}/download/",
            'stream_url': f"/source-management/api/video/{access_token}/stream/",
            'thumbnail_url': f"/source-management/api/video/{access_token}/thumbnail/",
        }
        
        return JsonResponse(response_data)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required_source_list
def api_video_metadata(request, access_token):
    """API endpoint for video metadata"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        metadata = {
            'id': str(file_source.source_id),
            'name': file_source.name,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'width': file_source.width,
            'height': file_source.height,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'audio_channels': file_source.audio_channels,
            'audio_sample_rate': file_source.audio_sample_rate,
            'bitrate': file_source.bitrate,
            'file_format': file_source.file_format,
            'status': file_source.status,
        }
        
        return JsonResponse(metadata)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required_source_list
def api_video_download(request, access_token):
    """API endpoint for video download"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        # Stream the file
        response = StreamingHttpResponse(
            video_file.open('rb'),
            content_type='video/mp4'
        )
        response['Content-Disposition'] = f'attachment; filename="{video_file.name}"'
        response['Content-Length'] = video_file.size
        
        return response
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required_source_list
def api_video_stream(request, access_token):
    """API endpoint for video streaming"""
    try:
        file_source = FileSource.objects.get(access_token=access_token)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        # Get file path
        file_path = video_file.path
        
        # Check if file exists
        if not os.path.exists(file_path):
            return JsonResponse({'error': 'Video file not found on disk'}, status=404)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Handle range requests for streaming
        range_header = request.META.get('HTTP_RANGE', '').strip()
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            if start >= file_size:
                return HttpResponse(status=416)
            
            # Read the requested range
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)
            
            response = HttpResponse(data, content_type='video/mp4')
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = len(data)
            response.status_code = 206
            
            return response
        else:
            # Return full file
            response = StreamingHttpResponse(
                open(file_path, 'rb'),
                content_type='video/mp4'
            )
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = file_size
            
            return response
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Video Processing Views
@login_required_source_list
def submit_video_processing(request, source_id):
    """Submit a video for processing to external service"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the file source
        file_source = FileSource.objects.get(source_id=source_id)
        
        if file_source.status != 'ready':
            return JsonResponse({
                'error': 'Video not ready for processing',
                'status': file_source.status
            }, status=400)
        
        # Get processing parameters from request
        target_fps = request.POST.get('target_fps')
        target_resolution = request.POST.get('target_resolution')
        
        if not target_fps or not target_resolution:
            return JsonResponse({
                'error': 'Missing required parameters: target_fps and target_resolution'
            }, status=400)
        
        try:
            target_fps = int(target_fps)
            # Align with FastPublisher limit (1-5)
            if not (1 <= target_fps <= 5):
                return JsonResponse({
                    'error': 'target_fps must be between 1 and 5'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'error': 'target_fps must be a valid integer'
            }, status=400)
        
        # Validate resolution format (e.g., "640x480")
        if not re.match(r'^\d+x\d+$', target_resolution):
            return JsonResponse({
                'error': 'target_resolution must be in format "widthxheight" (e.g., "640x480")'
            }, status=400)
        
        # Import and use the processing service
        from .services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        # Submit the job
        result = processing_service.submit_video_processing(
            file_source, target_fps, target_resolution
        )
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': 'Video processing job submitted successfully',
                'job_id': result['job_id'],
                'external_job_id': result.get('external_job_id'),
                'estimated_completion_time': 'Calculating...',
                'processing_started_at': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error'],
                'details': result.get('details', '')
            }, status=500)
            
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

@login_required_source_list
def get_processing_status(request, job_id):
    """Get the status of a processing job"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        result = processing_service.get_job_status(job_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'job_id': result['job_id'],
                'external_job_id': result['external_job_id'],
                'current_status': result['status'],
                'external_status': result['external_status'],
                'response': result['response']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error']
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

@login_required_source_list
def cancel_processing_job(request, job_id):
    """Cancel a processing job"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        result = processing_service.cancel_job(job_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

def processing_callback(request, access_token):
    """Callback endpoint for external processing service"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Find the processing job by access token
        from .models import VideoProcessingJob
        processing_job = VideoProcessingJob.objects.get(access_token=access_token)
        
        # Parse the callback data
        callback_data = json.loads(request.body)
        
        # Update job status based on callback
        new_status = callback_data.get('status', 'unknown')
        if new_status in ['completed', 'failed']:
            processing_job.update_status(
                new_status,
                external_response=callback_data,
                processed_video_url=callback_data.get('processed_video_url', ''),
                processing_metadata=callback_data.get('processing_metadata', {})
            )
        
        # Log the callback
        logger.info(f"Received callback for job {processing_job.job_id}: {new_status}")
        
        return JsonResponse({'status': 'success', 'message': 'Callback processed'})
        
    except VideoProcessingJob.DoesNotExist:
        return JsonResponse({'error': 'Invalid access token'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in callback'}, status=400)
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required_source_list
def list_processing_jobs(request, source_id):
    """List all processing jobs for a specific source"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the file source
        file_source = FileSource.objects.get(source_id=source_id)
        
        # Get all processing jobs for this source
        from .models import VideoProcessingJob
        jobs = VideoProcessingJob.objects.filter(source=file_source).order_by('-submitted_at')
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'job_id': job.job_id,
                'external_job_id': job.external_job_id,
                'status': job.status,
                'target_fps': job.target_fps,
                'target_resolution': job.target_resolution,
                'submitted_at': job.submitted_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message,
                'processed_video_url': job.processed_video_url,
            })
        
        return JsonResponse({
            'status': 'success',
            'source_id': str(source_id),
            'source_name': file_source.name,
            'jobs': jobs_data,
            'total_jobs': len(jobs_data)
        })
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

def fastpublisher_status_check(request, source_id):
    """Simple status endpoint for FastPublisher to check job status"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the file source
        file_source = FileSource.objects.get(source_id=source_id)
        
        # Get the most recent processing job for this source
        from .models import VideoProcessingJob
        latest_job = VideoProcessingJob.objects.filter(source=file_source).order_by('-submitted_at').first()
        
        if not latest_job:
            return JsonResponse({
                'status': 'not_found',
                'message': 'No processing jobs found for this source'
            }, status=404)
        
        # Return simple status for FastPublisher
        return JsonResponse({
            'source_id': str(source_id),
            'job_id': latest_job.job_id,
            'status': latest_job.status,
            'message': latest_job.error_message if latest_job.error_message else 'Job is processing normally',
            'processed_video_url': latest_job.processed_video_url if latest_job.processed_video_url else None
        })
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'error': 'Internal server error',
            'message': str(e)
        }, status=500)

def fastpublisher_video_access(request, source_id):
    """Unauthenticated video access endpoint for FastPublisher"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the file source by source_id (not access_token)
        file_source = FileSource.objects.get(source_id=source_id)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        video_file = file_source.video_file
        if not video_file:
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        # Get file path
        file_path = video_file.path
        
        # Check if file exists
        if not os.path.exists(file_path):
            return JsonResponse({'error': 'Video file not found on disk'}, status=404)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Handle range requests for streaming
        range_header = request.META.get('HTTP_RANGE', '').strip()
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            if start >= file_size:
                return HttpResponse(status=416)
            
            # Read the requested range
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)
            
            response = HttpResponse(data, content_type='video/mp4')
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = len(data)
            response.status_code = 206
            
            return response
        else:
            # Return full file
            response = StreamingHttpResponse(
                open(file_path, 'rb'),
                content_type='video/mp4'
            )
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = file_size
            
            return response
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fastpublisher_submit_video(request, source_id):
    """Unauthenticated video submission endpoint for FastPublisher"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the file source
        file_source = FileSource.objects.get(source_id=source_id)
        
        if file_source.status != 'ready':
            return JsonResponse({
                'error': 'Video not ready for processing',
                'status': file_source.status
            }, status=400)
        
        # Get processing parameters from request
        target_fps = request.POST.get('target_fps')
        target_resolution = request.POST.get('target_resolution')
        
        if not target_fps or not target_resolution:
            return JsonResponse({
                'error': 'Missing required parameters: target_fps and target_resolution'
            }, status=400)
        
        try:
            target_fps = int(target_fps)
            # Align with FastPublisher limit (1-5)
            if not (1 <= target_fps <= 5):
                return JsonResponse({
                    'error': 'target_fps must be between 1 and 5'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'error': 'target_fps must be a valid integer'
            }, status=400)
        
        # Validate resolution format (e.g., "640x480")
        if not re.match(r'^\d+x\d+$', target_resolution):
            return JsonResponse({
                'error': 'target_resolution must be in format "widthxheight" (e.g., "640x480")'
            }, status=400)
        
        # Import and use the processing service
        from .services import VideoProcessingService
        processing_service = VideoProcessingService()
        
        # Submit the job and include health status for debugging
        service_health = processing_service.health()
        result = processing_service.submit_video_processing(
            file_source, target_fps, target_resolution
        )
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': 'Video processing job submitted successfully',
                'job_id': result['job_id'],
                'external_job_id': result.get('external_job_id'),
                'estimated_completion_time': 'Calculating...',
                'processing_started_at': timezone.now().isoformat(),
                'external_service_url': result.get('external_service_url'),
                'external_service_health': service_health
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['error'],
                'details': result.get('details', ''),
                'external_service_url': result.get('external_service_url'),
                'external_service_health': service_health
            }, status=500)
            
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

def fastpublisher_video_metadata(request, source_id):
    """Unauthenticated video metadata endpoint for FastPublisher"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        file_source = FileSource.objects.get(source_id=source_id)
        
        if file_source.status != 'ready':
            return JsonResponse({'error': 'Video not ready'}, status=400)
        
        metadata = {
            'source_id': str(file_source.source_id),
            'name': file_source.name,
            'file_size': file_source.file_size,
            'duration': file_source.duration,
            'width': file_source.width,
            'height': file_source.height,
            'fps': file_source.fps,
            'codec': file_source.codec,
            'audio_codec': file_source.audio_codec,
            'audio_channels': file_source.audio_channels,
            'audio_sample_rate': file_source.audio_sample_rate,
            'bitrate': file_source.bitrate,
            'file_format': file_source.file_format,
            'status': file_source.status,
            'stream_url': f"/source-management/api/fastpublisher-video/{source_id}/",
            'access_token': file_source.access_token,
        }
        
        return JsonResponse(metadata)
        
    except FileSource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fastpublisher_health(request):
    """Proxy health check for FastPublisher so frontend avoids CORS."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        from .services import VideoProcessingService
        service = VideoProcessingService()
        health = service.health()
        return JsonResponse({
            'ok': health.get('ok', False),
            'url': health.get('url'),
            'status_code': health.get('status_code'),
            'error': health.get('error'),
            'response': health.get('response')
        }, status=200 if health.get('ok') else 503)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
