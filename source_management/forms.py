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
            'camera_protocol', 'camera_type', 'camera_resolution', 
            'camera_resolution_width', 'camera_resolution_height', 'camera_fps', 'camera_bitrate', 'camera_codec',
            'camera_audio_enabled', 'camera_audio_codec', 'camera_audio_channels', 'camera_audio_sample_rate',
            'camera_buffer_size', 'camera_timeout', 'camera_keepalive', 'camera_retry_attempts',
            'configuration', 'tags', 'topic_suffix'
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
            'camera_resolution_width': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1920'}),
            'camera_resolution_height': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1080'}),
            'camera_fps': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30'}),
            'camera_bitrate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2000000'}),
            'camera_codec': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., h264, h265, mjpeg'}),
            'camera_audio_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'camera_audio_codec': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., aac, pcm, g711'}),
            'camera_audio_channels': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1, 2'}),
            'camera_audio_sample_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8000, 16000, 44100'}),
            'camera_buffer_size': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1000'}),
            'camera_timeout': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30'}),
            'camera_keepalive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'camera_retry_attempts': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 3'}),
            'configuration': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
            'tags': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '["tag1", "tag2"]'}),
            'topic_suffix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., front, back, main (max 6 chars, no spaces)'}),
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
        self.fields['camera_resolution_width'].help_text = 'Camera width in pixels'
        self.fields['camera_resolution_height'].help_text = 'Camera height in pixels'
        self.fields['camera_fps'].help_text = 'Frame rate in frames per second'
        self.fields['camera_bitrate'].help_text = 'Camera bitrate in bits per second'
        self.fields['camera_codec'].help_text = 'Video codec used by the camera'
        self.fields['camera_audio_enabled'].help_text = 'Whether the camera has audio capability'
        self.fields['camera_audio_codec'].help_text = 'Audio codec used by the camera'
        self.fields['camera_audio_channels'].help_text = 'Number of audio channels'
        self.fields['camera_audio_sample_rate'].help_text = 'Audio sample rate in Hz'
        self.fields['camera_buffer_size'].help_text = 'Buffer size in milliseconds'
        self.fields['camera_timeout'].help_text = 'Connection timeout in seconds'
        self.fields['camera_keepalive'].help_text = 'Whether to use keepalive connections'
        self.fields['camera_retry_attempts'].help_text = 'Number of retry attempts on failure'
        self.fields['configuration'].help_text = 'Additional configuration as JSON (optional)'
        self.fields['tags'].help_text = 'Tags for categorization as JSON array (optional)'
        self.fields['topic_suffix'].help_text = 'Suffix to add to the MQTT topic for this camera (e.g., /camera/front_door)'
    
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
    
    def clean_topic_suffix(self):
        """Clean and validate topic suffix"""
        suffix = self.cleaned_data.get('topic_suffix', '').strip()
        if suffix:
            # Remove spaces and limit to 6 characters
            clean_suffix = suffix.replace(' ', '')[:6]
            if len(clean_suffix) < len(suffix.replace(' ', '')):
                raise forms.ValidationError('Topic suffix cannot contain spaces')
            if len(clean_suffix) > 6:
                raise forms.ValidationError('Topic suffix cannot exceed 6 characters')
            return clean_suffix
        return suffix
    
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
    
    # Add proper authentication fields instead of JSON
    stream_auth_username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g., admin'
        }),
        help_text='Username for stream authentication (if required)'
    )
    
    stream_auth_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter stream password'
        }),
        help_text='Password for stream authentication (if required)'
    )
    
    stream_auth_api_key = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g., sk-1234567890abcdef'
        }),
        help_text='API key for stream authentication (if required)'
    )
    
    stream_auth_token = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g., Bearer token123'
        }),
        help_text='Bearer token for stream authentication (if required)'
    )
    
    class Meta:
        model = StreamSource
        fields = [
            'name', 'description', 'location', 'zone',
            'latitude', 'longitude',
            'stream_url', 'stream_protocol', 'stream_quality', 
            'stream_resolution_width', 'stream_resolution_height', 'stream_fps', 'stream_bitrate', 'stream_codec',
            'stream_audio_codec', 'stream_audio_channels', 'stream_audio_sample_rate', 'stream_audio_bitrate',
            'stream_buffer_size', 'stream_timeout', 'stream_retry_attempts', 'stream_keepalive',
            'stream_parameters', 'stream_headers',
            'is_active', 'configuration', 'tags', 'topic_suffix'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Live Stream'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Building A, Floor 1'}),
            'zone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Zone A'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., 40.7128'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g., -74.0060'}),
            'stream_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'e.g., rtsp://192.168.1.100:554/stream'}),
            'stream_protocol': forms.Select(attrs={'class': 'form-select'}),
            'stream_quality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1080p, 720p'}),
            'stream_resolution_width': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1920'}),
            'stream_resolution_height': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1080'}),
            'stream_fps': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g., 30.0'}),
            'stream_bitrate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2000000'}),
            'stream_codec': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., h264, h265, av1'}),
            'stream_audio_codec': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., aac, mp3, opus'}),
            'stream_audio_channels': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1, 2'}),
            'stream_audio_sample_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8000, 16000, 44100'}),
            'stream_audio_bitrate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 128000'}),
            'stream_buffer_size': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1000'}),
            'stream_timeout': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30'}),
            'stream_retry_attempts': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 3'}),
            'stream_keepalive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'stream_parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
            'stream_headers': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"User-Agent": "CustomAgent"}'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'configuration': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
            'tags': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '["tag1", "tag2"]'}),
            'topic_suffix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., front, back, main (max 6 chars, no spaces)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Override the stream_url field to use CharField instead of URLField
        # This allows us to accept RTSP and other streaming protocol URLs
        self.fields['stream_url'] = forms.CharField(
            max_length=500,
            widget=forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., rtsp://192.168.1.100:554/stream'
            }),
            help_text='URL of the video stream (supports RTSP, RTMP, HTTP, UDP, etc.)'
        )
        
        # Add help text
        self.fields['name'].help_text = 'Display name for this stream (e.g., Live Stream)'
        self.fields['description'].help_text = 'Optional description of this stream'
        self.fields['location'].help_text = 'Physical location of the stream source'
        self.fields['zone'].help_text = 'Zone name for organization'
        self.fields['latitude'].help_text = 'GPS latitude coordinate'
        self.fields['longitude'].help_text = 'GPS longitude coordinate'
        self.fields['stream_protocol'].help_text = 'Protocol of the stream'
        self.fields['stream_quality'].help_text = 'Stream quality (e.g., 1080p, 720p)'
        self.fields['stream_resolution_width'].help_text = 'Stream width in pixels'
        self.fields['stream_resolution_height'].help_text = 'Stream height in pixels'
        self.fields['stream_fps'].help_text = 'Stream frame rate (frames per second)'
        self.fields['stream_bitrate'].help_text = 'Stream bitrate in bits per second'
        self.fields['stream_codec'].help_text = 'Video codec of the stream'
        self.fields['stream_audio_codec'].help_text = 'Audio codec of the stream'
        self.fields['stream_audio_channels'].help_text = 'Number of audio channels'
        self.fields['stream_audio_sample_rate'].help_text = 'Audio sample rate in Hz'
        self.fields['stream_audio_bitrate'].help_text = 'Audio bitrate in bits per second'
        self.fields['stream_buffer_size'].help_text = 'Buffer size in milliseconds'
        self.fields['stream_timeout'].help_text = 'Connection timeout in seconds'
        self.fields['stream_retry_attempts'].help_text = 'Number of retry attempts on failure'
        self.fields['stream_keepalive'].help_text = 'Whether to use keepalive connections'
        self.fields['stream_parameters'].help_text = 'Additional stream parameters as JSON'
        self.fields['stream_headers'].help_text = 'Custom HTTP headers as JSON'
        self.fields['is_active'].help_text = 'Whether this source is active'
        self.fields['configuration'].help_text = 'Additional configuration as JSON (optional)'
        self.fields['tags'].help_text = 'Tags for categorization as JSON array (optional)'
        self.fields['topic_suffix'].help_text = 'Suffix to add to the MQTT topic for this stream (e.g., /stream/front_door)'
    
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
    
    def clean_stream_url(self):
        """Custom validation for stream URLs to accept RTSP and other streaming protocols"""
        url = self.cleaned_data.get('stream_url', '').strip()
        if url:
            # Check if it's a valid streaming protocol URL
            import re
            # Pattern for common streaming protocols: rtsp://, rtmp://, http://, https://, udp://, etc.
            stream_url_pattern = r'^(rtsp|rtmp|http|https|udp|tcp|srt|webrtc)://[^\s]+$'
            if not re.match(stream_url_pattern, url):
                raise forms.ValidationError('Please enter a valid streaming URL (e.g., rtsp://192.168.1.100:554/stream, rtmp://server/live/stream)')
            # Update the cleaned data with the stripped URL
            self.cleaned_data['stream_url'] = url
        return url
    
    def clean_topic_suffix(self):
        """Clean and validate topic suffix"""
        suffix = self.cleaned_data.get('topic_suffix', '').strip()
        if suffix:
            # Remove spaces and limit to 6 characters
            clean_suffix = suffix.replace(' ', '')[:6]
            if len(clean_suffix) < len(suffix.replace(' ', '')):
                raise forms.ValidationError('Topic suffix cannot contain spaces')
            if len(clean_suffix) > 6:
                raise forms.ValidationError('Topic suffix cannot exceed 6 characters')
            return clean_suffix
        return suffix
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Build authentication JSON from individual fields
        auth_data = {}
        if self.cleaned_data.get('stream_auth_username'):
            auth_data['username'] = self.cleaned_data['stream_auth_username']
        if self.cleaned_data.get('stream_auth_password'):
            auth_data['password'] = self.cleaned_data['stream_auth_password']
        if self.cleaned_data.get('stream_auth_api_key'):
            auth_data['api_key'] = self.cleaned_data['stream_auth_api_key']
        if self.cleaned_data.get('stream_auth_token'):
            auth_data['token'] = self.cleaned_data['stream_auth_token']
        
        # Set the authentication field
        if auth_data:
            instance.stream_authentication = auth_data
        else:
            instance.stream_authentication = {}
        
        if commit:
            instance.save()
        return instance

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

class StreamSubmissionForm(forms.Form):
    """Form for submitting streams to downstream services"""
    
    # Basic stream configuration
    stream_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text="Unique identifier for this stream (auto-generated)"
    )
    
    source_url = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text="Source URL (auto-generated from source configuration)"
    )
    
    topic_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text="Topic name for downstream model subscription (auto-generated)"
    )
    
    external_service_id = forms.CharField(
        max_length=100,
        initial='django-source-management',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        }),
        help_text="Identifier for the external service"
    )
    
    # Processing parameters
    target_fps = forms.FloatField(
        min_value=0.1,
        max_value=300.0,
        initial=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0.1',
            'max': '300.0'
        }),
        help_text="Target frame rate (0.1-300 FPS)"
    )
    
    frame_quality = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=85,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '100'
        }),
        help_text="Frame quality (1-100)"
    )
    
    resize_enabled = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Enable frame resizing"
    )
    
    target_width = forms.IntegerField(
        min_value=1,
        max_value=7680,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '7680'
        }),
        help_text="Target width in pixels (if resizing enabled)"
    )
    
    target_height = forms.IntegerField(
        min_value=1,
        max_value=4320,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '4320'
        }),
        help_text="Target height in pixels (if resizing enabled)"
    )
    
    # Authentication (if applicable)
    username = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        }),
        help_text="Username for authentication (if required)"
    )
    
    password = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        }),
        help_text="Password for authentication (if required)"
    )
    
    # Advanced configuration
    enable_audio = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Enable audio processing"
    )
    
    audio_codec = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., aac, mp3, opus'
        }),
        help_text="Audio codec for processing"
    )
    
    audio_channels = forms.IntegerField(
        min_value=1,
        max_value=8,
        required=False,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '8'
        }),
        help_text="Number of audio channels"
    )
    
    audio_sample_rate = forms.IntegerField(
        min_value=8000,
        max_value=192000,
        required=False,
        initial=16000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '8000',
            'max': '192000'
        }),
        help_text="Audio sample rate in Hz"
    )
    
    # Network and performance
    buffer_size = forms.IntegerField(
        min_value=100,
        max_value=10000,
        required=False,
        initial=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '100',
            'max': '10000'
        }),
        help_text="Buffer size in milliseconds"
    )
    
    timeout = forms.IntegerField(
        min_value=5,
        max_value=300,
        required=False,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '5',
            'max': '300'
        }),
        help_text="Connection timeout in seconds"
    )
    
    retry_attempts = forms.IntegerField(
        min_value=0,
        max_value=10,
        required=False,
        initial=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '10'
        }),
        help_text="Number of retry attempts on failure"
    )
    
    keepalive = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Use keepalive connections"
    )
    
    # Custom metadata
    custom_metadata = forms.JSONField(
        required=False,
        initial=dict,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': '{"key": "value"}'
        }),
        help_text="Additional custom metadata as JSON"
    )
    
    def __init__(self, *args, **kwargs):
        source = kwargs.pop('source', None)
        super().__init__(*args, **kwargs)
        
        if source:
            # Pre-populate fields based on source configuration
            self.fields['stream_id'].initial = str(source.source_id)
            self.fields['topic_name'].initial = source.topic_name or source.generate_topic_name(source.topic_suffix)
            
            # Set source URL based on source type
            if hasattr(source, 'get_camera_url'):
                self.fields['source_url'].initial = source.get_camera_url()
            elif hasattr(source, 'stream_url'):
                self.fields['source_url'].initial = source.stream_url
            
            # Pre-populate authentication if available
            if hasattr(source, 'camera_username') and source.camera_username:
                self.fields['username'].initial = source.camera_username
            if hasattr(source, 'camera_password') and source.camera_password:
                self.fields['password'].initial = source.camera_password
            
            # Pre-populate audio settings if available
            if hasattr(source, 'camera_audio_enabled') and source.camera_audio_enabled:
                self.fields['enable_audio'].initial = True
                if hasattr(source, 'camera_audio_codec') and source.camera_audio_codec:
                    self.fields['audio_codec'].initial = source.camera_audio_codec
                if hasattr(source, 'camera_audio_channels') and source.camera_audio_channels:
                    self.fields['audio_channels'].initial = source.camera_audio_channels
                if hasattr(source, 'camera_audio_sample_rate') and source.camera_audio_sample_rate:
                    self.fields['audio_sample_rate'].initial = source.camera_audio_sample_rate
            
            # Pre-populate performance settings if available
            if hasattr(source, 'camera_buffer_size') and source.camera_buffer_size:
                self.fields['buffer_size'].initial = source.camera_buffer_size
            if hasattr(source, 'camera_timeout') and source.camera_timeout:
                self.fields['timeout'].initial = source.camera_timeout
            if hasattr(source, 'camera_retry_attempts') and source.camera_retry_attempts:
                self.fields['retry_attempts'].initial = source.camera_retry_attempts
            if hasattr(source, 'camera_keepalive') and source.camera_keepalive is not None:
                self.fields['keepalive'].initial = source.camera_keepalive
            
            # Pre-populate resolution settings if available
            if hasattr(source, 'camera_resolution_width') and source.camera_resolution_width:
                self.fields['target_width'].initial = source.camera_resolution_width
            if hasattr(source, 'camera_resolution_height') and source.camera_resolution_height:
                self.fields['target_height'].initial = source.camera_resolution_height
            
            # Pre-populate FPS if available
            if hasattr(source, 'camera_fps') and source.camera_fps:
                self.fields['target_fps'].initial = source.camera_fps
            elif hasattr(source, 'stream_fps') and source.stream_fps:
                self.fields['target_fps'].initial = source.stream_fps
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate resize settings
        resize_enabled = cleaned_data.get('resize_enabled')
        target_width = cleaned_data.get('target_width')
        target_height = cleaned_data.get('target_height')
        
        if resize_enabled and (not target_width or not target_height):
            self.add_error('target_width', 'Width and height are required when resizing is enabled')
            self.add_error('target_height', 'Width and height are required when resizing is enabled')
        
        # Validate audio settings
        enable_audio = cleaned_data.get('enable_audio')
        audio_codec = cleaned_data.get('audio_codec')
        
        if enable_audio and not audio_codec:
            self.add_error('audio_codec', 'Audio codec is required when audio is enabled')
        
        # Validate custom metadata
        custom_metadata = cleaned_data.get('custom_metadata')
        if custom_metadata:
            try:
                if isinstance(custom_metadata, str):
                    import json
                    json.loads(custom_metadata)
            except json.JSONDecodeError:
                self.add_error('custom_metadata', 'Custom metadata must be valid JSON')
        
        return cleaned_data
    
    def get_submission_payload(self):
        """Get the complete payload for downstream service submission"""
        cleaned_data = self.cleaned_data
        
        payload = {
            'stream_id': cleaned_data['stream_id'],
            'source_url': cleaned_data['source_url'],
            'topic_name': cleaned_data['topic_name'],
            'external_service_id': cleaned_data['external_service_id'],
            'target_fps': cleaned_data['target_fps'],
            'frame_quality': cleaned_data['frame_quality'],
            'resize_enabled': cleaned_data['resize_enabled'],
            'target_width': cleaned_data.get('target_width'),
            'target_height': cleaned_data.get('target_height'),
            'username': cleaned_data.get('username'),
            'password': cleaned_data.get('password'),
            'metadata': {}
        }
        
        # Add audio configuration if enabled
        if cleaned_data.get('enable_audio'):
            payload['metadata']['audio_enabled'] = True
            payload['metadata']['audio_codec'] = cleaned_data.get('audio_codec')
            payload['metadata']['audio_channels'] = cleaned_data.get('audio_channels')
            payload['metadata']['audio_sample_rate'] = cleaned_data.get('audio_sample_rate')
        else:
            payload['metadata']['audio_enabled'] = False
        
        # Add performance configuration
        payload['metadata']['buffer_size'] = cleaned_data.get('buffer_size')
        payload['metadata']['timeout'] = cleaned_data.get('timeout')
        payload['metadata']['retry_attempts'] = cleaned_data.get('retry_attempts')
        payload['metadata']['keepalive'] = cleaned_data.get('keepalive')
        
        # Add custom metadata
        if cleaned_data.get('custom_metadata'):
            if isinstance(cleaned_data['custom_metadata'], str):
                import json
                custom_meta = json.loads(cleaned_data['custom_metadata'])
            else:
                custom_meta = cleaned_data['custom_metadata']
            payload['metadata'].update(custom_meta)
        
        return payload 