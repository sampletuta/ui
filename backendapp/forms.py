from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from .models import Targets_watchlist, TargetPhoto, Case, SearchQuery, Targets_whitelist, WhitelistPhoto

User = get_user_model()

# Define choices here to avoid circular imports
GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
]

# Define choices here to avoid circular imports
GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
]

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'avatar', 'is_active', 'is_staff', 'is_superuser')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Last name'}),
            'role': forms.Select(attrs={'class': 'form-select bg-dark text-white border-0'}),
        }

class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'role', 'avatar',
            'password1', 'password2',
            'is_active', 'is_staff', 'is_superuser',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Last name'}),
            'role': forms.Select(attrs={'class': 'form-select bg-dark text-white border-0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'role', 'avatar',
            'is_active', 'is_staff', 'is_superuser',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Last name'}),
            'role': forms.Select(attrs={'class': 'form-select bg-dark text-white border-0'}),
        }

class SelfUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'avatar',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-0', 'placeholder': 'Last name'}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class MultipleImageInput(forms.ClearableFileInput):
    # Ensure Django accepts multiple files from this single input
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """A FileField that accepts multiple files and returns a list of files."""

    def to_python(self, data):
        # Normalize to list
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [f for f in data if f]
        return [data]

    def validate(self, data):
        # data is a list after to_python
        if self.required and not data:
            raise forms.ValidationError(self.error_messages['required'], code='required')


class TargetsWatchlistForm(forms.ModelForm):
    images = MultipleFileField(
        widget=MultipleImageInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True,
        }),
        required=False,
        help_text='Upload one or more images of the target (required for new targets)'
    )

    class Meta:
        model = Targets_watchlist
        fields = [
            'case', 'target_name', 'target_text', 'target_url', 'target_email', 'target_phone', 'case_status', 'gender'
        ]
        widgets = {
            'case': forms.Select(attrs={'class': 'form-select'}),
            'target_name': forms.TextInput(attrs={'class': 'form-control'}),
            'target_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'target_url': forms.URLInput(attrs={'class': 'form-control'}),
            'target_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'target_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'case_status': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_images(self):
        # Prefer cleaned_data so our MultipleFileField normalization applies
        images = self.cleaned_data.get('images') or []
        has_uploaded = any(getattr(img, 'name', None) for img in images)

        # Determine if we must require at least one image
        is_new = not getattr(self.instance, 'pk', None)
        has_existing = False
        try:
            has_existing = (not is_new) and hasattr(self.instance, 'images') and self.instance.images.exists()
        except Exception:
            has_existing = False

        if not has_uploaded and not has_existing:
            raise forms.ValidationError('At least one image is required for the target.')

        for image in images:
            if image and getattr(image, 'name', None):
                if not getattr(image, 'content_type', '').startswith('image/'):
                    raise forms.ValidationError(f'{image.name} is not a valid image file.')
                if getattr(image, 'size', 0) > 5 * 1024 * 1024:
                    raise forms.ValidationError(f'{image.name} is too large. Maximum size is 5MB.')

        return images

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'}))

# Advanced Search Forms
class AdvancedSearchForm(forms.ModelForm):
    # Target selection
    targets = forms.ModelMultipleChoiceField(
        queryset=Targets_watchlist.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select specific targets to search for'
    )
    
    # Additional filters
    gender_filter = forms.ChoiceField(
        choices=[('', 'Any Gender')] + GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    case_filter = forms.ModelChoiceField(
        queryset=Case.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Filter by specific case'
    )
    
    class Meta:
        model = SearchQuery
        fields = [
            'search_type', 'query_name', 'description', 'confidence_threshold',
            'radius_km', 'start_date', 'end_date', 'latitude', 'longitude'
        ]
        widgets = {
            'search_type': forms.Select(attrs={'class': 'form-select'}),
            'query_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter search name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Search description'}),
            'confidence_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.0',
                'max': '1.0',
                'step': '0.1'
            }),
            'radius_km': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.1',
                'max': '100.0',
                'step': '0.1'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Latitude',
                'step': 'any'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Longitude',
                'step': 'any'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

class QuickSearchForm(forms.Form):
    SEARCH_TYPES = [
        ('face', 'Face Search'),
        ('license_plate', 'License Plate'),
        ('object', 'Object Detection'),
    ]
    
    search_type = forms.ChoiceField(
        choices=SEARCH_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    query_text = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter search query...'
        })
    )
    
    confidence_threshold = forms.FloatField(
        initial=0.7,
        min_value=0.0,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0.0',
            'max': '1.0',
            'step': '0.1'
        })
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ('1h', 'Last Hour'),
            ('24h', 'Last 24 Hours'),
            ('7d', 'Last 7 Days'),
            ('30d', 'Last 30 Days'),
            ('custom', 'Custom Range'),
        ],
        initial='24h',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class MilvusSearchForm(forms.Form):
    face_image = forms.ImageField(
        label="Upload Face Image",
        help_text="Upload an image containing a face to search for similar faces",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'face_image'
        })
    )
    
    top_k = forms.IntegerField(
        label="Number of Results",
        initial=5,
        min_value=1,
        max_value=20,
        help_text="Maximum number of similar faces to return",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '20'
        })
    )
    
    confidence_threshold = forms.FloatField(
        label="Confidence Threshold",
        initial=0.6,
        min_value=0.0,
        max_value=1.0,
        help_text="Minimum similarity score to include in results",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0.0',
            'max': '1.0',
            'step': '0.1'
        })
    )
    
    apply_rerank = forms.BooleanField(
        label="Apply Re-ranking",
        required=False,
        initial=True,
        help_text="Enable query-time re-ranking (embedding + metadata boosts).",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class CaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ['case_name', 'description']
        widgets = {
            'case_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class WhitelistForm(forms.ModelForm):
    images = MultipleFileField(
        widget=MultipleImageInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True,
        }),
        required=False,
        help_text='Upload one or more images of the authorized person (required for new entries)'
    )

    class Meta:
        model = Targets_whitelist
        fields = [
            'person_name', 'employee_id', 'department', 'position',
            'person_text', 'email', 'phone', 'address',
            'access_level', 'status', 'gender',
            'valid_from', 'valid_until',
            'clearance_level', 'authorized_areas'
        ]
        widgets = {
            'person_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'person_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'access_level': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'clearance_level': forms.TextInput(attrs={'class': 'form-control'}),
            'authorized_areas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Enter authorized areas as comma-separated values'}),
        }

    def clean_images(self):
        """Validate uploaded images"""
        images = self.cleaned_data.get('images') or []
        has_uploaded = any(getattr(img, 'name', None) for img in images)

        # Determine if we must require at least one image
        is_new = not getattr(self.instance, 'pk', None)
        has_existing = False
        try:
            has_existing = (not is_new) and hasattr(self.instance, 'images') and self.instance.images.exists()
        except Exception:
            has_existing = False

        if not has_uploaded and not has_existing:
            raise forms.ValidationError('At least one image is required for the whitelist entry.')

        for image in images:
            if image and getattr(image, 'name', None):
                if not getattr(image, 'content_type', '').startswith('image/'):
                    raise forms.ValidationError(f'{image.name} is not a valid image file.')
                if getattr(image, 'size', 0) > 5 * 1024 * 1024:
                    raise forms.ValidationError(f'{image.name} is too large. Maximum size is 5MB.')

        return images

    def clean_authorized_areas(self):
        """Convert authorized_areas textarea to JSON-compatible list"""
        areas_text = self.cleaned_data.get('authorized_areas', '')
        if areas_text and areas_text.strip():
            # Split by comma and clean up whitespace
            areas = [area.strip() for area in areas_text.split(',') if area.strip()]
            return areas
        return []

    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')

        # Validate date range
        if valid_from and valid_until and valid_from >= valid_until:
            raise forms.ValidationError('Valid until date must be after valid from date.')

        return cleaned_data 