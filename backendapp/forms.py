from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from .models import Targets_watchlist, TargetPhoto, Case, SearchQuery

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
        fields = ('email', 'first_name', 'last_name', 'role')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
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
    collection_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Milvus collection name'
        })
    )
    
    partition_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Partition name (optional)'
        })
    )
    
    top_k = forms.IntegerField(
        initial=10,
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '1000'
        })
    )
    
    distance_threshold = forms.FloatField(
        initial=0.8,
        min_value=0.0,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0.0',
            'max': '1.0',
            'step': '0.01'
        })
    ) 

class CaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ['case_name', 'description']
        widgets = {
            'case_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        } 