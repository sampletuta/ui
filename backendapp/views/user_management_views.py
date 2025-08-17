"""
User Management Views Module
Handles user creation, editing, deletion, and profile management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
import logging

from ..forms import AdminUserCreationForm, AdminUserChangeForm, SelfUserChangeForm
from ..models import CustomUser, Case, SearchQuery, Targets_watchlist
from notifications.models import Notification
from .utils import is_staff_or_admin

logger = logging.getLogger(__name__)

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
