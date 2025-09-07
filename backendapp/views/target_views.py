"""
Target Management Views Module
Handles target creation, editing, deletion, and image management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction
import logging

from ..forms import TargetsWatchlistForm
from ..models import TargetPhoto, Targets_watchlist

logger = logging.getLogger(__name__)

@login_required
def list_watchlist(request):
    """List all watchlist targets with search and pagination"""
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
    """View target profile details"""
    target = get_object_or_404(Targets_watchlist.objects.select_related('case', 'created_by').prefetch_related('images'), pk=pk)
    return render(request, 'target_profile.html', {'target': target})

@login_required
def edit_target(request, pk):
    """Edit an existing target"""
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
    """Delete a target and all associated data"""
    target = get_object_or_404(Targets_watchlist, pk=pk)
    if request.method == 'POST':
        try:
            target_name = target.target_name
            target_id = str(target.id)
            
            logger.info(f"Starting deletion process for target {target_name} (ID: {target_id})")
            
            # Pre-check: Ensure we can delete this target
            if target.images.count() == 0:
                messages.error(request, f'Target "{target_name}" has no images and cannot be deleted.')
                return redirect('target_profile', pk=pk)
            
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
            
            # Step 2: Delete all related objects using standard Django methods
            logger.info(f"Deleting related objects for target {target_id}")
            
            # Delete all photos using force_delete to bypass model validation
            photos_deleted = 0
            for photo in target.images.all():
                try:
                    # Remove the image file from storage
                    if photo.image:
                        try:
                            photo.image.delete(save=False)
                        except Exception as e:
                            logger.warning(f"Failed to delete image file for photo {photo.id}: {e}")
                    
                    # Use force_delete to bypass the "last image" validation in the model
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
            
            # Step 3: Send notification
            try:
                from backendapp.utils.notifications import notify
                notify(recipient=target.created_by or request.user, actor=request.user, verb='deleted target', target=target)
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
            
            # Delete the target using Django ORM
            target.delete()
            logger.info(f"Successfully deleted target {target_id} using Django ORM")
            
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
                if "last image" in error_msg.lower():
                    messages.error(
                        request, 
                        f'Cannot delete target "{target_name}": Validation error - targets must have at least one image. '
                        'This error should not occur during normal deletion. Please contact support if this persists.'
                    )
                else:
                    messages.error(request, f'Validation error: {error_msg}')
            elif "permission" in error_msg.lower():
                messages.error(request, 'Permission denied: you do not have permission to delete this target.')
            else:
                messages.error(request, f'Failed to delete target: {error_msg}')
            
            return redirect('target_profile', pk=pk)
            
    return render(request, 'delete_target.html', {'target': target})

@login_required
def add_images(request, pk):
    """Add images to an existing target"""
    target = get_object_or_404(Targets_watchlist, pk=pk)
    if request.method == 'POST':
        images = request.FILES.getlist('images')
        if images:
            # Safety check: ensure we're not removing all existing images
            current_image_count = target.images.count()
            if current_image_count == 0:
                messages.warning(
                    request, 
                    f'Target "{target.target_name}" currently has no images. '
                    'Adding images will restore the target to a valid state.'
                )
            
            uploaded_count = 0
            for image in images:
                if image.name:  # Only process files with names
                    try:
                        TargetPhoto.objects.create(person=target, image=image, uploaded_by=request.user)
                        uploaded_count += 1
                        try:
                            from backendapp.utils.notifications import notify
                            notify(recipient=target.created_by or request.user, actor=request.user, verb='uploaded images', target=target)
                        except Exception:
                            pass
                    except Exception as e:
                        messages.error(request, f'Failed to upload {image.name}: {str(e)}')
            
            if uploaded_count > 0:
                new_total = current_image_count + uploaded_count
                messages.success(
                    request, 
                    f'{uploaded_count} image(s) uploaded successfully! '
                    f'Target "{target.target_name}" now has {new_total} image(s).'
                )
            else:
                messages.error(request, 'No valid images were uploaded.')
        else:
            messages.error(request, 'Please select at least one image to upload.')
        return redirect('target_profile', pk=pk)
    return render(request, 'add_images.html', {'target': target})

@login_required
def delete_image(request, pk, image_id):
    """Delete a specific image from a target"""
    target = get_object_or_404(Targets_watchlist, pk=pk)
    image = get_object_or_404(TargetPhoto, pk=image_id, person=target)
    
    if request.method == 'POST':
        try:
            # Check if this is the last image before deletion
            current_image_count = target.images.count()
            if current_image_count <= 1:
                messages.error(
                    request, 
                    f"Cannot delete the last image for target '{target.target_name}'. "
                    f"Each target must have at least one image for face recognition. "
                    f"Current image count: {current_image_count}. "
                    "Please add another image first, or delete the entire target instead."
                )
                return redirect('target_profile', pk=pk)
            
            # Additional safety check - ensure we're not deleting the last image
            if current_image_count == 1:
                messages.error(
                    request, 
                    f"Safety check failed: Attempting to delete the last image for target '{target.target_name}'. "
                    "This operation is not allowed. Please add another image first."
                )
                return redirect('target_profile', pk=pk)
            
            # Send notification
            try:
                from backendapp.utils.notifications import notify
                notify(recipient=target.created_by or request.user, actor=request.user, verb='deleted image', target=target, action_object=image)
            except Exception:
                pass
            
            # Delete the image
            image.delete()
            messages.success(request, f'Image deleted successfully! Target "{target.target_name}" now has {current_image_count - 1} image(s).')
            return redirect('target_profile', pk=pk)
            
        except ValidationError as e:
            # Handle validation errors gracefully
            error_msg = str(e)
            if "last image" in error_msg.lower():
                messages.error(
                    request, 
                    f'Cannot delete image: {error_msg} '
                    f'Target "{target.target_name}" must maintain at least one image for face recognition.'
                )
            else:
                messages.error(request, f'Validation error: {error_msg}')
            return redirect('target_profile', pk=pk)
        except Exception as e:
            # Handle other errors
            messages.error(request, f'Failed to delete image: {str(e)}')
            return redirect('target_profile', pk=pk)
    
    return render(request, 'delete_image.html', {'target': target, 'image': image})
