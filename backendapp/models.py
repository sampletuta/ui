# NOTE: The import below is required for Django models. If you see a linter error, ensure Django is installed and your environment is set up correctly.
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError
import uuid 
import json
from django.conf import settings
from django.urls import reverse
from notifications.signals import notify

# Create your models here.
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLES, default='user')
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    # Security fields for login attempts
    login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
    
    def get_short_name(self):
        return self.first_name or self.email

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('profile')

class Case(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, related_name='cases', on_delete=models.CASCADE)

    def __str__(self):
        return self.case_name

    def get_absolute_url(self):
        return reverse('case_detail', kwargs={'pk': self.id})

class Targets_watchlist(models.Model):
    CASE_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('archived', 'Archived'),
    ]
    GENDER = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, related_name='targets_watchlist', on_delete=models.CASCADE)
    target_name = models.CharField(max_length=100,help_text='Name of the target')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    target_text = models.TextField(blank=True, null=True)
    target_url = models.URLField(blank=True, null=True)
    target_email = models.EmailField(blank=True, null=True)
    target_phone = models.CharField(max_length=100, blank=True, null=True)
    case_status = models.CharField(max_length=100, choices=CASE_STATUS, default='active')
    gender = models.CharField(max_length=100, choices=GENDER, default='male')
    created_by = models.ForeignKey(CustomUser, related_name='targets_watchlist', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.target_name
    
    def has_images(self):
        """Check if target has at least one image"""
        return self.images.exists()
    
    def get_primary_image(self):
        """Get the first image or return None"""
        return self.images.first()
    
    def get_image_count(self):
        """Get the total number of images"""
        return self.images.count()

    def get_absolute_url(self):
        return reverse('target_profile', kwargs={'pk': self.id})

class TargetPhoto(models.Model):
    person = models.ForeignKey(Targets_watchlist, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='target_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, related_name='uploaded_images', on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Image for {self.person.target_name} ({self.id})"
    
    def clean(self):
        """Validate image file"""
        if self.image:
            # Check file size (max 5MB)
            try:
                if getattr(self.image, 'size', 0) > 5 * 1024 * 1024:
                    raise ValidationError('Image file size must be under 5MB.')
            except Exception:
                # If size cannot be determined, skip size check
                pass

            # Validate that the file is an actual image
            # Prefer content_type when available (e.g., on UploadedFile)
            content_type = ''
            try:
                content_type = getattr(getattr(self.image, 'file', None), 'content_type', '') or ''
            except Exception:
                content_type = ''

            if not content_type.startswith('image/'):
                # Fallback: try to open with Pillow
                try:
                    if hasattr(self.image, 'open'):
                        self.image.open()
                    # Ensure file pointer at start
                    if hasattr(self.image, 'seek'):
                        self.image.seek(0)
                    with Image.open(self.image) as img:
                        img.verify()
                    # Reset pointer after verify
                    if hasattr(self.image, 'seek'):
                        self.image.seek(0)
                except (UnidentifiedImageError, OSError, ValueError) as _e:
                    raise ValidationError('File must be an image.')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_url_for_notifications(self, notification, request):
        from django.urls import reverse
        return reverse('target_profile', kwargs={'pk': self.person.id})
        
# New Advanced Search Models
class SearchQuery(models.Model):
    SEARCH_TYPES = [
        ('face', 'Face Search'),
        ('license_plate', 'License Plate Search'),
        ('object', 'Object Detection'),
        ('behavior', 'Behavior Analysis'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='search_queries')
    search_type = models.CharField(max_length=20, choices=SEARCH_TYPES, default='face')
    query_name = models.CharField(max_length=200, help_text='Name for this search query')
    description = models.TextField(blank=True, null=True)
    
    # Date Range Filtering
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    
    # Geospatial Search (using JSON fields for coordinates)
    latitude = models.FloatField(blank=True, null=True, help_text='Center latitude for geospatial search')
    longitude = models.FloatField(blank=True, null=True, help_text='Center longitude for geospatial search')
    radius_km = models.FloatField(default=5.0, help_text='Search radius in kilometers')
    
    # Confidence Threshold
    confidence_threshold = models.FloatField(default=0.7, help_text='Minimum confidence score (0.0-1.0)')
    
    # Target Filters
    target_filters = models.JSONField(default=dict, blank=True, help_text='Additional target filters')
    
    # Milvus Integration
    milvus_collection = models.CharField(max_length=100, blank=True, null=True)
    milvus_partition = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.query_name} ({self.search_type}) by {self.user.email}"
    
    def get_location_point(self):
        """Return coordinates as a tuple for Folium"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None

    def get_absolute_url(self):
        return reverse('search_results_advanced', kwargs={'search_id': self.id})

class SearchResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name='results')
    target = models.ForeignKey(Targets_watchlist, on_delete=models.CASCADE, related_name='search_results')
    
    # Detection Details
    timestamp = models.FloatField(help_text='Timestamp in seconds')
    confidence = models.FloatField(help_text='Detection confidence score')
    bounding_box = models.JSONField(blank=True, null=True, help_text='Bounding box as JSON: {x, y, w, h}')
    
    # Geospatial Data (using JSON for coordinates)
    latitude = models.FloatField(blank=True, null=True, help_text='Detection latitude')
    longitude = models.FloatField(blank=True, null=True, help_text='Detection longitude')
    camera_id = models.CharField(max_length=100, blank=True, null=True)
    camera_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Media Files
    face_image = models.ImageField(upload_to='detected_faces/', blank=True, null=True)
    source_video_url = models.URLField(blank=True, null=True)
    source_video_timestamp = models.FloatField(blank=True, null=True)
    
    # Milvus Data
    milvus_vector_id = models.CharField(max_length=100, blank=True, null=True)
    milvus_distance = models.FloatField(blank=True, null=True, help_text='Distance from query vector')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Result for {self.target.target_name} at {self.timestamp}s (conf: {self.confidence})"
    
    def get_location_point(self):
        """Return coordinates as a tuple for Folium"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            try:
                actor = self.search_query.user
                recipient = self.search_query.user
                notify.send(
                    actor,
                    recipient=recipient,
                    verb='detected',
                    target=self.target,
                    action_object=self,
                    description=f"Detection at {self.timestamp}s (conf {self.confidence:.2f})"
                )
            except Exception:
                # Silently ignore notification failures to avoid blocking saves
                pass

    def get_url_for_notifications(self, notification, request):
        from django.urls import reverse
        return reverse('search_results_advanced', kwargs={'search_id': self.search_query.id})

# Legacy models for backward compatibility
class SearchHistory(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='search_histories')
    video_file = models.FileField(upload_to='search_videos/')
    target_list = models.ForeignKey(Targets_watchlist, on_delete=models.CASCADE, related_name='search_histories')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    result_summary = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Search {self.id} by {self.user} on {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
    