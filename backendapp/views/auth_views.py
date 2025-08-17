"""
Authentication Views Module
Handles user login, logout, signup, and profile management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging

from ..forms import (
    LoginForm,
    CustomUserCreationForm,
    CustomPasswordChangeForm,
    AdminUserChangeForm,
    SelfUserChangeForm,
)
from ..models import CustomUser

logger = logging.getLogger(__name__)

def login(request):
    """User login view"""
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
                response = redirect('dashboard')
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
                    auth_login(request, user)
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

@login_required
def logout_view(request):
    """Logout view"""
    auth_logout(request)
    return redirect('login')

def logout(request):
    """Custom logout view"""
    auth_logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

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
def profile(request):
    """User profile view"""
    return render(request, 'profile.html', {'user': request.user})

@login_required
def settings_view(request):
    """User settings view for password change"""
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

# Helper functions for authentication
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
