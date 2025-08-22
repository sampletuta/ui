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