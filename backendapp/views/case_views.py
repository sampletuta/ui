"""
Case Management Views Module
Handles case creation, editing, deletion, and target assignment
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
import logging

from ..forms import CaseForm, TargetsWatchlistForm
from ..models import Case, TargetPhoto, Targets_watchlist

logger = logging.getLogger(__name__)

@login_required
def case_list(request):
    """List all cases for the current user"""
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
                from notifications.signals import notify
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
                from notifications.signals import notify
                notify.send(request.user, recipient=request.user, verb='updated case', target=case)
            except Exception:
                pass
            return redirect('case_detail', pk=case.pk)
    else:
        form = CaseForm(instance=case)
    
    return render(request, 'case_form.html', {'form': form, 'title': f'Edit Case: {case.case_name}'})

@login_required
def case_delete(request, pk):
    """Delete a case and all its targets with proper cascading deletion"""
    case = get_object_or_404(Case, pk=pk, created_by=request.user)
    if request.method == 'POST':
        case_name = case.case_name
        case_id = str(case.id)
        
        try:
            logger.info(f"Starting deletion process for case {case_name} (ID: {case_id})")
            
            # Step 1: Get all targets in this case
            targets = case.targets_watchlist.all()
            target_count = targets.count()
            logger.info(f"Case {case_name} has {target_count} targets to delete")
            
            # Step 2: Delete all targets in the case first (with proper cleanup)
            targets_deleted = 0
            for target in targets:
                try:
                    target_name = target.target_name
                    target_id = str(target.id)
                    logger.info(f"Deleting target {target_name} (ID: {target_id}) from case {case_name}")
                    
                    # Use the standard target deletion logic
                    success = delete_target_for_case_deletion(target, request.user)
                    if success:
                        targets_deleted += 1
                        logger.info(f"Successfully deleted target {target_name}")
                    else:
                        logger.error(f"Failed to delete target {target_name}")
                        
                except Exception as e:
                    logger.error(f"Error deleting target {target.target_name}: {e}")
                    continue
            
            logger.info(f"Deleted {targets_deleted} out of {target_count} targets from case {case_name}")
            
            # Step 3: Send notification about case deletion
            try:
                from notifications.signals import notify
                notify.send(request.user, recipient=case.created_by, verb='deleted case', target=case, description=f'Case "{case_name}" deleted')
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
            
            # Step 4: Now delete the case itself
            logger.info(f"Deleting case {case_name}")
            case.delete()
            
            messages.success(request, f'Case "{case_name}" and {targets_deleted} targets deleted successfully!')
            logger.info(f"Case deletion completed successfully for {case_name} (ID: {case_id})")
            return redirect('case_list')
            
        except Exception as e:
            logger.error(f"Failed to delete case {case_name}: {e}", exc_info=True)
            messages.error(request, f'Failed to delete case "{case_name}": {str(e)}')
            return redirect('case_detail', pk=pk)
    
    return render(request, 'case_confirm_delete.html', {'case': case})

def delete_target_for_case_deletion(target, user):
    """
    Helper function to delete a target when deleting a case.
    This now uses standard deletion since the signal validation has been removed.
    """
    try:
        target_name = target.target_name
        target_id = str(target.id)
        
        logger.info(f"Starting deletion process for target {target_name} (ID: {target_id}) during case deletion")
        
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
        
        # Step 3: Now delete the target itself
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
        
        logger.info(f"Target deletion completed successfully for {target_name} (ID: {target_id})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete target {target_id}: {e}", exc_info=True)
        return False

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
                from notifications.signals import notify
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
                    from face_ai.services.target_integration_wrapper import TargetIntegrationWrapper
                    
                    # Initialize face AI service with async support
                    face_service = TargetIntegrationWrapper(use_async=True, max_workers=4)
                    
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
