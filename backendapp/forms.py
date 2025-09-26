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

# Base form class with unified styling
class BaseForm(forms.Form):
    """Base form class with unified styling for all forms"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_unified_styling()
    
    def apply_unified_styling(self):
        """Apply unified styling to all form fields"""
        for field_name, field in self.fields.items():
            # Apply base classes
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or ''
                })
            elif isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'Email address'
                })
            elif isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'Password'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': field.label or ''
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select'
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'form-check-input'
                })
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'accept': 'image/*' if 'image' in field_name.lower() else '*'
                })
            elif isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'datetime-local'
                })
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'date'
                })
            elif isinstance(field.widget, forms.TimeInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'time'
                })
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'number'
                })
            elif isinstance(field.widget, forms.URLInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'URL'
                })
            elif isinstance(field.widget, forms.TelephoneInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'Phone number'
                })
            
            # Add help text styling
            if field.help_text:
                field.help_text = f'<small class="form-text text-muted">{field.help_text}</small>'

class BaseModelForm(forms.ModelForm):
    """Base model form class with unified styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_unified_styling()
    
    def apply_unified_styling(self):
        """Apply unified styling to all form fields"""
        for field_name, field in self.fields.items():
            # Apply base classes
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or ''
                })
            elif isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'Email address'
                })
            elif isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'Password'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': field.label or ''
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select'
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'form-check-input'
                })
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'accept': 'image/*' if 'image' in field_name.lower() else '*'
                })
            elif isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'datetime-local'
                })
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'date'
                })
            elif isinstance(field.widget, forms.TimeInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'time'
                })
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'number'
                })
            elif isinstance(field.widget, forms.URLInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'URL'
                })
            elif isinstance(field.widget, forms.TelephoneInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or 'Phone number'
                })
            
            # Add help text styling
            if field.help_text:
                field.help_text = f'<small class="form-text text-muted">{field.help_text}</small>'

class CustomUserCreationForm(BaseModelForm, UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

class CustomUserChangeForm(BaseModelForm, UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'avatar', 'is_active', 'is_staff', 'is_superuser')

class AdminUserCreationForm(BaseModelForm, UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'role', 'avatar',
            'password1', 'password2',
            'is_active', 'is_staff', 'is_superuser',
        )

class AdminUserChangeForm(BaseModelForm, UserChangeForm):
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'role', 'avatar',
            'is_active', 'is_staff', 'is_superuser',
        )

class SelfUserChangeForm(BaseModelForm, UserChangeForm):
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'avatar',
        )

class LoginForm(BaseForm):
    """Login form for user authentication"""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'id': 'id_email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'id_password'
        })
    )

class CustomPasswordChangeForm(BaseForm, PasswordChangeForm):
    pass

# Multiple file input widget
class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleImageInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

    def to_python(self, data):
        if data is None:
            return None
        elif isinstance(data, (list, tuple)):
            return [super().to_python(item) for item in data]
        else:
            return super().to_python(data)

    def validate(self, data):
        # data is a list after to_python
        if self.required and not data:
            raise forms.ValidationError(self.error_messages['required'], code='required')

class TargetsWatchlistForm(BaseModelForm):
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

    def clean_images(self):
        # Prefer cleaned_data so our MultipleFileField normalization applies
        images = self.cleaned_data.get('images', [])
        if not images:
            raise forms.ValidationError('At least one image is required.')
        
        # Validate each image
        for image in images:
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError(f'Image {image.name} is too large. Maximum size is 5MB.')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                raise forms.ValidationError(f'Image {image.name} has an unsupported format. Please use JPEG, PNG, GIF, or WebP.')
        
        return images

class CaseForm(BaseModelForm):
    class Meta:
        model = Case
        fields = ['case_name', 'description']

class WhitelistForm(BaseModelForm):
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

    def clean_images(self):
        # Prefer cleaned_data so our MultipleFileField normalization applies
        images = self.cleaned_data.get('images', [])
        if not images:
            raise forms.ValidationError('At least one image is required.')
        
        # Validate each image
        for image in images:
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError(f'Image {image.name} is too large. Maximum size is 5MB.')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                raise forms.ValidationError(f'Image {image.name} has an unsupported format. Please use JPEG, PNG, GIF, or WebP.')
        
        return images

class SearchForm(BaseForm):
    query = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter search query...'
        })
    )
    case = forms.ModelChoiceField(
        queryset=Case.objects.all(),
        required=False,
        empty_label="All Cases",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AdvancedSearchForm(BaseForm):
    query = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter search query...'
        })
    )
    case = forms.ModelChoiceField(
        queryset=Case.objects.all(),
        required=False,
        empty_label="All Cases",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    gender = forms.ChoiceField(
        choices=[('', 'All Genders')] + GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    case_status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + [
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('closed', 'Closed'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )