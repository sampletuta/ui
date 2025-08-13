from django.shortcuts import render, redirect, get_object_or_404
from .forms import TargetsWatchlistForm, LoginForm, CustomUserCreationForm, CustomUserChangeForm, CustomPasswordChangeForm, AdvancedSearchForm, QuickSearchForm, MilvusSearchForm, CaseForm
from .models import TargetPhoto, Targets_watchlist, Case, SearchHistory, SearchQuery, SearchResult, CustomUser
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
import os
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from datetime import datetime, timedelta
import json
import folium
from math import radians, cos, sin, asin, sqrt
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
import logging
from notifications.signals import notify
from notifications.models import Notification

logger = logging.getLogger(__name__)

def login(request):
    logger.info("Login view called")
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        logger.info("POST request received")
        form = LoginForm(request.POST)
        logger.info(f"Form is valid: {form.is_valid()}")
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            logger.info(f"Attempting authentication for email: {email}")
            user = authenticate(request, username=email, password=password)
            logger.info(f"Authentication result: {user}")
            if user is not None:
                auth_login(request, user)
                logger.info(f"User logged in successfully: {user.email}")
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                logger.info("Redirecting to dashboard...")
                response = redirect('dashboard') #dashboard home page
                logger.info(f"Redirect response: {response}")
                return response
            else:
                logger.warning(f"Authentication failed for email: {email}")
                messages.error(request, 'Invalid email or password')
        else:
            logger.error(f"Form errors: {form.errors}")
    else:
        form = LoginForm()
    return render(request, 'signin.html', {'form': form})

@login_required
def dashboard(request):
    total_targets = Targets_watchlist.objects.count()
    total_cases = Case.objects.count()
    total_images = TargetPhoto.objects.count()
    recent_targets = Targets_watchlist.objects.select_related('case').order_by('-created_at')[:5]
    # Status distribution for chart
    status_counts = list(Targets_watchlist.objects.values('case_status').annotate(count=Count('id')))
    gender_counts = list(Targets_watchlist.objects.values('gender').annotate(count=Count('id')))
    
    # Notifications removed - no longer using django-notifications-hq
    
    return render(request, 'dashboard.html', {
        'total_targets': total_targets,
        'total_cases': total_cases,
        'total_images': total_images,
        'recent_targets': recent_targets,
        'status_counts': status_counts,
        'gender_counts': gender_counts,
    })

@login_required
def backend(request):
    if request.method == 'POST':
        form = TargetsWatchlistForm(request.POST, request.FILES)
        if form.is_valid():
            watchlist = form.save(commit=False)
            watchlist.created_by = request.user
            watchlist.save()
            try:
                notify.send(request.user, recipient=watchlist.created_by, verb='added target', target=watchlist)
            except Exception:
                pass
            
            # Handle multiple image uploads using validated files from the form
            images = form.cleaned_data.get('images') or []
            uploaded_count = 0
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        TargetPhoto.objects.create(person=watchlist, image=image, uploaded_by=request.user)
                        uploaded_count += 1
                        try:
                            notify.send(request.user, recipient=watchlist.created_by, verb='uploaded images', target=watchlist, action_object=watchlist)
                        except Exception:
                            pass
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, 'Target added successfully with images!')
            else:
                messages.warning(request, 'Target added, but no images were uploaded.')
            return redirect('list_watchlist')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TargetsWatchlistForm()
    return render(request, 'add_watchlist.html', {'form': form})

@login_required
def list_watchlist(request):
    watchlists = Targets_watchlist.objects.select_related('case', 'created_by').prefetch_related('images').all()
    
    # Handle search functionality
    search_query = request.GET.get('q')
    if search_query:
        watchlists = watchlists.filter(
            Q(target_name__icontains=search_query) |
            Q(target_text__icontains=search_query) |
            Q(target_email__icontains=search_query) |
            Q(target_phone__icontains=search_query) |
            Q(case__case_name__icontains=search_query)
        )
    
    return render(request, 'list_watchlist.html', {
        'watchlists': watchlists,
        'search_query': search_query
    })

@login_required
def target_profile(request, pk):
    target = get_object_or_404(Targets_watchlist.objects.select_related('case', 'created_by').prefetch_related('images'), pk=pk)
    return render(request, 'target_profile.html', {'target': target})

@login_required
def edit_target(request, pk):
    target = get_object_or_404(Targets_watchlist, pk=pk)
    if request.method == 'POST':
        # Include request.FILES so optional image uploads are handled correctly
        form = TargetsWatchlistForm(request.POST, request.FILES, instance=target)
        if form.is_valid():
            form.save()
            # Optionally process new images added during edit
            images = form.cleaned_data.get('images') or []
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        TargetPhoto.objects.create(person=target, image=image, uploaded_by=request.user)
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')
            messages.success(request, 'Target updated successfully!')
            return redirect('target_profile', pk=pk)
    else:
        form = TargetsWatchlistForm(instance=target)
    return render(request, 'edit_target.html', {'form': form, 'target': target})

@login_required
def delete_target(request, pk):
    target = get_object_or_404(Targets_watchlist, pk=pk)
    if request.method == 'POST':
        try:
            notify.send(request.user, recipient=target.created_by or request.user, verb='deleted target', target=target)
        except Exception:
            pass
        target.delete()
        messages.success(request, 'Target deleted successfully!')
        return redirect('list_watchlist')
    return render(request, 'delete_target.html', {'target': target})

@login_required
def add_images(request, pk):
    target = get_object_or_404(Targets_watchlist, pk=pk)
    if request.method == 'POST':
        images = request.FILES.getlist('images')
        if images:
            uploaded_count = 0
            for image in images:
                if image.name:  # Only process files with names
                    try:
                        TargetPhoto.objects.create(person=target, image=image, uploaded_by=request.user)
                        uploaded_count += 1
                        try:
                            notify.send(request.user, recipient=target.created_by or request.user, verb='uploaded images', target=target)
                        except Exception:
                            pass
                    except Exception as e:
                        messages.error(request, f'Failed to upload {image.name}: {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, f'{uploaded_count} image(s) uploaded successfully!')
            else:
                messages.error(request, 'No valid images were uploaded.')
        else:
            messages.error(request, 'Please select at least one image to upload.')
        return redirect('target_profile', pk=pk)
    return render(request, 'add_images.html', {'target': target})

@login_required
def delete_image(request, pk, image_id):
    target = get_object_or_404(Targets_watchlist, pk=pk)
    image = get_object_or_404(TargetPhoto, pk=image_id, person=target)
    if request.method == 'POST':
        try:
            notify.send(request.user, recipient=target.created_by or request.user, verb='deleted image', target=target, action_object=image)
        except Exception:
            pass
        image.delete()
        messages.success(request, 'Image deleted successfully!')
        return redirect('target_profile', pk=pk)
    return render(request, 'delete_image.html', {'target': target, 'image': image})

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user and redirect back."""
    try:
        request.user.notifications.unread().mark_all_as_read()
    except Exception:
        try:
            Notification.objects.filter(recipient=request.user, unread=True).update(unread=False)
        except Exception:
            pass
    next_url = request.META.get('HTTP_REFERER') or '/inbox/notifications/'
    return redirect(next_url)

@login_required
def notifications_list(request):
    """List notifications for the current user."""
    notifications_qs = Notification.objects.filter(recipient=request.user).select_related('actor_content_type', 'target_content_type', 'action_object_content_type').order_by('-timestamp')
    return render(request, 'notifications_list.html', {
        'notifications': notifications_qs,
    })

@login_required
def notification_detail(request, notification_id):
    """Detail page for a single notification; marks as read and shows metadata."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if notification.unread:
        try:
            notification.mark_as_read()
        except Exception:
            pass
    return render(request, 'notification_detail.html', {
        'notification': notification,
    })

# Advanced Search Views
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
    """Milvus vector search interface"""
    if request.method == 'POST':
        form = MilvusSearchForm(request.POST)
        if form.is_valid():
            collection_name = form.cleaned_data['collection_name']
            partition_name = form.cleaned_data['partition_name']
            top_k = form.cleaned_data['top_k']
            distance_threshold = form.cleaned_data['distance_threshold']
            
            # Execute Milvus search
            results = execute_milvus_search(collection_name, partition_name, top_k, distance_threshold)
            
            return render(request, 'milvus_search_results.html', {
                'results': results,
                'collection_name': collection_name,
                'top_k': top_k
            })
    else:
        form = MilvusSearchForm()
    
    return render(request, 'milvus_search.html', {'form': form})

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

# Folium Map Functions
def create_search_map():
    """Create a Folium map for search interface"""
    # Default to a central location (e.g., NYC)
    center_lat, center_lng = 40.7128, -74.0060
    
    map_obj = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add a marker for the center point
    folium.Marker(
        [center_lat, center_lng],
        popup='Search Center',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(map_obj)
    
    return map_obj

def create_results_map(results, search_query):
    """Create a Folium map showing search results"""
    if not results:
        return create_search_map()
    
    # Calculate center point from results or use search query center
    if search_query.latitude and search_query.longitude:
        center_lat, center_lng = search_query.latitude, search_query.longitude
    else:
        # Calculate center from results
        lats = [r.latitude for r in results if r.latitude]
        lngs = [r.longitude for r in results if r.longitude]
        if lats and lngs:
            center_lat, center_lng = sum(lats)/len(lats), sum(lngs)/len(lngs)
        else:
            center_lat, center_lng = 40.7128, -74.0060
    
    map_obj = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Add search radius circle if specified
    if search_query.latitude and search_query.longitude and search_query.radius_km:
        folium.Circle(
            radius=search_query.radius_km * 1000,  # Convert km to meters
            location=[search_query.latitude, search_query.longitude],
            popup=f'Search Radius: {search_query.radius_km}km',
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.2
        ).add_to(map_obj)
    
    # Add markers for each result
    for result in results:
        if result.latitude and result.longitude:
            folium.Marker(
                [result.latitude, result.longitude],
                popup=f"""
                <b>{result.target.target_name}</b><br>
                Confidence: {result.confidence:.2f}<br>
                Time: {result.timestamp}s<br>
                Camera: {result.camera_name or 'Unknown'}
                """,
                icon=folium.Icon(color='blue', icon='user')
            ).add_to(map_obj)
    
    return map_obj

# Geospatial utility functions
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

# Search Execution Functions
def execute_advanced_search(search_query):
    """Execute advanced search with all filters"""
    # This would integrate with your face detection service
    # For now, return mock results
    
    # Apply geospatial filter
    if search_query.latitude and search_query.longitude:
        # Filter by radius using haversine distance
        pass
    
    # Apply date filter
    if search_query.start_date or search_query.end_date:
        # Filter by date range
        pass
    
    # Apply confidence threshold
    # Filter by confidence
    
    # Apply target filters
    if search_query.target_filters:
        # Filter by selected targets
        pass
    
    # This would call your external face detection service
    # and return results in the SearchResult format
    
    return []

def execute_quick_search(search_type, query_text, confidence, start_date, end_date):
    """Execute quick search"""
    # Simple search implementation
    # This would integrate with your face detection service
    
    return []

def execute_milvus_search(collection_name, partition_name, top_k, distance_threshold):
    """Execute Milvus vector search"""
    # This would integrate with Milvus
    # For now, return mock results
    
    return []

# Legacy views for backward compatibility
@login_required
def milvus_search_legacy(request):
    # Placeholder: In a real implementation, connect to Milvus and perform search
    requirements_met = False  # Change to True when Milvus integration is ready
    context = {
        'requirements_met': requirements_met,
    }
    return render(request, 'milvus_search.html', context)

@login_required
def video_face_search(request):
    from .models import Targets_watchlist
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
    return render(request, 'video_face_search.html', {'target_lists': target_lists, 'recent_searches': recent_searches})

@login_required
def start_video_face_search(request):
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
            return JsonResponse({'success': True, 'upload_id': upload_id, 'file_url': file_url, 'complete': True})

        return JsonResponse({'success': True, 'upload_id': upload_id, 'complete': False})

    except Exception as e:
        logger.exception('upload_chunk error')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def search_results(request, search_id):
    from .models import SearchHistory, SearchResult
    search = SearchHistory.objects.select_related('target_list').get(id=search_id, user=request.user)
    results = SearchResult.objects.filter(search=search).select_related('target')
    return render(request, 'search_results.html', {'search': search, 'results': results})

@login_required
def profile(request):
    """User profile view"""
    return render(request, 'profile.html', {'user': request.user})

@login_required
def settings_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('settings')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'settings.html', {'form': form})

## Removed duplicate 'settings' view to avoid shadowing django.conf.settings

def signup(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password1'])
                    user.save()
                    
                    messages.success(request, 'Account created successfully! You can now login.')
                    return redirect('login')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Create Account',
        'submit_text': 'Create Account',
    }
    return render(request, 'signup.html', context)

@login_required
def logout_view(request):
    auth_logout(request)
    return redirect('login')

def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.role == 'admin'

def is_staff_or_admin(user):
    """Check if user is staff or admin"""
    return user.is_authenticated and (user.is_staff or user.role == 'admin')

def handle_failed_login(user):
    """Handle failed login attempt"""
    user.login_attempts += 1
    user.last_failed_login = timezone.now()
    
    # Lock account after 3 failed attempts
    if user.login_attempts >= 3:
        user.is_active = False
        user.locked_until = timezone.now() + timedelta(minutes=30)  # Lock for 30 minutes
        messages.error(request, 'Account locked due to multiple failed login attempts. Please try again in 30 minutes.')
    else:
        remaining_attempts = 3 - user.login_attempts
        messages.error(request, f'Invalid credentials. {remaining_attempts} attempts remaining.')
    
    user.save()

def handle_successful_login(user):
    """Handle successful login"""
    user.login_attempts = 0
    user.last_failed_login = None
    user.locked_until = None
    user.save()

def custom_login(request):
    """Custom login view with security features"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                user = CustomUser.objects.get(email=email)
                
                # Check if account is locked
                if not user.is_active:
                    if user.locked_until and user.locked_until > timezone.now():
                        remaining_time = user.locked_until - timezone.now()
                        minutes = int(remaining_time.total_seconds() / 60)
                        messages.error(request, f'Account is locked. Please try again in {minutes} minutes.')
                    else:
                        # Unlock account if lock time has expired
                        user.is_active = True
                        user.login_attempts = 0
                        user.save()
                        messages.success(request, 'Account unlocked. You can now login.')
                    return render(request, 'signin.html', {'form': form})
                
                # Authenticate user
                user = authenticate(request, username=email, password=password)
                
                if user is not None:
                    handle_successful_login(user)
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name or user.email}!')
                    
                    # Redirect to next page or dashboard
                    next_url = request.GET.get('next', 'dashboard')
                    return redirect(next_url)
                else:
                    handle_failed_login(user)
                    
            except CustomUser.DoesNotExist:
                messages.error(request, 'Invalid email or password.')
            
    else:
        form = LoginForm()
    
    return render(request, 'signin.html', {'form': form})

def logout(request):
    """Custom logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

@login_required
def user_list(request):
    """List all users (admin only)"""
    if not is_staff_or_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    users = CustomUser.objects.all().order_by('-date_joined')
    
    context = {
        'users': users,
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
        'locked_users': users.filter(is_active=False).count(),
    }
    return render(request, 'user_list.html', context)

@login_required
def user_create(request):
    """Create new user (admin only)"""
    if not is_staff_or_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password1'])
                    user.save()
                    
                    messages.success(request, f'User "{user.email}" created successfully.')
                    return redirect('user_list')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Create New User',
        'submit_text': 'Create User',
    }
    return render(request, 'user_form.html', context)

@login_required
def user_update(request, user_id):
    """Update user (admin only)"""
    if not is_staff_or_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(request, f'User "{user.email}" updated successfully.')
                    return redirect('user_list')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserChangeForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'title': f'Edit User: {user.email}',
        'submit_text': 'Update User',
    }
    return render(request, 'user_form.html', context)

@login_required
def user_delete(request, user_id):
    """Delete user (admin only)"""
    if not is_staff_or_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.user.id == user.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user_email = user.email
                user.delete()
                messages.success(request, f'User "{user_email}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
        
        return redirect('user_list')
    
    context = {
        'user': user,
        'title': f'Delete User: {user.email}',
    }
    return render(request, 'user_confirm_delete.html', context)

@login_required
def user_unlock(request, user_id):
    """Unlock user account (admin only)"""
    if not is_staff_or_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user.is_active = True
                user.login_attempts = 0
                user.last_failed_login = None
                user.locked_until = None
                user.save()
                
                messages.success(request, f'User "{user.email}" unlocked successfully.')
        except Exception as e:
            messages.error(request, f'Error unlocking user: {str(e)}')
        
        return redirect('user_list')
    
    context = {
        'user': user,
        'title': f'Unlock User: {user.email}',
    }
    return render(request, 'user_confirm_unlock.html', context)

@login_required
def user_profile(request):
    """User profile page"""
    user = request.user
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(request, 'Profile updated successfully.')
                    return redirect('user_profile')
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserChangeForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'title': 'My Profile',
        'submit_text': 'Update Profile',
    }
    return render(request, 'user_profile.html', context)

# API endpoint for user management
@login_required
def api_user_status(request, user_id):
    """API endpoint to get user status"""
    if not is_staff_or_admin(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        user = CustomUser.objects.get(id=user_id)
        data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'login_attempts': user.login_attempts,
            'last_failed_login': user.last_failed_login.isoformat() if user.last_failed_login else None,
            'locked_until': user.locked_until.isoformat() if user.locked_until else None,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat(),
        }
        return JsonResponse(data)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Case Management Views
@login_required
def case_list(request):
    """List all cases"""
    cases = Case.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'case_list.html', {'cases': cases})

@login_required
def case_create(request):
    """Create a new case"""
    if request.method == 'POST':
        form = CaseForm(request.POST)
        if form.is_valid():
            case = form.save(commit=False)
            case.created_by = request.user
            case.save()
            messages.success(request, f'Case "{case.case_name}" created successfully!')
            try:
                notify.send(request.user, recipient=request.user, verb='created case', target=case)
            except Exception:
                pass
            return redirect('case_detail', pk=case.pk)
    else:
        form = CaseForm()
    
    return render(request, 'case_form.html', {'form': form, 'title': 'Create New Case'})

@login_required
def case_detail(request, pk):
    """View case details and its targets"""
    case = get_object_or_404(Case, pk=pk, created_by=request.user)
    targets = case.targets_watchlist.all().order_by('-created_at')
    return render(request, 'case_detail.html', {'case': case, 'targets': targets})

@login_required
def case_edit(request, pk):
    """Edit an existing case"""
    case = get_object_or_404(Case, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = CaseForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            messages.success(request, f'Case "{case.case_name}" updated successfully!')
            try:
                notify.send(request.user, recipient=request.user, verb='updated case', target=case)
            except Exception:
                pass
            return redirect('case_detail', pk=case.pk)
    else:
        form = CaseForm(instance=case)
    
    return render(request, 'case_form.html', {'form': form, 'title': f'Edit Case: {case.case_name}'})

@login_required
def case_delete(request, pk):
    """Delete a case"""
    case = get_object_or_404(Case, pk=pk, created_by=request.user)
    if request.method == 'POST':
        case_name = case.case_name
        try:
            notify.send(request.user, recipient=case.created_by, verb='deleted case', target=case, description=f'Case "{case_name}" deleted')
        except Exception:
            pass
        case.delete()
        messages.success(request, f'Case "{case_name}" deleted successfully!')
        return redirect('case_list')
    
    return render(request, 'case_confirm_delete.html', {'case': case})

@login_required
def add_target_to_case(request, case_pk):
    """Add a target to a specific case"""
    case = get_object_or_404(Case, pk=case_pk, created_by=request.user)
    
    if request.method == 'POST':
        form = TargetsWatchlistForm(request.POST, request.FILES)
        if form.is_valid():
            target = form.save(commit=False)
            target.case = case
            target.created_by = request.user
            target.save()
            try:
                notify.send(request.user, recipient=case.created_by, verb='added target', target=target, action_object=case)
            except Exception:
                pass
            
            # Handle multiple image uploads using validated files from the form
            images = form.cleaned_data.get('images') or []
            uploaded_count = 0
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        TargetPhoto.objects.create(person=target, image=image, uploaded_by=request.user)
                        uploaded_count += 1
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, f'Target "{target.target_name}" added to case "{case.case_name}" successfully with images!')
            else:
                messages.warning(request, f'Target "{target.target_name}" added to case "{case.case_name}", but no images were uploaded.')
            return redirect('case_detail', pk=case.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TargetsWatchlistForm(initial={'case': case})
    
    return render(request, 'add_target_to_case.html', {'form': form, 'case': case})
