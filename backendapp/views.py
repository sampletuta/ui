from django.shortcuts import render, redirect, get_object_or_404
from .forms import (
    TargetsWatchlistForm,
    LoginForm,
    CustomUserCreationForm,
    CustomUserChangeForm,
    CustomPasswordChangeForm,
    AdvancedSearchForm,
    QuickSearchForm,
    MilvusSearchForm,
    CaseForm,
    AdminUserCreationForm,
    AdminUserChangeForm,
    SelfUserChangeForm,
)
from .models import TargetPhoto, Targets_watchlist, Case, SearchHistory, SearchQuery, SearchResult, CustomUser
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
import os
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

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
    recent_cases = Case.objects.select_related('created_by').order_by('-created_at')[:5]

    # Monthly trend data (last 7 months including current)
    from datetime import date
    now = timezone.now().date()
    def add_months(d, months):
        year = d.year + (d.month - 1 + months) // 12
        month = (d.month - 1 + months) % 12 + 1
        day = min(d.day, 28)  # avoid end-of-month pitfalls
        return date(year, month, day)

    months_labels = []
    targets_month_counts = []
    cases_month_counts = []
    images_month_counts = []
    for i in range(6, -1, -1):  # 7 points
        mdate = add_months(now.replace(day=1), -i)
        months_labels.append(mdate.strftime('%b %Y'))
        targets_month_counts.append(
            Targets_watchlist.objects.filter(created_at__year=mdate.year, created_at__month=mdate.month).count()
        )
        cases_month_counts.append(
            Case.objects.filter(created_at__year=mdate.year, created_at__month=mdate.month).count()
        )
        images_month_counts.append(
            TargetPhoto.objects.filter(uploaded_at__year=mdate.year, uploaded_at__month=mdate.month).count()
        )

    
    # Notifications removed - no longer using django-notifications-hq
    
    return render(request, 'dashboard.html', {
        'total_targets': total_targets,
        'total_cases': total_cases,
        'total_images': total_images,
        'recent_targets': recent_targets,
        'status_counts': status_counts,
        'gender_counts': gender_counts,
        'recent_cases': recent_cases,
        'months_labels': months_labels,
        'targets_month_counts': targets_month_counts,
        'cases_month_counts': cases_month_counts,
        'images_month_counts': images_month_counts,
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
    watchlists_qs = Targets_watchlist.objects.select_related('case', 'created_by').prefetch_related('images').all()
    
    # Handle search functionality
    search_query = request.GET.get('q')
    if search_query:
        watchlists_qs = watchlists_qs.filter(
            Q(target_name__icontains=search_query) |
            Q(target_text__icontains=search_query) |
            Q(target_email__icontains=search_query) |
            Q(target_phone__icontains=search_query) |
            Q(case__case_name__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(watchlists_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'list_watchlist.html', {
        'watchlists': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
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
            target_name = target.target_name
            target_id = str(target.id)
            
            logger.info(f"Starting deletion process for target {target_name} (ID: {target_id})")
            
            # Step 1: Clean up Milvus embeddings
            try:
                from face_ai.services.milvus_api_service import MilvusAPIService
                milvus_service = MilvusAPIService()
                
                deleted_count = milvus_service.delete_embeddings_by_target_id(target_id)
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} Milvus embeddings for target {target_id}")
                else:
                    logger.info(f"No Milvus embeddings found for target {target_id}")
                    
            except ImportError:
                logger.warning("Face AI service not available for Milvus cleanup")
            except Exception as e:
                logger.warning(f"Failed to clean up Milvus embeddings for target {target_id}: {e}")
            
            # Step 2: Manually delete all related objects first
            logger.info(f"Deleting related objects for target {target_id}")
            
            # Delete all photos manually using force_delete to bypass validation
            photos_deleted = 0
            for photo in target.images.all():
                try:
                    # Remove the image file from storage
                    if photo.image:
                        try:
                            photo.image.delete(save=False)
                        except Exception as e:
                            logger.warning(f"Failed to delete image file for photo {photo.id}: {e}")
                    
                    # Use force_delete to bypass the "last image" validation
                    # This is safe because we're deleting the entire target
                    photo.force_delete()
                    photos_deleted += 1
                    logger.info(f"Force deleted photo {photo.id}")
                except Exception as e:
                    logger.error(f"Failed to delete photo {photo.id}: {e}")
            
            logger.info(f"Deleted {photos_deleted} photos for target {target_id}")
            
            # Delete search results
            search_results_deleted = 0
            for result in target.search_results.all():
                try:
                    result.delete()
                    search_results_deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete search result {result.id}: {e}")
            
            logger.info(f"Deleted {search_results_deleted} search results for target {target_id}")
            
            # Delete search histories
            search_histories_deleted = 0
            for history in target.search_histories.all():
                try:
                    history.delete()
                    search_histories_deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete search history {history.id}: {e}")
            
            logger.info(f"Deleted {search_histories_deleted} search histories for target {target_id}")
            
            # Step 3: Check for any remaining related objects
            logger.info(f"Checking for remaining related objects for target {target_id}")
            
            # Check if there are any remaining photos
            remaining_photos = target.images.count()
            if remaining_photos > 0:
                logger.warning(f"Still have {remaining_photos} photos after deletion attempt")
                # Force delete any remaining photos
                for photo in target.images.all():
                    try:
                        photo.force_delete()
                        logger.info(f"Force deleted remaining photo {photo.id}")
                    except Exception as e:
                        logger.error(f"Failed to delete remaining photo {photo.id}: {e}")
            
            # Check if there are any remaining search results
            remaining_results = target.search_results.count()
            if remaining_results > 0:
                logger.warning(f"Still have {remaining_results} search results after deletion attempt")
                # Force delete any remaining search results
                for result in target.search_results.all():
                    try:
                        result.delete()
                        logger.info(f"Deleted remaining search result {result.id}")
                    except Exception as e:
                        logger.error(f"Failed to delete remaining search result {result.id}: {e}")
            
            # Check if there are any remaining search histories
            remaining_histories = target.search_histories.count()
            if remaining_histories > 0:
                logger.warning(f"Still have {remaining_histories} search histories after deletion attempt")
                # Force delete any remaining search histories
                for history in target.search_histories.all():
                    try:
                        history.delete()
                        logger.info(f"Deleted remaining search history {history.id}")
                    except Exception as e:
                        logger.error(f"Failed to delete remaining search history {history.id}: {e}")
            
            # Step 4: Send notification
            try:
                notify.send(request.user, recipient=target.created_by or request.user, verb='deleted target', target=target)
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
            
            # Step 4: Now delete the target itself
            logger.info(f"Deleting target {target_id}")
            
            # Final check - verify no related objects remain
            final_photos = target.images.count()
            final_results = target.search_results.count()
            final_histories = target.search_histories.count()
            
            logger.info(f"Final object counts - Photos: {final_photos}, Results: {final_results}, Histories: {final_histories}")
            
            if final_photos > 0 or final_results > 0 or final_histories > 0:
                logger.warning(f"Still have related objects after deletion attempts")
                raise Exception(f"Cannot delete target: still has {final_photos} photos, {final_results} results, {final_histories} histories")
            
            # First try to delete using Django ORM
            try:
                target.delete()
                logger.info(f"Successfully deleted target {target_id} using Django ORM")
            except Exception as e:
                logger.warning(f"Django ORM deletion failed: {e}, trying raw SQL")
                
                # If Django ORM fails, use raw SQL to bypass any remaining constraints
                try:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        # Delete the target directly from database
                        cursor.execute("DELETE FROM backendapp_targets_watchlist WHERE id = %s", [target_id])
                        if cursor.rowcount > 0:
                            logger.info(f"Successfully deleted target {target_id} from database using raw SQL")
                        else:
                            logger.warning(f"No rows were deleted for target {target_id}")
                            
                except Exception as sql_error:
                    logger.error(f"Raw SQL deletion also failed: {sql_error}")
                    raise Exception(f"Failed to delete target using both Django ORM and raw SQL: {e}, SQL error: {sql_error}")
            
            messages.success(request, f'Target "{target_name}" deleted successfully!')
            logger.info(f"Target deletion completed successfully for {target_name} (ID: {target_id})")
            return redirect('list_watchlist')
            
        except Exception as e:
            logger.error(f"Failed to delete target {target_id}: {e}", exc_info=True)
            
            # Provide specific error messages
            error_msg = str(e)
            if "foreign key constraint" in error_msg.lower():
                messages.error(request, 'Cannot delete target: it is referenced by other objects in the system.')
            elif "validation" in error_msg.lower():
                messages.error(request, f'Validation error: {error_msg}')
            elif "permission" in error_msg.lower():
                messages.error(request, 'Permission denied: you do not have permission to delete this target.')
            else:
                messages.error(request, f'Failed to delete target: {error_msg}')
            
            return redirect('target_profile', pk=pk)
            
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
            # Check if this is the last image before deletion
            if target.images.count() <= 1:
                messages.error(
                    request, 
                    f"Cannot delete the last image for target '{target.target_name}'. "
                    "Each target must have at least one image. "
                    "Please add another image first, or delete the entire target instead."
                )
                return redirect('target_profile', pk=pk)
            
            # Send notification
            try:
                notify.send(request.user, recipient=target.created_by or request.user, verb='deleted image', target=target, action_object=image)
            except Exception:
                pass
            
            # Delete the image
            image.delete()
            messages.success(request, 'Image deleted successfully!')
            return redirect('target_profile', pk=pk)
            
        except ValidationError as e:
            # Handle validation errors gracefully
            messages.error(request, str(e))
            return redirect('target_profile', pk=pk)
        except Exception as e:
            # Handle other errors
            messages.error(request, f'Failed to delete image: {str(e)}')
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
@require_POST
def mark_notification_read(request):
    """Mark a single notification as read for the current user (AJAX)."""
    notification_id = request.POST.get('id') or request.POST.get('notification_id')
    if not notification_id:
        return JsonResponse({'success': False, 'error': 'Missing id'}, status=400)
    try:
        nid = int(notification_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid id'}, status=400)
    try:
        notification = Notification.objects.get(id=nid, recipient=request.user)
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    try:
        notification.mark_as_read()
    except Exception:
        try:
            notification.unread = False
            notification.save(update_fields=['unread'])
        except Exception:
            return JsonResponse({'success': False, 'error': 'Failed to mark as read'}, status=500)
    return JsonResponse({'success': True})

@login_required
@require_POST
def clear_notifications(request):
    """Bulk clear notifications for the current user.
    Actions:
      - action=all: delete all notifications
      - action=read: delete only read notifications
      - action=older_than_days&days=N: delete notifications older than N days
      - action=keep_latest&keep=N&scope=all|read: keep latest N (by timestamp desc), delete the rest in scope
    """
    action = request.POST.get('action')
    if not action:
        return JsonResponse({'success': False, 'error': 'Missing action'}, status=400)
    qs = Notification.objects.filter(recipient=request.user)
    try:
        if action == 'all':
            deleted, _ = qs.delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        if action == 'read':
            deleted, _ = qs.filter(unread=False).delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        if action == 'older_than_days':
            days_raw = request.POST.get('days')
            try:
                days = int(days_raw)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Invalid days'}, status=400)
            cutoff = timezone.now() - timedelta(days=days)
            deleted, _ = qs.filter(timestamp__lt=cutoff).delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        if action == 'keep_latest':
            keep_raw = request.POST.get('keep')
            scope = (request.POST.get('scope') or 'read').lower()
            try:
                keep = int(keep_raw)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Invalid keep'}, status=400)
            scope_qs = qs if scope == 'all' else qs.filter(unread=False)
            ids_to_keep = list(scope_qs.order_by('-timestamp').values_list('id', flat=True)[:keep])
            if not ids_to_keep:
                # nothing to keep; delete per scope
                deleted, _ = scope_qs.delete()
                return JsonResponse({'success': True, 'deleted': deleted})
            deleted, _ = scope_qs.exclude(id__in=ids_to_keep).delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        return JsonResponse({'success': False, 'error': 'Unknown action'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def delete_notification(request):
    """Delete a single notification for the current user (hard delete)."""
    notification_id = request.POST.get('id') or request.POST.get('notification_id')
    if not notification_id:
        return JsonResponse({'success': False, 'error': 'Missing id'}, status=400)
    try:
        nid = int(notification_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid id'}, status=400)
    try:
        deleted, _ = Notification.objects.filter(id=nid, recipient=request.user).delete()
        if deleted:
            return JsonResponse({'success': True, 'deleted': deleted})
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def notifications_list(request):
    """List notifications for the current user."""
    notifications_qs = Notification.objects.filter(recipient=request.user).select_related('actor_content_type', 'target_content_type', 'action_object_content_type').order_by('-timestamp')
    per_page_default = 20
    try:
        per_page = int(request.GET.get('per_page', per_page_default))
    except (TypeError, ValueError):
        per_page = per_page_default
    paginator = Paginator(notifications_qs, per_page)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    current = page_obj.number
    total = paginator.num_pages
    start = max(1, current - 2)
    end = min(total, current + 2)
    page_range = list(range(start, end + 1))
    return render(request, 'notifications_list.html', {
        'notifications': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_range': page_range,
        'per_page': per_page,
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
    """Milvus vector search interface for face similarity search"""
    if request.method == 'POST':
        form = MilvusSearchForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Import the face search service
                from face_ai.services.face_search_service import FaceSearchService
                
                # Initialize the service
                face_search_service = FaceSearchService()
                
                # Get form data
                face_image = form.cleaned_data['face_image']
                top_k = form.cleaned_data['top_k']
                confidence_threshold = form.cleaned_data['confidence_threshold']
                
                # Perform face search
                search_result = face_search_service.search_faces_in_image(
                    face_image, 
                    top_k=top_k, 
                    confidence_threshold=confidence_threshold
                )
                
                if search_result['success']:
                    # Get search statistics
                    stats = face_search_service.get_search_statistics()
                    
                    return render(request, 'milvus_search_results.html', {
                        'search_result': search_result,
                        'stats': stats,
                        'form': form,
                        'uploaded_image': face_image
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
    
    # Get basic statistics for display
    try:
        from face_ai.services.face_search_service import FaceSearchService
        face_search_service = FaceSearchService()
        stats = face_search_service.get_search_statistics()
    except Exception as e:
        logger.warning(f"Could not get search statistics: {e}")
        stats = {'success': False, 'error': str(e)}
    
    return render(request, 'milvus_search.html', {
        'form': form, 
        'stats': stats
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

def is_case_manager(user):
    return user.is_authenticated and user.role == 'case_manager'

def is_operator(user):
    return user.is_authenticated and user.role == 'operator'

def is_staff_or_admin(user):
    """Check if user is staff or admin"""
    return user.is_authenticated and (user.is_staff or user.role == 'admin')

def handle_failed_login(request, user):
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
                    handle_failed_login(request, user)
                    
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
        'admin_users': users.filter(is_superuser=True).count(),
        'locked_users': users.filter(is_active=False).count(),
        'inactive_users': users.filter(is_active=False).count(),
    }
    return render(request, 'user_list.html', context)

@login_required
def user_create(request):
    """Create new user (admin only)"""
    if not is_staff_or_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
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
        form = AdminUserCreationForm()
    
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
        form = AdminUserChangeForm(request.POST, instance=user)
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
        form = AdminUserChangeForm(instance=user)
    
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
        FormClass = AdminUserChangeForm if is_staff_or_admin(user) else SelfUserChangeForm
        form = FormClass(request.POST, request.FILES, instance=user)
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
        FormClass = AdminUserChangeForm if is_staff_or_admin(user) else SelfUserChangeForm
        form = FormClass(instance=user)
    # Recent activity & personal content
    recent_notifications = Notification.objects.filter(recipient=user).order_by('-timestamp')[:5]
    recent_cases = Case.objects.filter(created_by=user).order_by('-created_at')[:5]
    recent_targets = Targets_watchlist.objects.filter(created_by=user).order_by('-created_at')[:5]
    recent_searches = SearchQuery.objects.filter(user=user).order_by('-created_at')[:5]

    context = {
        'form': form,
        'user': user,
        'title': 'My Profile',
        'submit_text': 'Update Profile',
        'recent_notifications': recent_notifications,
        'recent_cases': recent_cases,
        'recent_targets': recent_targets,
        'recent_searches': recent_searches,
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
            # Check if at least one image is provided
            images = form.cleaned_data.get('images') or []
            if not images:
                messages.error(request, 'At least one image is required for each target.')
                return render(request, 'add_target_to_case.html', {'form': form, 'case': case})
            
            target = form.save(commit=False)
            target.case = case
            target.created_by = request.user
            target.save()
            try:
                notify.send(request.user, recipient=case.created_by, verb='added target', target=target, action_object=case)
            except Exception:
                pass
            
            # Handle multiple image uploads using validated files from the form
            uploaded_count = 0
            created_photos = []
            
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        target_photo = TargetPhoto.objects.create(person=target, image=image, uploaded_by=request.user)
                        uploaded_count += 1
                        created_photos.append(target_photo)
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')
            
            # Ensure at least one photo was successfully uploaded
            if uploaded_count == 0:
                # Delete the target if no images could be uploaded
                target.delete()
                messages.error(request, 'Failed to upload any images. Target creation cancelled.')
                return render(request, 'add_target_to_case.html', {'form': form, 'case': case})
            
            # Process photos for face detection and embedding storage
            if created_photos:
                try:
                    from face_ai.services.target_integration import TargetIntegrationService
                    
                    # Initialize face AI service
                    face_service = TargetIntegrationService()
                    
                    # Process all photos for the target
                    processing_result = face_service.process_target_photos_batch(created_photos, str(target.id))
                    
                    if processing_result['success']:
                        total_embeddings = processing_result['total_embeddings']
                        processed_photos = processing_result['processed_photos']
                        
                        if total_embeddings > 0:
                            messages.success(
                                request, 
                                f'Target "{target.target_name}" added successfully with {uploaded_count} images! '
                                f'Face AI processed {processed_photos} photos and stored {total_embeddings} face embeddings in Milvus.'
                            )
                        else:
                            messages.success(
                                request, 
                                f'Target "{target.target_name}" added successfully with {uploaded_count} images! '
                                f'Face AI processed {processed_photos} photos but no faces were detected.'
                            )
                        
                        # Log any failed photos
                        if processing_result['failed_photos']:
                            failed_count = len(processing_result['failed_photos'])
                            messages.warning(
                                request, 
                                f'{failed_count} photos failed face processing. Check logs for details.'
                            )
                            
                    else:
                        messages.warning(
                            request, 
                            f'Target "{target.target_name}" added successfully with {uploaded_count} images, '
                            f'but face AI processing failed: {processing_result.get("error", "Unknown error")}'
                        )
                        
                except ImportError:
                    messages.warning(
                        request, 
                        f'Target "{target.target_name}" added successfully with {uploaded_count} images, '
                        f'but face AI service is not available.'
                    )
                except Exception as e:
                    logger.error(f"Face AI processing failed for target {target.id}: {e}")
                    messages.warning(
                        request, 
                        f'Target "{target.target_name}" added successfully with {uploaded_count} images, '
                        f'but face AI processing encountered an error.'
                    )
            else:
                messages.warning(request, f'Target "{target.target_name}" added to case "{case.case_name}", but no images were uploaded.')
            
            return redirect('case_detail', pk=case.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TargetsWatchlistForm(initial={'case': case})
    
    return render(request, 'add_target_to_case.html', {'form': form, 'case': case})

@login_required
def face_verification(request):
    """Face verification service to compare two images and show similarity"""
    if request.method == 'POST':
        try:
            # Check if we have base64 data from preview or file uploads
            image1_base64 = request.POST.get('image1_base64')
            image2_base64 = request.POST.get('image2_base64')
            threshold = float(request.POST.get('threshold', 50)) / 100  # Convert percentage to decimal
            
            # If no base64 data, process file uploads
            if not image1_base64 or not image2_base64:
                image1 = request.FILES.get('image1')
                image2 = request.FILES.get('image2')
                
                if not image1 or not image2:
                    messages.error(request, 'Please upload both images for comparison.')
                    return render(request, 'face_verification.html')
                
                # Convert images to base64 for processing and display
                import base64
                
                def image_to_base64(image_file):
                    image_file.seek(0)
                    image_data = image_file.read()
                    return base64.b64encode(image_data).decode('utf-8')
                
                # Process images
                image1_base64 = image_to_base64(image1)
                image2_base64 = image_to_base64(image2)
                image1_name = image1.name
                image2_name = image2.name
            else:
                # Use names from preview or generate generic names
                image1_name = request.POST.get('image1_name', 'Reference Image')
                image2_name = request.POST.get('image2_name', 'Query Image')
            
            # Import face AI service
            from face_ai.services.face_detection import FaceDetectionService
            from face_ai.services.milvus_service import MilvusService
            
            face_service = FaceDetectionService()
            milvus_service = MilvusService()
            
            # CRITICAL: Validate face detection before verification
            # Check Image 1 for single face
            face1_validation = face_service.detect_faces_in_image_base64(image1_base64)
            if not face1_validation['success']:
                messages.error(request, f'Image 1: {face1_validation["error"]}')
                return render(request, 'face_verification.html')
            
            if face1_validation['faces_detected'] == 0:
                messages.error(request, 'Image 1: No faces detected. Please upload an image with a clear, visible face.')
                return render(request, 'face_verification.html')
            
            if face1_validation['faces_detected'] > 1:
                messages.error(request, f'Image 1: Multiple faces detected ({face1_validation["faces_detected"]}). Please upload an image with only one person.')
                return render(request, 'face_verification.html')
            
            # Check Image 2 for single face
            face2_validation = face_service.detect_faces_in_image_base64(image2_base64)
            if not face2_validation['success']:
                messages.error(request, f'Image 2: {face2_validation["error"]}')
                return render(request, 'face_verification.html')
            
            if face2_validation['faces_detected'] == 0:
                messages.error(request, 'Image 2: No faces detected. Please upload an image with a clear, visible face.')
                return render(request, 'face_verification.html')
            
            if face2_validation['faces_detected'] > 1:
                messages.error(request, f'Image 2: Multiple faces detected ({face2_validation["faces_detected"]}). Please upload an image with only one person.')
                return render(request, 'face_verification.html')
            
            # Validate face quality and confidence
            face1_confidence = face1_validation['faces'][0]['confidence'] if face1_validation['faces'] else 0
            face2_confidence = face2_validation['faces'][0]['confidence'] if face2_validation['faces'] else 0
            
            min_confidence = 0.6  # Minimum detection confidence
            if face1_confidence < min_confidence:
                messages.warning(request, f'Image 1: Low face detection confidence ({face1_confidence:.1%}). Results may be unreliable.')
            
            if face2_confidence < min_confidence:
                messages.warning(request, f'Image 2: Low face detection confidence ({face2_confidence:.1%}). Results may be unreliable.')
            
            # Now proceed with face verification since we have valid single faces
            result = face_service.verify_faces(image1_base64, image2_base64, threshold)
            
            if result['success']:
                # Store results for template
                context = {
                    'verification_result': result,
                    'image1_name': image1_name,
                    'image2_name': image2_name,
                    'threshold': threshold * 100,
                    'similarity_score': result['similarity_score'],
                    'is_match': result['faces_match'],  # Map faces_match to is_match for template
                    'age_estimate': result.get('face1', {}).get('age', 'N/A'),
                    'gender_estimate': result.get('face1', {}).get('gender', 'N/A'),
                    'confidence': result.get('face1', {}).get('confidence', 'N/A'),
                    'image1_base64': image1_base64,
                    'image2_base64': image2_base64,
                    'face1_confidence': face1_confidence,
                    'face2_confidence': face2_confidence,
                    'face1_bbox': face1_validation['faces'][0]['bbox'] if face1_validation['faces'] else None,
                    'face2_bbox': face2_validation['faces'][0]['bbox'] if face2_validation['faces'] else None
                }
                
                # Add success message
                if result['faces_match']:
                    messages.success(request, f'✅ Faces MATCH! Similarity: {result["similarity_score"]:.2%}')
                else:
                    messages.warning(request, f'❌ Faces DO NOT MATCH. Similarity: {result["similarity_score"]:.2%}')
                
                return render(request, 'face_verification.html', context)
            else:
                messages.error(request, f'Face verification failed: {result.get("error", "Unknown error")}')
                return render(request, 'face_verification.html')
                
        except Exception as e:
            messages.error(request, f'Error during face verification: {str(e)}')
            return render(request, 'face_verification.html')
    
    return render(request, 'face_verification.html')

@login_required
def face_verification_preview(request):
    """Preview uploaded images and validate face detection requirements before verification"""
    if request.method == 'POST':
        try:
            # Get form data
            image1 = request.FILES.get('image1')
            image2 = request.FILES.get('image2')
            threshold = float(request.POST.get('threshold', 50)) / 100
            
            if not image1 or not image2:
                messages.error(request, 'Please upload both images for comparison.')
                return render(request, 'face_verification.html')
            
            # Import face AI service
            from face_ai.services.face_detection import FaceDetectionService
            
            face_service = FaceDetectionService()
            
            # Convert images to base64 for preview and validation
            import base64
            
            def image_to_base64(image_file):
                image_file.seek(0)
                image_data = image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
            
            # Process images
            img1_base64 = image_to_base64(image1)
            img2_base64 = image_to_base64(image2)
            
            # Validate face detection requirements
            face1_validation = face_service.detect_faces_in_image_base64(img1_base64)
            face2_validation = face_service.detect_faces_in_image_base64(img2_base64)
            
            # Prepare validation results
            validation_results = {
                'image1': {
                    'name': image1.name,
                    'base64': img1_base64,
                    'validation': face1_validation,
                    'status': 'valid' if face1_validation['success'] and face1_validation['faces_detected'] == 1 else 'invalid'
                },
                'image2': {
                    'name': image2.name,
                    'base64': img2_base64,
                    'validation': face2_validation,
                    'status': 'valid' if face2_validation['success'] and face2_validation['faces_detected'] == 1 else 'invalid'
                },
                'threshold': threshold * 100,
                'overall_status': 'ready' if (
                    face1_validation['success'] and face1_validation['faces_detected'] == 1 and
                    face2_validation['success'] and face2_validation['faces_detected'] == 1
                ) else 'not_ready'
            }
            
            # Add appropriate messages
            if validation_results['overall_status'] == 'ready':
                messages.success(request, '✅ Both images meet verification requirements! Ready to proceed with face verification.')
            else:
                if validation_results['image1']['status'] == 'invalid':
                    if face1_validation['faces_detected'] == 0:
                        messages.error(request, f'❌ {image1.name}: No faces detected. Please upload an image with a clear, visible face.')
                    elif face1_validation['faces_detected'] > 1:
                        messages.error(request, f'❌ {image1.name}: Multiple faces detected ({face1_validation["faces_detected"]}). Please upload an image with only one person.')
                    else:
                        messages.error(request, f'❌ {image1.name}: Face detection failed. Please try a different image.')
                
                if validation_results['image2']['status'] == 'invalid':
                    if face2_validation['faces_detected'] == 0:
                        messages.error(request, f'❌ {image2.name}: No faces detected. Please upload an image with a clear, visible face.')
                    elif face2_validation['faces_detected'] > 1:
                        messages.error(request, f'❌ {image2.name}: Multiple faces detected ({face2_validation["faces_detected"]}). Please upload an image with only one person.')
                    else:
                        messages.error(request, f'❌ {image2.name}: Face detection failed. Please try a different image.')
                
                messages.warning(request, '⚠️ Please fix the issues above before proceeding with face verification.')
            
            return render(request, 'face_verification_preview.html', validation_results)
                
        except Exception as e:
            messages.error(request, f'Error during image validation: {str(e)}')
            return render(request, 'face_verification.html')
    
    return redirect('face_verification')

@login_required
def face_verification_watchlist(request):
    """Advanced watchlist verification with multiple modes"""
    # Get all watchlist targets for selection
    watchlist_targets = Targets_watchlist.objects.select_related('case').all()
    
    if request.method == 'POST':
        try:
            verification_mode = request.POST.get('verification_mode')
            threshold = float(request.POST.get('threshold', 60)) / 100
            max_results = int(request.POST.get('max_results', 5))
            
            if verification_mode == 'mode1':
                # Mode 1: Watchlist vs Image
                return handle_mode1_verification(request, watchlist_targets, threshold, max_results)
            elif verification_mode == 'mode2':
                # Mode 2: Watchlist vs Watchlist
                return handle_mode2_verification(request, watchlist_targets, threshold, max_results)
            else:
                messages.error(request, 'Invalid verification mode selected.')
                return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
                
        except Exception as e:
            messages.error(request, f'Error during watchlist verification: {str(e)}')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
    
    return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})

def handle_mode1_verification(request, watchlist_targets, threshold, max_results):
    """Handle Mode 1: Compare selected watchlist targets against one image"""
    try:
        query_image = request.FILES.get('query_image')
        target_ids = request.POST.getlist('target_ids')
        
        if not query_image:
            messages.error(request, 'Please upload an image for verification.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if not target_ids:
            messages.error(request, 'Please select at least one watchlist target.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Import services
        from face_ai.services.face_detection import FaceDetectionService
        from face_ai.services.milvus_service import MilvusService
        from .models import Targets_watchlist, TargetPhoto
        
        face_service = FaceDetectionService()
        milvus_service = MilvusService()
        
        # Convert image to base64 for processing
        import base64
        
        def image_to_base64(image_file):
            image_file.seek(0)
            image_data = image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
        
        # Process query image
        query_base64 = image_to_base64(query_image)
        
        # Validate face detection in query image
        query_validation = face_service.detect_faces_in_image_base64(query_base64)
        if not query_validation['success']:
            messages.error(request, f'Face detection failed: {query_validation["error"]}')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if query_validation['faces_detected'] == 0:
            messages.error(request, 'No faces detected in the uploaded image. Please upload an image with a clear, visible face.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if query_validation['faces_detected'] > 1:
            messages.error(request, f'Multiple faces detected ({query_validation["faces_detected"]}). Please upload an image with only one person.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Get the face embedding from query image
        query_face = query_validation['faces'][0]
        query_embedding = face_service.app.get(face_service._base64_to_image(query_base64))[0].normed_embedding
        
        # Process each selected target
        verification_results = []
        total_targets = len(target_ids)
        
        for target_id in target_ids:
            try:
                target = Targets_watchlist.objects.get(id=target_id)
                
                # Get target photos
                target_photos = TargetPhoto.objects.filter(person=target)
                
                for photo in target_photos:
                    try:
                        # Convert photo to base64 for comparison
                        photo_base64 = face_service.image_to_base64(photo.image)
                        
                        # Compare faces
                        result = face_service.verify_faces(query_base64, photo_base64, threshold)
                        
                        if result['success'] and result['faces_match']:
                            verification_results.append({
                                'target': target,
                                'photo': photo,
                                'similarity': result['similarity_score'] * 100,
                                'confidence': query_face['confidence']
                            })
                    except Exception as e:
                        logger.error(f"Error processing photo {photo.id}: {e}")
                        continue
                        
            except Targets_watchlist.DoesNotExist:
                continue
        
        # Sort by similarity (highest first)
        verification_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Limit results per target
        if max_results > 0:
            verification_results = verification_results[:max_results * total_targets]
        
        # Prepare context
        context = {
            'watchlist_targets': watchlist_targets,
            'verification_mode': 'mode1',
            'query_image_name': query_image.name,
            'query_image_base64': query_base64,
            'threshold': threshold * 100,
            'total_targets': total_targets,
            'verification_results': verification_results,
            'total_matches': len(verification_results)
        }
        
        if verification_results:
            messages.success(request, f'Found {len(verification_results)} potential matches across {total_targets} selected targets!')
        else:
            messages.info(request, f'No matches found above {threshold * 100}% similarity threshold.')
        
        return render(request, 'face_verification_watchlist.html', context)
        
    except Exception as e:
        messages.error(request, f'Error during Mode 1 verification: {str(e)}')
        return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})

def handle_mode2_verification(request, watchlist_targets, threshold, max_results):
    """Handle Mode 2: Compare watchlist targets against each other using Milvus embeddings"""
    try:
        source_target_id = request.POST.get('source_target_id')
        target_ids = request.POST.getlist('target_ids')
        
        if not source_target_id:
            messages.error(request, 'Please select a source target.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if not target_ids:
            messages.error(request, 'Please select at least one target to compare.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Import services
        from face_ai.services.milvus_service import MilvusService
        from .models import Targets_watchlist, TargetPhoto
        
        milvus_service = MilvusService()
        
        # Check Milvus collection status first
        collection_status = milvus_service.check_collection_status()
        if collection_status['status'] == 'error':
            logger.error(f"Milvus collection error: {collection_status['message']}")
            messages.error(request, f'Milvus collection error: {collection_status["message"]}')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        elif collection_status['status'] == 'warning':
            logger.warning(f"Milvus collection has issues: {collection_status['message']}")
            messages.warning(request, f'Milvus collection has issues, attempting to continue with limited functionality: {collection_status["message"]}')
            # Continue with limited functionality instead of failing completely
        else:
            logger.info(f"Milvus collection status: {collection_status}")
        
        # Get source target
        try:
            source_target = Targets_watchlist.objects.get(id=source_target_id)
        except Targets_watchlist.DoesNotExist:
            messages.error(request, 'Source target not found.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Get source target photos and their Milvus embeddings
        source_photos = TargetPhoto.objects.filter(person=source_target)
        if not source_photos.exists():
            messages.error(request, 'Source target has no photos for comparison.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Process each target to compare using normalized target embeddings
        verification_results = []
        total_targets = len(target_ids)
        
        # Debug logging
        logger.info(f"Mode 2: Processing {total_targets} targets against source target {source_target.target_name}")
        logger.info(f"Source target has {source_photos.count()} photos")
        
        # Get the source target's normalized embedding
        source_embedding = milvus_service.get_target_normalized_embedding(str(source_target.id))
        if not source_embedding:
            logger.warning(f"No normalized embedding found for source target {source_target.target_name}")
            messages.warning(request, f"No normalized embedding found for source target {source_target.target_name}. Please ensure photos are processed through the face-ai system first.")
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'verification_mode': 'mode2',
                'source_target_name': source_target.target_name,
                'threshold': threshold * 100,
                'total_targets': total_targets,
                'verification_results': [],
                'total_matches': 0,
                'error_message': f'No normalized embedding found for source target {source_target.target_name}. Please ensure photos are processed through the face-ai system first.'
            })
        
        logger.info(f"Found normalized embedding for source target {source_target.target_name}")
        
        # Search for similar targets using the source target's normalized embedding
        search_results = milvus_service.search_similar_targets(
            source_embedding, 
            top_k=max_results * total_targets,  # Get enough results for all targets
            threshold=threshold
        )
        
        logger.info(f"Milvus search returned {len(search_results)} similar targets")
        
        # Process search results and get target information
        for result in search_results:
            try:
                result_target_id = result.get('target_id')
                similarity = result.get('similarity', 0)
                
                # Skip if this is the source target itself
                if str(result_target_id) == str(source_target.id):
                    continue
                
                # Check if this result is in our selected targets
                if str(result_target_id) in target_ids:
                    # Get the target information
                    target = Targets_watchlist.objects.get(id=result_target_id)
                    
                    # Get a representative photo for display
                    photo = TargetPhoto.objects.filter(person=target).first()
                    
                    if photo:
                        verification_results.append({
                            'target': target,
                            'photo': photo,
                            'similarity': similarity * 100,  # Convert to percentage
                            'milvus_id': result.get('id'),
                            'confidence': result.get('confidence', 0)
                        })
                        logger.info(f"Added verification result for {target.target_name} with similarity {similarity * 100:.1f}%")
                        
            except Exception as e:
                logger.error(f"Error processing search result: {e}")
                continue
                            
            except Targets_watchlist.DoesNotExist:
                continue
        
        # Sort by similarity (highest first)
        verification_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Remove duplicates (same target-photo combination)
        seen_combinations = set()
        unique_results = []
        for result in verification_results:
            combination = (result['target'].id, result['photo'].id)
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_results.append(result)
        
        verification_results = unique_results
        
        # Limit results per target
        if max_results > 0:
            verification_results = verification_results[:max_results * total_targets]
        
        # Prepare context
        context = {
            'watchlist_targets': watchlist_targets,
            'verification_mode': 'mode2',
            'source_target_name': source_target.target_name,
            'threshold': threshold * 100,
            'total_targets': total_targets,
            'verification_results': verification_results,
            'total_matches': len(verification_results)
        }
        
        if verification_results:
            messages.success(request, f'Found {len(verification_results)} potential matches across {total_targets} targets using Milvus embeddings!')
        else:
            messages.info(request, f'No matches found above {threshold * 100}% similarity threshold.')
            # Add debug info to help troubleshoot
            messages.warning(request, 'Debug: Check logs for detailed information about the verification process.')
        
        return render(request, 'face_verification_watchlist.html', context)
        
    except Exception as e:
        messages.error(request, f'Error during Mode 2 verification: {str(e)}')
        return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
