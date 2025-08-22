# Streaming Video Player

A modern, feature-rich video player designed specifically for streaming sources including RTSP, RTMP, HLS, and HTTP streams.

## Features

### 🎥 Multi-Protocol Support
- **RTSP Streams** - Real Time Streaming Protocol
- **RTMP Streams** - Real Time Messaging Protocol  
- **HLS Streams** - HTTP Live Streaming (.m3u8)
- **HTTP/HTTPS** - Direct video file streaming
- **WebRTC** - Web Real-Time Communication (requires gateway server)

### 🎮 Advanced Controls
- **Playback Controls** - Play, pause, stop
- **Speed Control** - 0.25x to 4x playback speed
- **Volume Control** - Mute/unmute with slider
- **Fullscreen Support** - Native fullscreen mode
- **Progress Bar** - Click to seek, hover for time preview
- **Keyboard Shortcuts** - Space, M, F, arrows, etc.

### 🔧 Smart Features
- **Auto-Protocol Detection** - Automatically detects stream type
- **Fallback Support** - Graceful degradation for unsupported protocols
- **Retry Logic** - Automatic reconnection on failures
- **Buffer Management** - Optimized buffering for smooth playback
- **Error Handling** - User-friendly error messages and recovery

### 📱 Responsive Design
- **Mobile Optimized** - Touch-friendly controls
- **Responsive Layout** - Adapts to different screen sizes
- **Accessibility** - Keyboard navigation and screen reader support
- **Dark Theme** - Modern, eye-friendly interface

## Quick Start

### 1. Basic Usage

```html
<!-- Include the CSS and JavaScript -->
<link rel="stylesheet" href="{% static 'css/streaming_video_player.css' %}">
<script src="{% static 'js/streaming_video_player.js' %}"></script>

<!-- Create a container -->
<div id="myPlayer"></div>

<!-- Initialize the player -->
<script>
const player = new StreamingVideoPlayer('myPlayer', {
    autoplay: true,
    muted: false,
    controls: true
});

// Load a stream
player.loadStream('rtsp://camera-ip:554/stream', 'rtsp');
</script>
```

### 2. Configuration Options

```javascript
const player = new StreamingVideoPlayer('containerId', {
    autoplay: true,        // Auto-start playback
    muted: false,          // Start muted
    controls: true,        // Show custom controls
    width: '100%',         // Player width
    height: '100%'         // Player height
});
```

### 3. Loading Different Stream Types

```javascript
// RTSP Stream
player.loadStream('rtsp://192.168.1.100:554/stream', 'rtsp');

// RTMP Stream
player.loadStream('rtmp://server/live/stream', 'rtmp');

// HLS Stream
player.loadStream('https://server.com/stream.m3u8', 'hls');

// HTTP Video
player.loadStream('https://server.com/video.mp4', 'http');

// Auto-detect protocol
player.loadStream('rtsp://camera-ip:554/stream', 'auto');
```

## API Reference

### Constructor

```javascript
new StreamingVideoPlayer(containerId, options)
```

**Parameters:**
- `containerId` (string) - ID of the HTML container element
- `options` (object) - Configuration options

### Methods

#### `loadStream(url, protocol)`
Loads a stream with the specified URL and protocol.

```javascript
player.loadStream('rtsp://camera:554/stream', 'rtsp');
```

#### `play()`
Starts playback.

```javascript
player.play();
```

#### `pause()`
Pauses playback.

```javascript
player.pause();
```

#### `stop()`
Stops playback and resets to beginning.

```javascript
player.stop();
```

#### `setSpeed(speed)`
Sets playback speed (0.25, 0.5, 1, 1.5, 2, 4).

```javascript
player.setSpeed(2); // 2x speed
```

#### `setVolume(volume)`
Sets volume level (0.0 to 1.0).

```javascript
player.setVolume(0.5); // 50% volume
```

#### `toggleMute()`
Toggles mute state.

```javascript
player.toggleMute();
```

#### `toggleFullscreen()`
Toggles fullscreen mode.

```javascript
player.toggleFullscreen();
```

#### `destroy()`
Destroys the player instance and cleans up resources.

```javascript
player.destroy();
```

### Events

The player automatically handles these events:
- `loadedmetadata` - Video metadata loaded
- `playing` - Playback started
- `pause` - Playback paused
- `ended` - Playback ended
- `error` - Error occurred
- `waiting` - Buffering
- `canplay` - Ready to play

### Properties

- `currentStream` - Currently loaded stream URL
- `isPlaying` - Current playback state
- `isMuted` - Current mute state
- `currentSpeed` - Current playback speed
- `video` - HTML video element reference

## Integration Examples

### 1. Django Template Integration

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div class="streaming-container">
    <h2>Live Camera Stream</h2>
    <div id="cameraPlayer"></div>
</div>

<link rel="stylesheet" href="{% static 'css/streaming_video_player.css' %}">
<script src="{% static 'js/streaming_video_player.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const player = new StreamingVideoPlayer('cameraPlayer', {
        autoplay: true,
        muted: true
    });
    
    // Load camera stream
    player.loadStream('{{ camera_stream_url }}', 'rtsp');
});
</script>
{% endblock %}
```

### 2. Source Management Integration

```python
# views.py
def camera_stream(request, camera_id):
    camera = get_object_or_404(CameraSource, pk=camera_id)
    return render(request, 'camera_stream.html', {
        'camera': camera,
        'stream_url': camera.get_stream_url()
    })
```

```html
<!-- camera_stream.html -->
<div id="cameraPlayer"></div>

<script>
const player = new StreamingVideoPlayer('cameraPlayer');
player.loadStream('{{ stream_url }}', 'rtsp');
</script>
```

### 3. Dynamic Stream Switching

```javascript
// Switch between multiple cameras
const cameras = [
    { id: 'cam1', url: 'rtsp://camera1:554/stream' },
    { id: 'cam2', url: 'rtsp://camera2:554/stream' },
    { id: 'cam3', url: 'rtsp://camera3:554/stream' }
];

let currentCameraIndex = 0;

function switchCamera() {
    currentCameraIndex = (currentCameraIndex + 1) % cameras.length;
    const camera = cameras[currentCameraIndex];
    
    player.loadStream(camera.url, 'rtsp');
    updateCameraInfo(camera);
}

// Auto-switch every 30 seconds
setInterval(switchCamera, 30000);
```

## Protocol Support Details

### RTSP Streams
- **Requirements**: Media gateway server (GStreamer, FFmpeg, Node-Media-Server)
- **Browser Support**: Limited native support, requires WebRTC gateway
- **Use Case**: IP cameras, surveillance systems

### RTMP Streams
- **Requirements**: RTMP server (Nginx-RTMP, Node-Media-Server)
- **Browser Support**: No native support, requires conversion
- **Use Case**: Live streaming, broadcasting

### HLS Streams
- **Requirements**: HLS server or CDN
- **Browser Support**: Native support in Safari, HLS.js for others
- **Use Case**: Adaptive bitrate streaming, live events

### HTTP Streams
- **Requirements**: Web server with video files
- **Browser Support**: Full native support
- **Use Case**: Video on demand, recorded content

## Browser Compatibility

| Browser | RTSP | RTMP | HLS | HTTP | WebRTC |
|---------|------|------|-----|------|--------|
| Chrome  | ❌   | ❌   | ✅  | ✅   | ✅     |
| Firefox | ❌   | ❌   | ✅  | ✅   | ✅     |
| Safari  | ❌   | ❌   | ✅  | ✅   | ✅     |
| Edge    | ❌   | ❌   | ✅  | ✅   | ✅     |

**Note**: RTSP and RTMP require media gateway servers for browser compatibility.

## Performance Optimization

### 1. Buffer Management
```javascript
// Optimize HLS buffering
const player = new StreamingVideoPlayer('container', {
    hlsConfig: {
        maxBufferLength: 30,
        maxMaxBufferLength: 600,
        maxBufferSize: 60 * 1000 * 1000
    }
});
```

### 2. Quality Selection
```javascript
// Auto-quality switching for HLS
player.on('qualityChanged', function(quality) {
    console.log('Quality changed to:', quality);
});
```

### 3. Connection Management
```javascript
// Handle connection errors
player.on('error', function(error) {
    if (error.fatal) {
        // Attempt reconnection
        setTimeout(() => {
            player.loadStream(player.currentStream);
        }, 5000);
    }
});
```

## Troubleshooting

### Common Issues

#### 1. RTSP Stream Not Playing
**Problem**: RTSP streams show "WebRTC streaming requires a media gateway server"
**Solution**: Set up a media gateway server (GStreamer, FFmpeg) to convert RTSP to WebRTC

#### 2. HLS Stream Buffering
**Problem**: HLS streams buffer frequently
**Solution**: Adjust buffer settings and check network conditions

#### 3. Volume Control Not Working
**Problem**: Volume slider doesn't respond
**Solution**: Ensure the video element is properly loaded before adjusting volume

#### 4. Fullscreen Not Working
**Problem**: Fullscreen button doesn't work
**Solution**: Check browser permissions and ensure HTTPS for production sites

### Debug Mode

Enable debug logging:
```javascript
// Add this before initializing the player
localStorage.setItem('streamingPlayerDebug', 'true');

const player = new StreamingVideoPlayer('container');
```

## Customization

### 1. Custom Controls
```css
/* Customize control colors */
.streaming-video-player {
    --primary-color: #ff6b6b;
    --secondary-color: #4ecdc4;
    --error-color: #ff4757;
}
```

### 2. Custom Themes
```css
/* Light theme */
.streaming-video-player.light-theme {
    --bg-primary: rgba(255, 255, 255, 0.9);
    --text-primary: #333;
    --border-color: #ddd;
}
```

### 3. Custom Events
```javascript
// Listen for custom events
player.on('streamLoaded', function(streamInfo) {
    console.log('Stream loaded:', streamInfo);
});

player.on('qualityChanged', function(quality) {
    updateQualityIndicator(quality);
});
```

## Security Considerations

### 1. HTTPS Requirements
- Fullscreen API requires HTTPS in production
- WebRTC requires secure context
- HLS streams should use HTTPS

### 2. CORS Configuration
```python
# Django settings.py
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://streaming-server.com"
]
```

### 3. Authentication
```javascript
// Add authentication headers
player.loadStream(url, protocol, {
    headers: {
        'Authorization': 'Bearer ' + token
    }
});
```

## Deployment

### 1. Static Files
```bash
# Collect static files
python manage.py collectstatic

# Ensure CSS and JS are served
STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles/'
```

### 2. Media Server Setup
```bash
# Install GStreamer for RTSP gateway
sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good

# Start RTSP to WebRTC gateway
gst-launch-1.0 rtspsrc location=rtsp://camera:554/stream ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! v4l2sink device=/dev/video0
```

### 3. Production Configuration
```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']

# Use CDN for static files
STATIC_URL = 'https://cdn.yourdomain.com/static/'
```

## Support and Contributing

### Getting Help
1. Check the browser console for error messages
2. Verify stream URLs are accessible
3. Test with different browsers
4. Check network connectivity

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### License
This streaming video player is part of the Django Video Management System and follows the same license terms.

---

For more information, visit the project documentation or contact the development team.
