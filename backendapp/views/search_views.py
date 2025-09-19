"""
Search Views Module
Handles advanced search, quick search, Milvus search, and video face search
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
import os
import logging

from ..forms import AdvancedSearchForm, QuickSearchForm, MilvusSearchForm
from ..models import (
    SearchHistory, SearchQuery, SearchResult, Targets_watchlist, TargetPhoto, Case
)
from .utils import (
    create_search_map, create_results_map, execute_advanced_search,
    execute_quick_search
)

logger = logging.getLogger(__name__)

@login_required
def advanced_search(request):
    """Advanced search with geospatial, date filtering, and Milvus integration"""
    if request.method == 'POST':
        form = AdvancedSearchForm(request.POST)
        if form.is_valid():
            search_query = form.save(commit=False)
            search_query.user = request.user
            
            # Handle target filters
            targets = form.cleaned_data.get('targets')
            if targets:
                search_query.target_filters = {
                    'target_ids': list(targets.values_list('id', flat=True)),
                    'gender': form.cleaned_data.get('gender_filter'),
                    'case_id': form.cleaned_data.get('case_filter').id if form.cleaned_data.get('case_filter') else None
                }
            
            search_query.save()
            
            # Execute search (this would integrate with your face detection service)
            results = execute_advanced_search(search_query)
            
            messages.success(request, f'Search "{search_query.query_name}" created successfully!')
            return redirect('search_results_advanced', search_id=search_query.id)
    else:
        form = AdvancedSearchForm()
    
    # Create Folium map for geospatial visualization
    map_obj = create_search_map()
    
    return render(request, 'advanced_search.html', {
        'form': form,
        'cases': Case.objects.all(),
        'targets': Targets_watchlist.objects.all(),
        'map': map_obj._repr_html_()
    })

@login_required
def quick_search(request):
    """Quick search interface for simple queries"""
    if request.method == 'POST':
        form = QuickSearchForm(request.POST)
        if form.is_valid():
            # Create a temporary search query for quick search
            search_type = form.cleaned_data['search_type']
            query_text = form.cleaned_data['query_text']
            confidence = form.cleaned_data['confidence_threshold']
            date_range = form.cleaned_data['date_range']
            
            # Calculate date range
            from datetime import datetime, timedelta
            now = datetime.now()
            if date_range == '1h':
                start_date = now - timedelta(hours=1)
            elif date_range == '24h':
                start_date = now - timedelta(days=1)
            elif date_range == '7d':
                start_date = now - timedelta(days=7)
            elif date_range == '30d':
                start_date = now - timedelta(days=30)
            else:
                start_date = None
            
            # Execute quick search
            results = execute_quick_search(search_type, query_text, confidence, start_date, now)
            
            return render(request, 'quick_search_results.html', {
                'results': results,
                'search_type': search_type,
                'query_text': query_text,
                'confidence': confidence
            })
    else:
        form = QuickSearchForm()
    
    return render(request, 'quick_search.html', {'form': form})

@login_required
def milvus_search(request):
    """Milvus vector search interface for face similarity search"""
    import asyncio
    
    if request.method == 'POST':
        form = MilvusSearchForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Import the new face search service
                from face_ai.services.face_search_service_v2 import FaceSearchService
                
                # Define async function to handle the search
                async def perform_search():
                    async with FaceSearchService() as face_search_service:
                        # Get form data
                        face_image = form.cleaned_data['face_image']
                        top_k = form.cleaned_data['top_k']
                        confidence_threshold = form.cleaned_data['confidence_threshold']
                        
                        # Perform face search; allow toggling re-ranking from form
                        apply_rerank = form.cleaned_data.get('apply_rerank', True)
                        search_result = await face_search_service.search_faces_in_image(
                            face_image,
                            top_k=top_k,
                            confidence_threshold=confidence_threshold,
                            apply_rerank=apply_rerank
                        )
                        
                        if search_result['success']:
                            # Get service information
                            service_info = await face_search_service.get_service_info()
                            return search_result, service_info
                        else:
                            return search_result, None
                
                # Run the async function
                search_result, service_info = asyncio.run(perform_search())
                
                if search_result['success']:
                    return render(request, 'milvus_search_results.html', {
                        'search_result': search_result,
                        'service_info': service_info,
                        'form': form,
                        'uploaded_image': form.cleaned_data['face_image']
                    })
                else:
                    messages.error(request, f'Search failed: {search_result["error"]}')
                        
            except ImportError as e:
                messages.error(request, f'Face search service not available: {e}')
            except Exception as e:
                logger.error(f"Face search error: {e}")
                messages.error(request, f'An error occurred during face search: {str(e)}')
    else:
        form = MilvusSearchForm()
    
    # Get basic service information for display
    try:
        from face_ai.services.face_search_service_v2 import FaceSearchService
        
        async def get_service_info():
            async with FaceSearchService() as face_search_service:
                return await face_search_service.get_service_info()
        
        service_info = asyncio.run(get_service_info())
    except Exception as e:
        logger.warning(f"Could not get service information: {e}")
        service_info = {'status': 'error', 'error': str(e)}
    
    return render(request, 'milvus_search.html', {
        'form': form, 
        'service_info': service_info
    })

@login_required
def search_results_advanced(request, search_id):
    """Display results for advanced search"""
    search_query = get_object_or_404(SearchQuery, id=search_id, user=request.user)
    results = SearchResult.objects.filter(search_query=search_query).select_related('target')
    
    # Create Folium map for results visualization
    map_obj = create_results_map(results, search_query)
    
    return render(request, 'search_results_advanced.html', {
        'search_query': search_query,
        'results': results,
        'map': map_obj._repr_html_()
    })

@login_required
def search_history(request):
    """View search history"""
    search_queries = SearchQuery.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'search_history.html', {
        'search_queries': search_queries
    })

@login_required
def video_face_search(request):
    """Video face search interface"""
    target_lists = Targets_watchlist.objects.all()
    recent_searches = SearchHistory.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    if request.method == 'POST':
        video_file = request.FILES.get('video_file')
        target_list_id = request.POST.get('target_list')
        if video_file and target_list_id:
            target_list = Targets_watchlist.objects.get(id=target_list_id)
            search = SearchHistory.objects.create(
                user=request.user,
                video_file=video_file,
                target_list=target_list,
                status='queued',
            )
            messages.success(request, 'Video uploaded and search started!')
            return redirect('video_face_search')
        else:
            messages.error(request, 'Please select a video and a target list.')
    
    return render(request, 'video_face_search.html', {
        'target_lists': target_lists, 
        'recent_searches': recent_searches
    })

@login_required
def start_video_face_search(request):
    """Start video face search via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    video_file = request.FILES.get('video_file')
    target_lists = request.POST.getlist('target_lists[]')
    
    if not video_file or not target_lists:
        return JsonResponse({'success': False, 'error': 'Missing video or targets'}, status=400)
    
    if 'all' in target_lists:
        target_qs = Targets_watchlist.objects.all()
    else:
        target_qs = Targets_watchlist.objects.filter(id__in=target_lists)
    
    search_ids = []
    for target in target_qs:
        search = SearchHistory.objects.create(
            user=request.user,
            video_file=video_file,
            target_list=target,
            status='queued',
        )
        search_ids.append(str(search.id))
    
    return JsonResponse({'success': True, 'search_ids': search_ids})

@login_required
def search_status(request):
    """Get search status via AJAX"""
    search_id = request.GET.get('id')
    if not search_id:
        return JsonResponse({'success': False, 'error': 'Missing id'}, status=400)
    
    try:
        search = SearchHistory.objects.get(id=search_id, user=request.user)
    except SearchHistory.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    
    # Dummy progress for now
    progress = 100 if search.status == 'completed' else (50 if search.status == 'processing' else 0)
    
    return JsonResponse({
        'success': True,
        'status': search.status,
        'created_at': search.created_at,
        'progress': progress,
        'result_summary': search.result_summary,
        'error_message': search.error_message,
    })

@login_required
@csrf_exempt
def upload_chunk(request):
    """Handle chunked file uploads"""
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

        upload_id = request.POST.get('upload_id')
        chunk_index_raw = request.POST.get('chunk_index')
        total_chunks_raw = request.POST.get('total_chunks')
        original_filename = request.POST.get('original_filename')
        chunk = request.FILES.get('chunk')

        # Validate numeric fields
        try:
            chunk_index = int(chunk_index_raw)
            total_chunks = int(total_chunks_raw)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid chunk_index or total_chunks'}, status=400)

        if not (upload_id and chunk_index >= 0 and total_chunks > 0 and chunk and original_filename):
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)

        # Save chunk
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'chunked_uploads', upload_id)
        os.makedirs(upload_dir, exist_ok=True)
        chunk_path = os.path.join(upload_dir, f'{chunk_index:05d}.part')
        
        with open(chunk_path, 'wb') as f:
            for c in chunk.chunks():
                f.write(c)

        # Check if all chunks are present
        chunk_files = sorted([f for f in os.listdir(upload_dir) if f.endswith('.part')])
        if len(chunk_files) == total_chunks:
            # Assemble chunks
            final_dir = os.path.join(settings.MEDIA_ROOT, 'search_videos')
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, f'{upload_id}_{original_filename}')
            
            with open(final_path, 'wb') as outfile:
                for i in range(total_chunks):
                    part_path = os.path.join(upload_dir, f'{i:05d}.part')
                    with open(part_path, 'rb') as infile:
                        outfile.write(infile.read())
            
            # Cleanup chunk files
            for f_name in chunk_files:
                os.remove(os.path.join(upload_dir, f_name))
            os.rmdir(upload_dir)
            
            file_url = os.path.join(settings.MEDIA_URL, 'search_videos', f'{upload_id}_{original_filename}')
            return JsonResponse({
                'success': True, 
                'upload_id': upload_id, 
                'file_url': file_url, 
                'complete': True
            })

        return JsonResponse({'success': True, 'upload_id': upload_id, 'complete': False})

    except Exception as e:
        logger.exception('upload_chunk error')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def search_results(request, search_id):
    """Display search results"""
    search = SearchHistory.objects.select_related('target_list').get(id=search_id, user=request.user)
    results = SearchResult.objects.filter(search=search).select_related('target')
    return render(request, 'search_results.html', {'search': search, 'results': results})

# Legacy views for backward compatibility
@login_required
def milvus_search_legacy(request):
    """Legacy Milvus search view"""
    # Placeholder: In a real implementation, connect to Milvus and perform search
    requirements_met = False  # Change to True when Milvus integration is ready
    context = {
        'requirements_met': requirements_met,
    }
    return render(request, 'milvus_search.html', context)
