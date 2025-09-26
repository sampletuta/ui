# NOTE: The import below is required for Django models. If you see a linter error, ensure Django is installed and your environment is set up correctly.
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError
import uuid 
import json
import logging
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from backendapp.utils.notifications import notify

logger = logging.getLogger(__name__)

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
        ('case_manager', 'Case Manager'),
        ('operator', 'Operator'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLES, default='operator')
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
    
    # Note: Delete method is handled manually in the view to avoid conflicts
    # The view manually deletes related objects and then removes the target

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
            
            # Additional validation for face detection quality
            try:
                if hasattr(self.image, 'open'):
                    self.image.open()
                if hasattr(self.image, 'seek'):
                    self.image.seek(0)
                
                with Image.open(self.image) as img:
                    # Check image dimensions
                    width, height = img.size
                    if width < 100 or height < 100:
                        raise ValidationError(
                            'Image resolution is too low for reliable face detection. '
                            'Please use images with dimensions of at least 100x100 pixels.'
                        )
                    
                    # Check if image is too small for face detection
                    if width < 200 or height < 200:
                        from django.contrib import messages
                        # This is a warning, not an error - allow the upload but inform the user
                        pass
                        
            except Exception as e:
                # If we can't validate dimensions, just log it and continue
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not validate image dimensions for {self.image.name}: {e}")
                pass
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """
        Prevent deletion of the last image in a target.
        Use this for normal photo deletion by users.
        """
        # Check if this is the last image for the target
        if self.person.images.count() <= 1:
            raise ValidationError(
                f"Cannot delete the last image for target '{self.person.target_name}'. "
                "Each target must have at least one image."
            )
        
        # Proceed with deletion
        super().delete(*args, **kwargs)
    
    def force_delete(self, *args, **kwargs):
        """
        Force delete without validation.
        Use this when deleting the entire target (bypasses "last image" check).
        """
        super().delete(*args, **kwargs)
    
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
    
    # NEW: Deduplication tracking
    is_duplicate = models.BooleanField(default=False, help_text='Whether this detection is a duplicate')
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, help_text='Original detection if this is a duplicate')
    deduplication_reason = models.CharField(max_length=50, blank=True, help_text='Reason for deduplication: temporal, spatial, confidence, rate_limit')
    
    # NEW: Alert tracking
    alert_created = models.BooleanField(default=False, help_text='Whether an alert was created for this detection')
    alert_created_at = models.DateTimeField(null=True, blank=True, help_text='When the alert was created')
    
    # NEW: External detection tracking
    external_detection_id = models.CharField(max_length=100, blank=True, null=True, help_text='External detection service ID')
    detection_source = models.CharField(max_length=50, default='internal', help_text='Source of detection: internal, external, api')
    
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
            self._handle_detection_storage_and_alert()
    
    def _handle_detection_storage_and_alert(self):
        """Handle both storage deduplication and alert creation"""
        try:
            from .utils.enhanced_deduplication import enhanced_deduplication_service
            
            # Prepare detection data for deduplication
            detection_data = {
                'target_id': str(self.target.id),
                'timestamp': self.timestamp,
                'confidence': self.confidence,
                'bounding_box': self.bounding_box or {},
                'camera_id': self.camera_id,
                'user_id': str(self.search_query.user.id),
                'detection_id': str(self.id)
            }
            
            # Check storage deduplication (less strict - keep more history)
            storage_result = enhanced_deduplication_service.check_storage_deduplication(detection_data)
            
            if not storage_result['should_store']:
                # Mark as duplicate and link to original
                self.is_duplicate = True
                self.duplicate_of_id = storage_result['original_detection_id']
                self.deduplication_reason = storage_result['reason']
                self.save(update_fields=['is_duplicate', 'duplicate_of', 'deduplication_reason'])
                logger.info(f"Detection {self.id} marked as duplicate: {storage_result['reason']}")
                return
            
            # Check alert deduplication (stricter rules)
            alert_result = enhanced_deduplication_service.check_alert_deduplication(detection_data)
            
            if alert_result['should_alert']:
                self._create_alert()
                logger.info(f"Alert created for detection {self.id}")
            else:
                logger.info(f"Alert suppressed for detection {self.id}: {alert_result['reason']}")
                
        except Exception as e:
            logger.error(f"Error in detection handling: {e}")
            # Fallback: create alert without deduplication
            try:
                self._create_alert()
            except Exception:
                pass
    
    def _create_alert(self):
        """Create notification alert for this detection"""
        try:
            actor = self.search_query.user
            recipient = self.search_query.user
            
            description = f"Detection at {self.timestamp}s (conf {self.confidence:.2f})"
            if self.camera_name:
                description += f" - {self.camera_name}"
            
            notify(
                recipient=recipient,
                actor=actor,
                verb='detected',
                target=self.target,
                action_object=self,
                description=description
            )
            
            # Mark alert as created
            self.alert_created = True
            self.alert_created_at = timezone.now()
            self.save(update_fields=['alert_created', 'alert_created_at'])
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")

    def get_url_for_notifications(self, notification, request):
        from django.urls import reverse
        return reverse('search_results_advanced', kwargs={'search_id': self.search_query.id})

# Whitelist Models
class Targets_whitelist(models.Model):
    """Whitelist for trusted/authorized individuals"""
    ACCESS_LEVELS = [
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access'),
        ('admin', 'Administrative Access'),
        ('vip', 'VIP Access'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    GENDER = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person_name = models.CharField(max_length=100, help_text='Name of the authorized person')
    employee_id = models.CharField(max_length=50, blank=True, null=True, help_text='Employee ID or badge number')
    department = models.CharField(max_length=100, blank=True, null=True, help_text='Department or division')
    position = models.CharField(max_length=100, blank=True, null=True, help_text='Job position or title')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Contact information
    person_text = models.TextField(blank=True, null=True, help_text='Additional notes about the person')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Authorization details
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='standard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    gender = models.CharField(max_length=20, choices=GENDER, default='other')

    # Validity period
    valid_from = models.DateTimeField(blank=True, null=True, help_text='Access valid from this date')
    valid_until = models.DateTimeField(blank=True, null=True, help_text='Access expires on this date')

    # Security clearance
    clearance_level = models.CharField(max_length=50, blank=True, null=True, help_text='Security clearance level')
    authorized_areas = models.JSONField(default=list, blank=True, help_text='List of authorized areas/zones')

    # Audit fields
    created_by = models.ForeignKey(CustomUser, related_name='whitelist_created', on_delete=models.SET_NULL, null=True, blank=True)
    approved_by = models.ForeignKey(CustomUser, related_name='whitelist_approved', on_delete=models.SET_NULL, null=True, blank=True)
    last_verified = models.DateTimeField(blank=True, null=True, help_text='Last time access was verified')

    def __str__(self):
        return f"{self.person_name} ({self.employee_id or 'No ID'})"

    def is_active(self):
        """Check if the whitelist entry is currently active"""
        if self.status != 'active':
            return False
        if self.valid_from and self.valid_from > timezone.now():
            return False
        if self.valid_until and self.valid_until < timezone.now():
            return False
        return True

    def has_images(self):
        """Check if person has at least one image"""
        return self.images.exists()

    def get_primary_image(self):
        """Get the first image or return None"""
        return self.images.first()

    def get_image_count(self):
        """Get the total number of images"""
        return self.images.count()

    def get_absolute_url(self):
        return reverse('whitelist_profile', kwargs={'pk': self.id})

    class Meta:
        verbose_name = 'Whitelist Entry'
        verbose_name_plural = 'Whitelist Entries'
        ordering = ['-created_at']

class WhitelistPhoto(models.Model):
    """Photos for whitelist entries"""
    person = models.ForeignKey(Targets_whitelist, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='whitelist_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, related_name='whitelist_images', on_delete=models.CASCADE)

    # Image quality metadata
    face_confidence = models.FloatField(blank=True, null=True, help_text='Face detection confidence score')
    image_quality = models.CharField(max_length=20, blank=True, null=True, help_text='Image quality assessment')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo for {self.person.person_name} ({self.id})"

    def clean(self):
        """Validate image file"""
        if self.image:
            # Check file size (max 5MB)
            try:
                if getattr(self.image, 'size', 0) > 5 * 1024 * 1024:
                    raise ValidationError('Image file size must be under 5MB.')
            except Exception:
                pass

            # Validate that the file is an actual image
            try:
                if hasattr(self.image, 'open'):
                    self.image.open()
                if hasattr(self.image, 'seek'):
                    self.image.seek(0)
                with Image.open(self.image) as img:
                    img.verify()
                if hasattr(self.image, 'seek'):
                    self.image.seek(0)
            except (UnidentifiedImageError, OSError, ValueError) as _e:
                raise ValidationError('File must be an image.')

            # Additional validation for face detection quality
            try:
                if hasattr(self.image, 'open'):
                    self.image.open()
                if hasattr(self.image, 'seek'):
                    self.image.seek(0)

                with Image.open(self.image) as img:
                    width, height = img.size
                    if width < 100 or height < 100:
                        raise ValidationError('Image resolution is too low for reliable face detection.')

            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not validate image dimensions for {self.image.name}: {e}")
                pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the last image for a whitelist entry"""
        if self.person.images.count() <= 1:
            raise ValidationError(
                f"Cannot delete the last image for '{self.person.person_name}'. "
                "Each whitelist entry must have at least one image."
            )
        super().delete(*args, **kwargs)

    def force_delete(self, *args, **kwargs):
        """Force delete without validation"""
        super().delete(*args, **kwargs)

    def get_url_for_notifications(self, notification, request):
        from django.urls import reverse
        return reverse('whitelist_profile', kwargs={'pk': self.person.id})

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
        
        