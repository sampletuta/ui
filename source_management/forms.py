from django import forms
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import CameraSource, FileSource, StreamSource
import os

User = get_user_model()

class CameraSourceForm(forms.ModelForm):
    """Form for creating/editing camera sources"""
    
    class Meta:
        model = CameraSource
        fields = [
            'name', 'description', 'location', 'zone',
            'latitude', 'longitude', 'is_active',
            'camera_ip', 'camera_port', 'camera_username', 'camera_password',
            'camera_protocol', 'camera_type', 'camera_resolution', 'camera_fps',
            'configuration', 'tags'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Front Door Camera'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Building A, Floor 1'}),
            'zone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Zone A'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., 40.7128'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., -74.0060'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'camera_ip': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 192.168.1.100'}),
            'camera_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 554'}),
            'camera_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., admin'}),
            'camera_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter camera password'}),
            'camera_protocol': forms.Select(attrs={'class': 'form-select'}),
            'camera_type': forms.Select(attrs={'class': 'form-select'}),
            'camera_resolution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1920x1080'}),
            'camera_fps': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30'}),
            'configuration': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
            'tags': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '["tag1", "tag2"]'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['name'].help_text = 'Display name for this camera (e.g., Front Door Camera)'
        self.fields['description'].help_text = 'Optional description of this camera'
        self.fields['location'].help_text = 'Physical location of the camera'
        self.fields['zone'].help_text = 'Zone name for organization'
        self.fields['latitude'].help_text = 'GPS latitude coordinate'
        self.fields['longitude'].help_text = 'GPS longitude coordinate'
        self.fields['camera_ip'].help_text = 'IP address of the camera (e.g., 192.168.1.100)'
        self.fields['camera_port'].help_text = 'Port number for camera connection (default: 554 for RTSP)'
        self.fields['camera_username'].help_text = 'Username for camera authentication (if required)'
        self.fields['camera_password'].help_text = 'Password for camera authentication (if required)'
        self.fields['camera_protocol'].help_text = 'Protocol used to connect to the camera'
        self.fields['camera_type'].help_text = 'Type of camera hardware'
        self.fields['camera_resolution'].help_text = 'Camera resolution (e.g., 1920x1080, 1280x720)'
        self.fields['camera_fps'].help_text = 'Frame rate in frames per second'
        self.fields['configuration'].help_text = 'Additional configuration as JSON (optional)'
        self.fields['tags'].help_text = 'Tags for categorization as JSON array (optional)'
    
    def clean_camera_ip(self):
        ip = self.cleaned_data['camera_ip']
        if ip:
            # Basic IP validation
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                raise forms.ValidationError('Please enter a valid IP address (e.g., 192.168.1.100)')
            
            # Check each octet
            octets = ip.split('.')
            for octet in octets:
                if not (0 <= int(octet) <= 255):
                    raise forms.ValidationError('IP address octets must be between 0 and 255')
        
        return ip
    
    def clean_camera_port(self):
        port = self.cleaned_data['camera_port']
        if port:
            if not (1 <= port <= 65535):
                raise forms.ValidationError('Port must be between 1 and 65535')
        return port
    
    def clean_camera_fps(self):
        fps = self.cleaned_data['camera_fps']
        if fps:
            if not (1 <= fps <= 120):
                raise forms.ValidationError('Frame rate must be between 1 and 120 FPS')
        return fps
    
    def clean_configuration(self):
        config = self.cleaned_data['configuration']
        if config:
            try:
                if isinstance(config, str):
                    import json
                    json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError('Configuration must be valid JSON')
        return config
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        if tags:
            try:
                if isinstance(tags, str):
                    import json
                    parsed_tags = json.loads(tags)
                    if not isinstance(parsed_tags, list):
                        raise forms.ValidationError('Tags must be a JSON array')
            except json.JSONDecodeError:
                raise forms.ValidationError('Tags must be valid JSON array')
        return tags

class FileSourceForm(forms.ModelForm):
    """Form for creating/editing file sources"""
    
    class Meta:
        model = FileSource
        fields = [
            'name', 'description', 'location',
            'latitude', 'longitude',
            'video_file', 'tags'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Security Footage'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Building A, Floor 1'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., 40.7128'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., -74.0060'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'tags': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '["tag1", "tag2"]'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow chunked uploads by not requiring the file at field level
        if 'video_file' in self.fields:
            self.fields['video_file'].required = False
        
        # Add help text
        self.fields['name'].help_text = 'Display name for this file (e.g., Security Footage)'
        self.fields['description'].help_text = 'Optional description of this file'
        self.fields['location'].help_text = 'Physical location where this file was recorded'
        self.fields['latitude'].help_text = 'GPS latitude coordinate where file was recorded'
        self.fields['longitude'].help_text = 'GPS longitude coordinate where file was recorded'
        self.fields['video_file'].help_text = 'Select a video file to upload (MP4, AVI, MOV, etc.)'
        self.fields['tags'].help_text = 'Tags for categorization as JSON array (optional)'
    
    def clean(self):
        cleaned = super().clean()
        video_file = cleaned.get('video_file')
        # Ensure we read POST for hidden fields regardless of cleaned_data
        chunked_upload_id = (self.data.get('chunked_upload_id') or
                              cleaned.get('chunked_upload_id'))
        chunked_original_filename = (self.data.get('chunked_original_filename') or
                                      cleaned.get('chunked_original_filename'))

        # Allow either direct file upload or chunked upload metadata
        if not video_file and not (chunked_upload_id and chunked_original_filename):
            # Point error to the file field so the UI shows where to act
            self.add_error('video_file', 'This field is required. Either select a file or complete the chunked upload.')
            return cleaned

        # If direct file provided, validate size and extension
        if video_file:
            max_size = getattr(settings, 'MAX_VIDEO_FILE_SIZE', 500 * 1024 * 1024)
            max_size_mb = max_size // (1024 * 1024)
            if video_file.size > max_size:
                raise forms.ValidationError(f'File size must be less than {max_size_mb}MB.')

            allowed_extensions = getattr(settings, 'ALLOWED_VIDEO_EXTENSIONS', ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'])
            file_extension = os.path.splitext(video_file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(f'File type not supported. Allowed: {", ".join(allowed_extensions)}')

        # Surface hidden field values into cleaned data for the view
        cleaned['chunked_upload_id'] = chunked_upload_id
        cleaned['chunked_original_filename'] = chunked_original_filename
        return cleaned
    
    def clean_configuration(self):
        config = self.cleaned_data['configuration']
        if config:
            try:
                if isinstance(config, str):
                    import json
                    json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError('Configuration must be valid JSON')
        return config
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        if tags:
            try:
                if isinstance(tags, str):
                    import json
                    parsed_tags = json.loads(tags)
                    if not isinstance(parsed_tags, list):
                        raise forms.ValidationError('Tags must be a JSON array')
            except json.JSONDecodeError:
                raise forms.ValidationError('Tags must be valid JSON array')
        return tags

class StreamSourceForm(forms.ModelForm):
    """Form for creating/editing stream sources"""
    
    class Meta:
        model = StreamSource
        fields = [
            'name', 'description', 'location',
            'latitude', 'longitude',
            'stream_url', 'stream_protocol', 'stream_quality', 'stream_parameters',
            'tags'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Live Stream'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Building A, Floor 1'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., 40.7128'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., -74.0060'}),
            'stream_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'e.g., rtsp://192.168.1.100:554/stream'}),
            'stream_protocol': forms.Select(attrs={'class': 'form-select'}),
            'stream_quality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1080p, 720p'}),
            'stream_parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
            'tags': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '["tag1", "tag2"]'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['name'].help_text = 'Display name for this stream (e.g., Live Stream)'
        self.fields['description'].help_text = 'Optional description of this stream'
        self.fields['location'].help_text = 'Physical location of the stream source'
        self.fields['latitude'].help_text = 'GPS latitude coordinate'
        self.fields['longitude'].help_text = 'GPS longitude coordinate'
        self.fields['stream_url'].help_text = 'URL of the video stream'
        self.fields['stream_protocol'].help_text = 'Protocol of the stream'
        self.fields['stream_quality'].help_text = 'Stream quality (e.g., 1080p, 720p)'
        self.fields['stream_parameters'].help_text = 'Additional stream parameters as JSON'
        self.fields['tags'].help_text = 'Tags for categorization as JSON array (optional)'
    
    def clean_stream_parameters(self):
        params = self.cleaned_data['stream_parameters']
        if params:
            try:
                if isinstance(params, str):
                    import json
                    json.loads(params)
            except json.JSONDecodeError:
                raise forms.ValidationError('Stream parameters must be valid JSON')
        return params
    
    def clean_configuration(self):
        config = self.cleaned_data['configuration']
        if config:
            try:
                if isinstance(config, str):
                    import json
                    json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError('Configuration must be valid JSON')
        return config
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        if tags:
            try:
                if isinstance(tags, str):
                    import json
                    parsed_tags = json.loads(tags)
                    if not isinstance(parsed_tags, list):
                        raise forms.ValidationError('Tags must be a JSON array')
            except json.JSONDecodeError:
                raise forms.ValidationError('Tags must be valid JSON array')
        return tags 

class VideoProcessingForm(forms.Form):
    """Form for configuring video processing parameters"""
    
    RESOLUTION_CHOICES = [
        ('640x480', '640x480 (VGA)'),
        ('1280x720', '1280x720 (HD)'),
        ('1920x1080', '1920x1080 (Full HD)'),
        ('2560x1440', '2560x1440 (2K)'),
        ('3840x2160', '3840x2160 (4K)'),
        ('custom', 'Custom Resolution'),
    ]
    
    target_fps = forms.IntegerField(
        min_value=1,
        max_value=120,
        initial=5,
        help_text="Target frame rate (1-120 FPS)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 5',
            'min': '1',
            'max': '120'
        })
    )
    
    target_resolution = forms.ChoiceField(
        choices=RESOLUTION_CHOICES,
        initial='640x480',
        help_text="Target resolution for the processed video",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'target_resolution'
        })
    )
    
    custom_resolution = forms.CharField(
        max_length=20,
        required=False,
        help_text="Custom resolution in format 'widthxheight' (e.g., 800x600)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 800x600',
            'style': 'display: none;'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['target_fps'].help_text = 'Target frame rate for the processed video (1-120 FPS)'
        self.fields['target_resolution'].help_text = 'Target resolution for the processed video'
        self.fields['custom_resolution'].help_text = 'Custom resolution in format "widthxheight" (e.g., 800x600)'
    
    def clean(self):
        cleaned_data = super().clean()
        target_resolution = cleaned_data.get('target_resolution')
        custom_resolution = cleaned_data.get('custom_resolution')
        
        # If custom resolution is selected, validate the custom_resolution field
        if target_resolution == 'custom':
            if not custom_resolution:
                self.add_error('custom_resolution', 'Custom resolution is required when "Custom Resolution" is selected')
            else:
                # Validate custom resolution format
                import re
                if not re.match(r'^\d+x\d+$', custom_resolution):
                    self.add_error('custom_resolution', 'Custom resolution must be in format "widthxheight" (e.g., 800x600)')
                else:
                    # Extract width and height
                    width, height = custom_resolution.split('x')
                    if not (1 <= int(width) <= 7680) or not (1 <= int(height) <= 4320):
                        self.add_error('custom_resolution', 'Resolution dimensions must be between 1x1 and 7680x4320')
        
        return cleaned_data
    
    def get_final_resolution(self):
        """Get the final resolution value (either from choice or custom)"""
        target_resolution = self.cleaned_data.get('target_resolution')
        if target_resolution == 'custom':
            return self.cleaned_data.get('custom_resolution')
        return target_resolution 