"""
Whitelist Management Views Module
Handles whitelist creation, editing, deletion, and image management for authorized personnel
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction
import logging

from ..forms import WhitelistForm
from ..models import WhitelistPhoto, Targets_whitelist

logger = logging.getLogger(__name__)

@login_required
def list_whitelist(request):
    """List all whitelist entries with search and pagination"""
    whitelist_qs = Targets_whitelist.objects.select_related('created_by', 'approved_by').prefetch_related('images').all()

    # Handle search functionality
    search_query = request.GET.get('q')
    if search_query:
        whitelist_qs = whitelist_qs.filter(
            Q(person_name__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    # Handle status filter
    status_filter = request.GET.get('status')
    if status_filter:
        whitelist_qs = whitelist_qs.filter(status=status_filter)

    # Handle access level filter
    access_filter = request.GET.get('access_level')
    if access_filter:
        whitelist_qs = whitelist_qs.filter(access_level=access_filter)

    # Pagination
    paginator = Paginator(whitelist_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'list_whitelist.html', {
        'whitelist_entries': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'status_filter': status_filter,
        'access_filter': access_filter
    })

@login_required
def whitelist_profile(request, pk):
    """View whitelist entry profile details"""
    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)

    return render(request, 'whitelist_profile.html', {
        'whitelist_entry': whitelist_entry,
        'images': whitelist_entry.images.all()
    })

@login_required
def add_whitelist(request):
    """Add new whitelist entry"""
    if request.method == 'POST':
        form = WhitelistForm(request.POST, request.FILES)
        if form.is_valid():
            whitelist_entry = form.save(commit=False)
            whitelist_entry.created_by = request.user

            # Set approval status based on user role
            if request.user.role in ['admin', 'case_manager']:
                whitelist_entry.approved_by = request.user
            else:
                messages.info(request, 'Your whitelist entry has been submitted for approval.')

            whitelist_entry.save()

            # Handle multiple image uploads
            images = form.cleaned_data.get('images') or []
            uploaded_count = 0
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        WhitelistPhoto.objects.create(
                            person=whitelist_entry,
                            image=image,
                            uploaded_by=request.user
                        )
                        uploaded_count += 1
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')

            if uploaded_count > 0:
                messages.success(request, f'Whitelist entry added successfully with {uploaded_count} image(s)!')
            else:
                messages.warning(request, 'Whitelist entry added, but no images were uploaded.')

            return redirect('list_whitelist')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = WhitelistForm()

    return render(request, 'add_whitelist.html', {'form': form})

@login_required
def edit_whitelist(request, pk):
    """Edit existing whitelist entry"""
    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)

    # Check permissions - only creator, admin, or case manager can edit
    if not (request.user == whitelist_entry.created_by or
            request.user.role in ['admin', 'case_manager']):
        messages.error(request, 'You do not have permission to edit this whitelist entry.')
        return redirect('whitelist_profile', pk=pk)

    if request.method == 'POST':
        form = WhitelistForm(request.POST, request.FILES, instance=whitelist_entry)
        if form.is_valid():
            whitelist_entry = form.save()

            # Handle new image uploads
            images = form.cleaned_data.get('images') or []
            uploaded_count = 0
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        WhitelistPhoto.objects.create(
                            person=whitelist_entry,
                            image=image,
                            uploaded_by=request.user
                        )
                        uploaded_count += 1
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')

            if uploaded_count > 0:
                messages.success(request, f'Whitelist entry updated with {uploaded_count} additional image(s)!')
            else:
                messages.success(request, 'Whitelist entry updated successfully!')

            return redirect('whitelist_profile', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = WhitelistForm(instance=whitelist_entry)

    return render(request, 'edit_whitelist.html', {
        'form': form,
        'whitelist_entry': whitelist_entry
    })

@login_required
def delete_whitelist(request, pk):
    """Delete whitelist entry"""
    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)

    # Check permissions
    if not (request.user == whitelist_entry.created_by or
            request.user.role in ['admin', 'case_manager']):
        messages.error(request, 'You do not have permission to delete this whitelist entry.')
        return redirect('whitelist_profile', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Delete all associated images first
                for image in whitelist_entry.images.all():
                    image.delete()

                # Delete the whitelist entry
                whitelist_entry.delete()

            messages.success(request, 'Whitelist entry deleted successfully.')
            return redirect('list_whitelist')

        except Exception as e:
            logger.error(f"Error deleting whitelist entry {pk}: {e}")
            messages.error(request, 'An error occurred while deleting the whitelist entry.')

    return render(request, 'delete_whitelist.html', {
        'whitelist_entry': whitelist_entry
    })

@login_required
def add_whitelist_images(request, pk):
    """Add additional images to existing whitelist entry"""
    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)

    # Check permissions
    if not (request.user == whitelist_entry.created_by or
            request.user.role in ['admin', 'case_manager']):
        messages.error(request, 'You do not have permission to add images to this whitelist entry.')
        return redirect('whitelist_profile', pk=pk)

    if request.method == 'POST':
        images = request.FILES.getlist('images')
        uploaded_count = 0

        for image in images:
            try:
                WhitelistPhoto.objects.create(
                    person=whitelist_entry,
                    image=image,
                    uploaded_by=request.user
                )
                uploaded_count += 1
            except Exception as e:
                messages.error(request, f'Failed to upload {image.name}: {str(e)}')

        if uploaded_count > 0:
            messages.success(request, f'{uploaded_count} image(s) uploaded successfully!')
        else:
            messages.warning(request, 'No images were uploaded.')

        return redirect('whitelist_profile', pk=pk)

    return render(request, 'add_whitelist_images.html', {
        'whitelist_entry': whitelist_entry
    })

@login_required
def delete_whitelist_image(request, pk, image_id):
    """Delete specific image from whitelist entry"""
    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)
    image = get_object_or_404(WhitelistPhoto, id=image_id, person=whitelist_entry)

    # Check permissions
    if not (request.user == image.uploaded_by or
            request.user.role in ['admin', 'case_manager']):
        messages.error(request, 'You do not have permission to delete this image.')
        return redirect('whitelist_profile', pk=pk)

    if request.method == 'POST':
        try:
            image.delete()
            messages.success(request, 'Image deleted successfully.')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error deleting whitelist image {image_id}: {e}")
            messages.error(request, 'An error occurred while deleting the image.')

    return redirect('whitelist_profile', pk=pk)

@login_required
def approve_whitelist(request, pk):
    """Approve whitelist entry (admin/case_manager only)"""
    if request.user.role not in ['admin', 'case_manager']:
        messages.error(request, 'You do not have permission to approve whitelist entries.')
        return redirect('list_whitelist')

    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)

    if request.method == 'POST':
        whitelist_entry.approved_by = request.user
        whitelist_entry.status = 'active'
        whitelist_entry.save()

        messages.success(request, f'Whitelist entry for {whitelist_entry.person_name} has been approved.')
        return redirect('whitelist_profile', pk=pk)

    return render(request, 'approve_whitelist.html', {
        'whitelist_entry': whitelist_entry
    })

@login_required
def suspend_whitelist(request, pk):
    """Suspend whitelist entry (admin/case_manager only)"""
    if request.user.role not in ['admin', 'case_manager']:
        messages.error(request, 'You do not have permission to suspend whitelist entries.')
        return redirect('list_whitelist')

    whitelist_entry = get_object_or_404(Targets_whitelist, pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        whitelist_entry.status = 'suspended'
        whitelist_entry.person_text = f"SUSPENDED: {reason}\n\n{whitelist_entry.person_text or ''}"
        whitelist_entry.save()

        messages.success(request, f'Whitelist entry for {whitelist_entry.person_name} has been suspended.')
        return redirect('whitelist_profile', pk=pk)

    return render(request, 'suspend_whitelist.html', {
        'whitelist_entry': whitelist_entry
    })
