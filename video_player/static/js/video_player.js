// Video Player API Configuration
const API_BASE_URL = window.location.origin + '/video/api/';
const API_ENDPOINTS = {
    videoStreams: API_BASE_URL + 'video-streams/get/',
    detectionEvents: API_BASE_URL + 'detection-events/get/',
    addDetection: API_BASE_URL + 'detection-event/add/',
    updateCamera: API_BASE_URL + 'camera/',
    clearData: API_BASE_URL + 'clear-data/'
};

// Global variables
let videoStreams = {};
let currentCamera = '';
let detectionEvents = [];
let currentCameraData = null;
let currentHls = null;
let isPlaying = false;
let isMuted = false;
let currentSpeed = 1;
let isLoading = false;
let retryCount = 0;
let dataUpdateInterval = null;
let isRealTimeMode = false;

// Initialize global variables from window context
function initializeGlobalData() {
    console.log('=== INITIALIZING GLOBAL DATA ===');
    console.log('window.videoStreams:', window.videoStreams);
    console.log('window.currentCamera:', window.currentCamera);
    console.log('window.detectionEvents:', window.detectionEvents);
    
    if (window.videoStreams) {
        videoStreams = window.videoStreams;
        console.log('✅ Initialized videoStreams from window context:', videoStreams);
        console.log('✅ videoStreams keys:', Object.keys(videoStreams));
    } else {
        console.error('❌ window.videoStreams is not available');
    }
    
    if (window.currentCamera) {
        currentCamera = window.currentCamera;
        console.log('✅ Initialized currentCamera from window context:', currentCamera);
    } else {
        console.error('❌ window.currentCamera is not available');
    }
    
    if (window.detectionEvents) {
        detectionEvents = window.detectionEvents;
        console.log('✅ Initialized detectionEvents from window context:', detectionEvents);
    } else {
        console.error('❌ window.detectionEvents is not available');
    }
    
    console.log('=== GLOBAL DATA INITIALIZATION COMPLETE ===');
    console.log('Final videoStreams:', videoStreams);
    console.log('Final currentCamera:', currentCamera);
}

// DOM Elements
let video, playPauseBtn, playIcon, progressBar, progressContainer, currentTimeSpan, durationSpan;
let volumeBtn, fullscreenBtn, cameraTabsContainer, detectionItems;
let timeNavTabs, timeTagsContainer, detectionsContainer, detectionsList, bookmarksContainer, manualTimeContainer;
let timeInput, seekButton, seekBackwardBtn, seekForwardBtn, speedButton, speedDropdown;
let progressBuffer, loadingOverlay, loadingText, loadingProgressBar, networkError;
let errorMessage, retryButton, refreshDataBtn, toggleRealTimeBtn, apiStatus;
let detectionMarkers, detectionFilterBtns;

// Initialize video player
function initVideoPlayer() {
    console.log('Initializing video player...');
    console.log('Available video streams:', videoStreams);
    console.log('Current camera:', currentCamera);
    
    // Get DOM elements
    video = document.getElementById('zmPlayer');
    playPauseBtn = document.getElementById('playPauseBtn');
    playIcon = document.getElementById('playIcon');
    progressBar = document.getElementById('progressBar');
    progressContainer = document.getElementById('progressContainer');
    currentTimeSpan = document.getElementById('currentTime');
    durationSpan = document.getElementById('duration');
    volumeBtn = document.getElementById('volumeBtn');
    fullscreenBtn = document.getElementById('fullscreenBtn');
    cameraTabsContainer = document.getElementById('cameraTabs');
    detectionItems = document.querySelectorAll('.detection-item');

    // Time navigation elements
    timeNavTabs = document.querySelectorAll('.time-nav-tab');
    timeTagsContainer = document.getElementById('timeTagsContainer');
    detectionsContainer = document.getElementById('detectionsContainer');
    detectionsList = document.getElementById('detectionsList');
    bookmarksContainer = document.getElementById('bookmarksContainer');
    manualTimeContainer = document.getElementById('manualTimeContainer');
    timeInput = document.getElementById('timeInput');
    seekButton = document.getElementById('seekButton');
    
    // Detection elements
    detectionMarkers = document.getElementById('detectionMarkers');
    detectionFilterBtns = document.querySelectorAll('.detection-filter-btn');

    // New control elements
    seekBackwardBtn = document.getElementById('seekBackwardBtn');
    seekForwardBtn = document.getElementById('seekForwardBtn');
    speedButton = document.getElementById('speedButton');
    speedDropdown = document.getElementById('speedDropdown');
    progressBuffer = document.getElementById('progressBuffer');
    loadingOverlay = document.getElementById('loadingOverlay');
    loadingText = document.getElementById('loadingText');
    loadingProgressBar = document.getElementById('loadingProgressBar');
    networkError = document.getElementById('networkError');
    errorMessage = document.getElementById('errorMessage');
    retryButton = document.getElementById('retryButton');

    // API control elements
    refreshDataBtn = document.getElementById('refreshDataBtn');
    toggleRealTimeBtn = document.getElementById('toggleRealTimeBtn');
    apiStatus = document.getElementById('apiStatus');

    // Check if video element exists
    if (!video) {
        console.error('Video element not found');
        return;
    }

    // Initialize components
    createCameraTabs();
    initTimeNavigation();
    initSpeedControl();
    initEventListeners();
    
    // Only initialize video if we have a current camera
    if (currentCamera && currentCamera !== 'no_camera') {
        console.log('Initializing video player with camera:', currentCamera);
        initVideoPlayerWithCamera(currentCamera);
    } else {
        console.log('No camera selected, video player ready but not playing');
    }
}

// Create camera tabs dynamically
function createCameraTabs() {
    console.log('=== CREATING CAMERA TABS ===');
    console.log('Camera tabs container:', cameraTabsContainer);
    console.log('Available video streams:', videoStreams);
    console.log('videoStreams type:', typeof videoStreams);
    console.log('videoStreams keys:', videoStreams ? Object.keys(videoStreams) : 'undefined');
    
    if (!cameraTabsContainer) {
        console.error('❌ Camera tabs container not found');
        return;
    }
    
    cameraTabsContainer.innerHTML = '';
    cameraTabs = [];
    
    // Check if we have video streams
    if (!videoStreams || Object.keys(videoStreams).length === 0) {
        console.log('❌ No video streams available for camera tabs');
        console.log('videoStreams value:', videoStreams);
        return;
    }
    
    console.log('✅ Creating tabs for cameras:', Object.keys(videoStreams));
    
    Object.keys(videoStreams).forEach(cameraId => {
        const cameraData = videoStreams[cameraId];
        if (!cameraData) {
            console.warn('❌ No camera data for:', cameraId);
            return;
        }
        
        console.log('✅ Creating tab for camera:', cameraId, cameraData);
        
        const button = document.createElement('button');
        button.setAttribute('data-camera', cameraId);
        button.setAttribute('data-live-url', cameraData.liveUrl || '');
        button.setAttribute('data-archive-url', cameraData.archiveUrl || '');
        button.textContent = cameraData.name || 'Unknown Camera';
        button.className = 'camera-tab-btn';
        
        // Add camera info tooltip
        button.title = `${cameraData.name}\nType: ${cameraData.type}\nLocation: ${cameraData.location || 'Unknown'}`;
        
        if (cameraId === currentCamera) {
            button.classList.add('active');
            console.log('✅ Set active tab for:', cameraId);
        }
        
        button.addEventListener('click', () => {
            console.log('Camera tab clicked:', cameraId);
            switchCamera(cameraId);
        });
        
        cameraTabsContainer.appendChild(button);
        cameraTabs.push(button);
        
        console.log('✅ Created tab for camera:', cameraId);
    });
    
    console.log('Total camera tabs created:', cameraTabs.length);
    
    // Show camera tabs container if we have tabs
    if (cameraTabs.length > 0) {
        cameraTabsContainer.style.display = 'flex';
        console.log('✅ Camera tabs container is now visible');
        
        // Show header if we have multiple sources
        const headerElement = document.getElementById('cameraTabsHeader');
        if (headerElement && cameraTabs.length > 1) {
            headerElement.style.display = 'block';
            console.log('✅ Camera tabs header is now visible');
        }
        
        console.log('✅ Camera tabs are now fully visible');
    } else {
        console.log('❌ No camera tabs were created');
    }
}

// Switch between cameras
function switchCamera(cameraId) {
    console.log('Switching to camera:', cameraId);
    
    // Update current camera
    currentCamera = cameraId;
    
    // Update active tab
    document.querySelectorAll('[data-camera]').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-camera="${cameraId}"]`)?.classList.add('active');
    
    // Initialize video player with new camera
    initVideoPlayerWithCamera(cameraId);
}

// Initialize time navigation
function initTimeNavigation() {
    currentCameraData = videoStreams[currentCamera];
    if (!currentCameraData) return;

    // Populate time tags
    populateTimeTags();
    
    // Populate bookmarks
    populateBookmarks();
}

// Populate time tags
function populateTimeTags() {
    if (!currentCameraData.timeTags || !timeTagsContainer) return;
    
    timeTagsContainer.innerHTML = '';
    currentCameraData.timeTags.forEach(tag => {
        const tagElement = document.createElement('div');
        tagElement.className = 'time-tag';
        tagElement.setAttribute('data-time', tag.time);
        tagElement.innerHTML = `
            <div class="time-tag-marker" style="background-color: ${tag.color}"></div>
            <div class="time-tag-time">${formatTime(tag.time)}</div>
            <div class="time-tag-label">${tag.label}</div>
            <div class="time-tag-type type-${tag.type}">${tag.type}</div>
        `;
        
        tagElement.addEventListener('click', () => {
            seekToTime(tag.time);
            highlightActiveTag(tagElement);
        });
        
        timeTagsContainer.appendChild(tagElement);
    });
}

// Populate bookmarks
function populateBookmarks() {
    if (!currentCameraData.bookmarks || !bookmarksContainer) return;
    
    bookmarksContainer.innerHTML = '';
    currentCameraData.bookmarks.forEach(bookmark => {
        const bookmarkElement = document.createElement('div');
        bookmarkElement.className = 'bookmark';
        bookmarkElement.setAttribute('data-time', bookmark.time);
        bookmarkElement.innerHTML = `
            <i class="fas fa-bookmark bookmark-icon"></i>
            <div class="bookmark-time">${formatTime(bookmark.time)}</div>
            <div class="bookmark-content">
                <div class="bookmark-label">${bookmark.label}</div>
                <div class="bookmark-description">${bookmark.description}</div>
            </div>
        `;
        
        bookmarkElement.addEventListener('click', () => {
            seekToTime(bookmark.time);
            highlightActiveBookmark(bookmarkElement);
        });
        
        bookmarksContainer.appendChild(bookmarkElement);
    });
}

// Highlight active tag
function highlightActiveTag(activeElement) {
    document.querySelectorAll('.time-tag').forEach(tag => {
        tag.classList.remove('active');
    });
    activeElement.classList.add('active');
}

// Highlight active bookmark
function highlightActiveBookmark(activeElement) {
    document.querySelectorAll('.bookmark').forEach(bookmark => {
        bookmark.classList.remove('active');
    });
    activeElement.classList.add('active');
}

// Detection Timeline Functions
let detectionData = [];
let currentDetectionFilter = 'all';

// Load detection data from API
async function loadDetectionData() {
    try {
        console.log('Loading detection data for video...');
        
        // Get current video URL or source ID
        const videoUrl = video?.src || window.location.href;
        const sourceId = getSourceIdFromUrl(videoUrl);
        
        const response = await fetch('/api/detections/timeline/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                source_id: sourceId,
                video_url: videoUrl,
                time_range_hours: 24
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            detectionData = data.timeline || [];
            console.log(`Loaded ${detectionData.length} detections`);
            
            // Update detection markers on progress bar
            updateDetectionMarkers();
            
            // Update detection list
            updateDetectionList();
            
            return detectionData;
        } else {
            throw new Error(data.error || 'Failed to load detection data');
        }
    } catch (error) {
        console.error('Error loading detection data:', error);
        detectionData = [];
        return [];
    }
}

// Update detection markers on progress bar
function updateDetectionMarkers() {
    if (!detectionMarkers || !video || !video.duration) return;
    
    // Clear existing markers
    detectionMarkers.innerHTML = '';
    
    // Filter detections based on current filter
    const filteredDetections = getFilteredDetections();
    
    filteredDetections.forEach(detection => {
        const marker = createDetectionMarker(detection);
        detectionMarkers.appendChild(marker);
    });
}

// Create a detection marker element
function createDetectionMarker(detection) {
    const marker = document.createElement('div');
    marker.className = 'detection-marker';
    
    // Determine marker type
    if (detection.alert_created) {
        marker.classList.add('alert');
    } else if (detection.is_duplicate) {
        marker.classList.add('duplicate');
    } else {
        marker.classList.add('normal');
    }
    
    // Calculate position on progress bar
    const position = (detection.timestamp / video.duration) * 100;
    marker.style.left = `${position}%`;
    
    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'detection-marker-tooltip';
    tooltip.innerHTML = `
        <div><strong>${detection.target_name}</strong></div>
        <div>Time: ${formatTime(detection.timestamp)}</div>
        <div>Confidence: ${(detection.confidence * 100).toFixed(1)}%</div>
        <div>Status: ${detection.alert_created ? 'Alert' : detection.is_duplicate ? 'Duplicate' : 'Normal'}</div>
    `;
    marker.appendChild(tooltip);
    
    // Add click handler
    marker.addEventListener('click', (e) => {
        e.stopPropagation();
        seekToTime(detection.timestamp);
        highlightDetectionItem(detection.id);
    });
    
    return marker;
}

// Update detection list
function updateDetectionList() {
    if (!detectionsList) return;
    
    // Clear existing items
    detectionsList.innerHTML = '';
    
    // Filter detections based on current filter
    const filteredDetections = getFilteredDetections();
    
    // Sort by timestamp
    filteredDetections.sort((a, b) => a.timestamp - b.timestamp);
    
    filteredDetections.forEach(detection => {
        const item = createDetectionItem(detection);
        detectionsList.appendChild(item);
    });
}

// Create a detection list item
function createDetectionItem(detection) {
    const item = document.createElement('div');
    item.className = 'detection-item';
    item.setAttribute('data-detection-id', detection.id);
    
    // Determine item type
    if (detection.alert_created) {
        item.classList.add('alert');
    } else if (detection.is_duplicate) {
        item.classList.add('duplicate');
    } else {
        item.classList.add('normal');
    }
    
    // Create status indicator
    const status = document.createElement('div');
    status.className = 'detection-item-status';
    if (detection.alert_created) {
        status.classList.add('alert');
    } else if (detection.is_duplicate) {
        status.classList.add('duplicate');
    } else {
        status.classList.add('normal');
    }
    
    // Create face image
    const faceImg = document.createElement('img');
    faceImg.className = 'detection-item-face';
    faceImg.src = detection.face_image_url || '/static/img/default-face.jpg';
    faceImg.alt = detection.target_name;
    faceImg.onerror = () => {
        faceImg.src = '/static/img/default-face.jpg';
    };
    
    item.innerHTML = `
        <div class="detection-item-header">
            <div class="detection-item-time">${formatTime(detection.timestamp)}</div>
            <div class="detection-item-confidence">${(detection.confidence * 100).toFixed(1)}%</div>
        </div>
        <div class="detection-item-content">
            <img class="detection-item-face" src="${detection.face_image_url || '/static/img/default-face.jpg'}" alt="${detection.target_name}" onerror="this.src='/static/img/default-face.jpg'">
            <div class="detection-item-info">
                <div class="detection-item-target">${detection.target_name}</div>
                <div class="detection-item-details">
                    <span>Camera: ${detection.camera_name || 'Unknown'}</span>
                    <span>Status: ${detection.alert_created ? 'Alert' : detection.is_duplicate ? 'Duplicate' : 'Normal'}</span>
                </div>
            </div>
        </div>
    `;
    
    // Add status indicator
    item.appendChild(status);
    
    // Add click handler
    item.addEventListener('click', () => {
        seekToTime(detection.timestamp);
        highlightDetectionItem(detection.id);
    });
    
    return item;
}

// Get filtered detections based on current filter
function getFilteredDetections() {
    switch (currentDetectionFilter) {
        case 'alerts':
            return detectionData.filter(d => d.alert_created);
        case 'duplicates':
            return detectionData.filter(d => d.is_duplicate);
        case 'all':
        default:
            return detectionData;
    }
}

// Highlight active detection item
function highlightDetectionItem(detectionId) {
    document.querySelectorAll('.detection-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const activeItem = document.querySelector(`[data-detection-id="${detectionId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Set detection filter
function setDetectionFilter(filter) {
    currentDetectionFilter = filter;
    
    // Update filter buttons
    detectionFilterBtns.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.filter === filter) {
            btn.classList.add('active');
        }
    });
    
    // Update markers and list
    updateDetectionMarkers();
    updateDetectionList();
}

// Get source ID from URL
function getSourceIdFromUrl(url) {
    // Extract source ID from URL patterns
    const patterns = [
        /\/stream\/([^\/]+)/,
        /\/source\/([^\/]+)/,
        /source_id=([^&]+)/
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) {
            return match[1];
        }
    }
    
    return null;
}

// Show loading overlay
function showLoading(message = 'Loading video...') {
    isLoading = true;
    if (loadingText) loadingText.textContent = message;
    if (loadingOverlay) loadingOverlay.classList.add('show');
    if (loadingProgressBar) loadingProgressBar.style.width = '0%';
    
    // Auto-hide loading after 10 seconds to prevent stuck states
    setTimeout(() => {
        if (isLoading) {
            hideLoading();
        }
    }, 10000);
}

// Hide loading overlay
function hideLoading() {
    isLoading = false;
    if (loadingOverlay) loadingOverlay.classList.remove('show');
}

// Show network error
function showNetworkError(message = 'Unable to load video stream') {
    if (errorMessage) errorMessage.textContent = message;
    if (networkError) networkError.classList.add('show');
    hideLoading();
}

// Hide network error
function hideNetworkError() {
    if (networkError) networkError.classList.remove('show');
}

// Update loading progress
function updateLoadingProgress(progress) {
    if (loadingProgressBar) loadingProgressBar.style.width = `${progress}%`;
}

// Seek to specific time
function seekToTime(seconds) {
    if (video && video.duration && isFinite(video.duration)) {
        const targetTime = Math.min(seconds, video.duration);
        video.currentTime = targetTime;
        console.log('Seeking to:', formatTime(targetTime));
        
        // Show loading if seeking to a time that's not buffered
        if (targetTime > video.currentTime + video.buffered.end(0)) {
            showLoading('Seeking to time...');
        }
    }
}

// Seek backward/forward
function seekRelative(seconds) {
    if (video && video.duration && isFinite(video.duration)) {
        const newTime = Math.max(0, Math.min(video.duration, video.currentTime + seconds));
        video.currentTime = newTime;
        console.log('Seeking', seconds > 0 ? 'forward' : 'backward', 'to:', formatTime(newTime));
    }
}

// Change playback speed
function changeSpeed(speed) {
    if (!video) return;
    
    currentSpeed = speed;
    
    // Ensure speed is within browser limits
    const maxSpeed = 16; // Most browsers limit to 16x
    const actualSpeed = Math.min(speed, maxSpeed);
    
    video.playbackRate = actualSpeed;
    if (speedButton) speedButton.textContent = `${speed}x`;
    
    // Update active speed option
    document.querySelectorAll('.speed-option').forEach(option => {
        option.classList.remove('active');
        if (parseFloat(option.dataset.speed) === speed) {
            option.classList.add('active');
        }
    });
    
    // Update fullscreen button if in fullscreen
    if (document.fullscreenElement && fullscreenBtn) {
        fullscreenBtn.innerHTML = `<i class="fas fa-compress"></i><span style="font-size: 10px; margin-left: 4px;">${speed}x</span>`;
    }
    
    console.log('Changed speed to:', speed, 'Actual playback rate:', actualSpeed);
    
    // Show warning if speed was limited
    if (speed > maxSpeed) {
        console.warn(`Speed ${speed}x was limited to ${maxSpeed}x due to browser limitations`);
    }
}

// Toggle speed dropdown
function toggleSpeedDropdown() {
    if (speedDropdown) speedDropdown.classList.toggle('show');
}

// Handle speed option selection
function selectSpeed(speed) {
    changeSpeed(speed);
    if (speedDropdown) speedDropdown.classList.remove('show');
}

// Initialize speed control
function initSpeedControl() {
    // Set initial speed
    changeSpeed(1);
    
    // Add event listeners for speed options
    document.querySelectorAll('.speed-option').forEach(option => {
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            const speed = parseFloat(option.dataset.speed);
            selectSpeed(speed);
        });
    });
}

// Initialize video player with current camera
function initVideoPlayerWithCamera(cameraId) {
    console.log('=== INITIALIZING VIDEO PLAYER WITH CAMERA ===');
    console.log('Camera ID:', cameraId);
    console.log('Available videoStreams:', videoStreams);
    console.log('videoStreams keys:', videoStreams ? Object.keys(videoStreams) : 'undefined');
    
    const cameraData = videoStreams[cameraId];
    if (!cameraData) {
        console.error('❌ Camera data not found for:', cameraId);
        console.error('Available cameras:', videoStreams ? Object.keys(videoStreams) : 'none');
        return;
    }

    console.log('✅ Found camera data:', cameraData);
    currentCameraData = cameraData;

    // Reset states
    hideNetworkError();
    showLoading('Initializing video...');
    retryCount = 0;

    // Destroy previous HLS instance
    if (currentHls) {
        currentHls.destroy();
        currentHls = null;
    }

    // Try live stream first, fallback to archive
    const streamUrl = cameraData.liveUrl || cameraData.archiveUrl;
    console.log('Stream URL for camera', cameraId, ':', streamUrl);
    console.log('Camera data:', cameraData);
    
    if (streamUrl) {
        // Determine stream type and handle accordingly
        const streamType = detectStreamType(streamUrl);
        console.log('Detected stream type:', streamType);
        
        switch (streamType) {
            case 'hls':
                loadHLSStream(streamUrl);
                break;
            case 'rtsp':
                loadRTSPStream(streamUrl, cameraData);
                break;
            case 'rtmp':
                loadRTMPStream(streamUrl, cameraData);
                break;
            case 'http':
            case 'https':
                loadDirectVideo(streamUrl);
                break;
            default:
                // Try as direct video file
                console.log('Trying as direct video file:', streamUrl);
                console.log('Video element can play MP4:', video.canPlayType('video/mp4'));
                loadDirectVideo(streamUrl);
        }
    } else {
        console.error('No stream URL available for camera:', cameraId);
        console.error('Camera data:', cameraData);
        showNetworkError('No video source available');
    }
}

// Detect stream type from URL
function detectStreamType(url) {
    if (url.includes('.m3u8')) return 'hls';
    if (url.includes('rtsp://')) return 'rtsp';
    if (url.includes('rtmp://')) return 'rtmp';
    if (url.startsWith('http://') || url.startsWith('https://')) return 'http';
    return 'unknown';
}

// Load HLS stream
function loadHLSStream(url) {
    console.log('Loading HLS stream:', url);
    
    if (Hls.isSupported()) {
        currentHls = new Hls({
            enableWorker: true,
            lowLatencyMode: true,
            backBufferLength: 90
        });
        
        currentHls.loadSource(url);
        currentHls.attachMedia(video);
        
        currentHls.on(Hls.Events.MANIFEST_PARSED, () => {
            console.log('HLS manifest parsed, playing video');
            hideLoading();
            video.play();
            isPlaying = true;
            playIcon.className = 'fas fa-pause';
            initTimeNavigation();
            if (window.initialSeek && isFinite(window.initialSeek) && window.initialSeek > 0) {
                video.currentTime = window.initialSeek;
            }
        });
        
        currentHls.on(Hls.Events.BUFFER_STALLED, () => {
            console.log('HLS buffer stalled');
            showLoading('Buffering...');
        });
        
        currentHls.on(Hls.Events.BUFFER_APPENDING, () => {
            console.log('HLS buffer appending');
            hideLoading();
        });
        
        currentHls.on(Hls.Events.ERROR, (event, data) => {
            console.error('HLS Error:', data);
            if (data.fatal) {
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                    showNetworkError('Network error occurred. Retrying...');
                    retryCount++;
                    if (retryCount < 3) {
                        setTimeout(() => {
                            currentHls.startLoad();
                        }, 2000);
                    } else {
                        // Fallback to archive URL
                        if (currentCameraData && currentCameraData.archiveUrl) {
                            console.log('Falling back to archive URL');
                            loadDirectVideo(currentCameraData.archiveUrl);
                        }
                    }
                } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                    showNetworkError('Media error occurred');
                }
            }
        });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        console.log('Using native HLS for:', url);
        loadDirectVideo(url);
    } else {
        showNetworkError('HLS not supported in this browser');
    }
}

// Load RTSP stream (convert to HTTP stream via proxy)
function loadRTSPStream(url, cameraData) {
    console.log('Loading RTSP stream:', url);
    
    // Show user-friendly message about RTSP
    showLoading('RTSP streams require a media gateway server. Checking for fallback...');
    
    // Try to use archive URL as fallback
    if (cameraData.archiveUrl) {
        console.log('RTSP not directly supported, using archive URL as fallback');
        setTimeout(() => {
            hideLoading();
            showNetworkError('RTSP stream not supported. Using fallback video instead.');
            loadDirectVideo(cameraData.archiveUrl);
        }, 2000);
    } else {
        // No fallback available
        hideLoading();
        showNetworkError('RTSP stream not supported and no fallback available. Please contact your administrator to set up a media gateway server.');
    }
}

// Load RTMP stream (convert to HTTP stream via proxy)
function loadRTMPStream(url, cameraData) {
    console.log('Loading RTMP stream:', url);
    
    // Show user-friendly message about RTMP
    showLoading('RTMP streams require a media gateway server. Checking for fallback...');
    
    // Try to use archive URL as fallback
    if (cameraData.archiveUrl) {
        console.log('RTMP not directly supported, using archive URL as fallback');
        setTimeout(() => {
            hideLoading();
            showNetworkError('RTMP stream not supported. Using fallback video instead.');
            loadDirectVideo(cameraData.archiveUrl);
        }, 2000);
    } else {
        // No fallback available
        hideLoading();
        showNetworkError('RTMP stream not supported and no fallback available. Please contact your administrator to set up a media gateway server.');
    }
}

// Load direct video file
function loadDirectVideo(url) {
    console.log('Loading direct video from URL:', url);
    
    if (!video) {
        console.error('Video element not found');
        return;
    }
    
    // Clear any existing source
    video.innerHTML = '';
    
    // Create new source element
    const source = document.createElement('source');
    source.src = url;
    
    // Detect video type from URL
    let videoType = 'video/mp4'; // default
    if (url.includes('.webm')) videoType = 'video/webm';
    else if (url.includes('.ogg')) videoType = 'video/ogg';
    else if (url.includes('.m3u8')) videoType = 'application/vnd.apple.mpegurl';
    else if (url.includes('.mp4')) videoType = 'video/mp4';
    
    source.type = videoType;
    console.log('Setting video source type:', videoType);
    video.appendChild(source);
    
    console.log('Video source set, loading...');
    video.load();
    
    // Add event listeners for debugging
    video.addEventListener('loadstart', () => {
        console.log('Video load started');
        showLoading('Loading video...');
    });
    
    video.addEventListener('loadedmetadata', () => {
        console.log('Video metadata loaded, duration:', video.duration);
        console.log('Video dimensions:', video.videoWidth, 'x', video.videoHeight);
        hideLoading();
        
        // Try to play the video
        const playPromise = video.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                console.log('Video started playing successfully');
                isPlaying = true;
                if (playIcon) playIcon.className = 'fas fa-pause';
                initTimeNavigation();
                
                // Load detection data for timeline markers
                loadDetectionData();
                
                // Seek if requested
                if (window.initialSeek && isFinite(window.initialSeek) && window.initialSeek > 0) {
                    video.currentTime = window.initialSeek;
                }
            }).catch(error => {
                console.error('Video play failed:', error);
                showNetworkError('Video play failed: ' + error.message);
            });
        }
    });
    
    video.addEventListener('waiting', () => {
        console.log('Video waiting for data');
        showLoading('Buffering...');
    });
    
    video.addEventListener('canplay', () => {
        console.log('Video can play');
        hideLoading();
    });
    
    video.addEventListener('canplaythrough', () => {
        console.log('Video can play through');
        hideLoading();
    });
    
    video.addEventListener('playing', () => {
        console.log('Video is now playing');
        hideLoading();
    });
    
    video.addEventListener('error', (e) => {
        console.error('Video error event:', e);
        console.error('Video error details:', video.error);
        showNetworkError('Failed to load video: ' + (video.error ? video.error.message : 'Unknown error'));
    });
    
    video.addEventListener('abort', () => {
        console.log('Video loading aborted');
    });
    
    video.addEventListener('stalled', () => {
        console.log('Video stalled');
        showLoading('Video stalled, retrying...');
    });
}

// Toggle play/pause
function togglePlayPause() {
    if (!video) return;
    
    if (isPlaying) {
        video.pause();
        playIcon.className = 'fas fa-play';
        isPlaying = false;
    } else {
        video.play();
        playIcon.className = 'fas fa-pause';
        isPlaying = true;
    }
}

// Format time helper function
function formatTime(seconds) {
    if (!seconds || !isFinite(seconds)) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize event listeners
function initEventListeners() {
    if (!video) return;

    // Play/Pause functionality
    if (playPauseBtn) playPauseBtn.addEventListener('click', togglePlayPause);
    video.addEventListener('click', togglePlayPause);

                // Progress bar functionality
            video.addEventListener('loadedmetadata', function() {
                if (video.duration && isFinite(video.duration)) {
                    durationSpan.textContent = formatTime(video.duration);
                }
            });

            video.addEventListener('timeupdate', function() {
                if (video.duration && isFinite(video.duration)) {
                    const progress = (video.currentTime / video.duration) * 100;
                    progressBar.style.width = progress + '%';
                    currentTimeSpan.textContent = formatTime(video.currentTime);
                    
                    // Update progress time display
                    const progressTimeDisplay = document.getElementById('progressCurrentTime');
                    if (progressTimeDisplay) {
                        progressTimeDisplay.textContent = formatTime(video.currentTime);
                    }
                    
                    // Update buffer progress
                    if (video.buffered.length > 0) {
                        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
                        const bufferProgress = (bufferedEnd / video.duration) * 100;
                        progressBuffer.style.width = bufferProgress + '%';
                    }
                }
            });

                if (progressContainer) {
                progressContainer.addEventListener('click', function(e) {
                    if (video.duration && isFinite(video.duration)) {
                        const rect = progressContainer.getBoundingClientRect();
                        const clickX = e.clientX - rect.left;
                        const width = rect.width;
                        const clickTime = (clickX / width) * video.duration;
                        video.currentTime = clickTime;
                    }
                });
                
                // Show time on hover
                progressContainer.addEventListener('mousemove', function(e) {
                    if (video.duration && isFinite(video.duration)) {
                        const rect = progressContainer.getBoundingClientRect();
                        const clickX = e.clientX - rect.left;
                        const width = rect.width;
                        const hoverTime = (clickX / width) * video.duration;
                        
                        const progressTimeDisplay = document.getElementById('progressCurrentTime');
                        if (progressTimeDisplay) {
                            progressTimeDisplay.textContent = formatTime(hoverTime);
                        }
                    }
                });
            }

    // Volume control
    if (volumeBtn) {
        volumeBtn.addEventListener('click', function() {
            if (isMuted) {
                video.muted = false;
                volumeBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
                isMuted = false;
            } else {
                video.muted = true;
                volumeBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
                isMuted = true;
            }
        });
    }

    // Seek controls
    if (seekBackwardBtn) seekBackwardBtn.addEventListener('click', () => seekRelative(-10));
    if (seekForwardBtn) seekForwardBtn.addEventListener('click', () => seekRelative(10));

    // Speed control
    if (speedButton) {
        speedButton.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSpeedDropdown();
        });
    }
    
    // Close speed dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (speedButton && speedDropdown && !speedButton.contains(e.target) && !speedDropdown.contains(e.target)) {
            speedDropdown.classList.remove('show');
        }
    });

                // Fullscreen functionality
            if (fullscreenBtn) {
                fullscreenBtn.addEventListener('click', function() {
                    if (document.fullscreenElement) {
                        document.exitFullscreen();
                        fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
                    } else {
                        video.requestFullscreen();
                        fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
                    }
                });
            }
            
            // Update fullscreen button to show speed when in fullscreen
            document.addEventListener('fullscreenchange', function() {
                if (document.fullscreenElement) {
                    // In fullscreen, show speed on the button
                    if (fullscreenBtn) {
                        fullscreenBtn.innerHTML = `<i class="fas fa-compress"></i><span style="font-size: 10px; margin-left: 4px;">${currentSpeed}x</span>`;
                    }
                } else {
                    // Exit fullscreen, show normal expand icon
                    if (fullscreenBtn) {
                        fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
                    }
                }
            });

    // Retry button
    if (retryButton) {
        retryButton.addEventListener('click', () => {
            hideNetworkError();
            initVideoPlayerWithCamera(currentCamera);
        });
    }

    // Camera tab switching
    if (cameraTabsContainer) {
        cameraTabsContainer.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON') {
                const cameraId = e.target.getAttribute('data-camera');
                
                // Remove active class from all tabs
                document.querySelectorAll('.camera-tabs button').forEach(t => t.classList.remove('active'));
                // Add active class to clicked tab
                e.target.classList.add('active');
                
                // Update current camera and initialize video
                currentCamera = cameraId;
                initVideoPlayerWithCamera(cameraId);
                
                console.log('Switched to camera:', cameraId);
            }
        });
    }

    // Detection item clicking
    if (detectionItems) {
        detectionItems.forEach(item => {
            item.addEventListener('click', function() {
                const cameraId = this.getAttribute('data-camera');
                const detectionId = this.getAttribute('data-detection-id');
                const timestamp = parseInt(this.getAttribute('data-timestamp'));
                
                // Remove active class from all items
                detectionItems.forEach(i => i.classList.remove('active'));
                // Add active class to clicked item
                this.classList.add('active');
                
                // Update camera tab
                document.querySelectorAll('.camera-tabs button').forEach(tab => {
                    if (tab.getAttribute('data-camera') === cameraId) {
                        document.querySelectorAll('.camera-tabs button').forEach(t => t.classList.remove('active'));
                        tab.classList.add('active');
                    }
                });
                
                // Switch to camera
                currentCamera = cameraId;
                initVideoPlayerWithCamera(cameraId);
                
                // Seek to detection time if available
                if (timestamp) {
                    setTimeout(() => {
                        seekToTime(timestamp);
                    }, 1000); // Wait for video to load
                }
                
                console.log('Selected detection:', detectionId, 'from camera:', cameraId, 'at time:', timestamp);
            });
        });
    }

    // Time navigation tabs
    if (timeNavTabs) {
        timeNavTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabType = this.getAttribute('data-tab');
                
                // Remove active class from all tabs
                timeNavTabs.forEach(t => t.classList.remove('active'));
                // Add active class to clicked tab
                this.classList.add('active');
                
                // Show/hide containers
                if (timeTagsContainer) timeTagsContainer.style.display = tabType === 'tags' ? 'flex' : 'none';
                if (detectionsContainer) detectionsContainer.style.display = tabType === 'detections' ? 'block' : 'none';
                if (bookmarksContainer) bookmarksContainer.style.display = tabType === 'bookmarks' ? 'flex' : 'none';
                if (manualTimeContainer) manualTimeContainer.style.display = tabType === 'manual' ? 'flex' : 'none';
                
                // Load detection data when detections tab is selected
                if (tabType === 'detections' && detectionData.length === 0) {
                    loadDetectionData();
                }
            });
        });
    }

    // Manual time seeking
    if (seekButton && timeInput) {
        seekButton.addEventListener('click', function() {
            const timeString = timeInput.value.trim();
            if (timeString) {
                const timeArray = timeString.split(':');
                if (timeArray.length === 2) {
                    const minutes = parseInt(timeArray[0]);
                    const seconds = parseInt(timeArray[1]);
                    const totalSeconds = minutes * 60 + seconds;
                    seekToTime(totalSeconds);
                }
            }
        });

        // Enter key for manual time input
        timeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                seekButton.click();
            }
        });
    }

    // Detection filter buttons
    if (detectionFilterBtns) {
        detectionFilterBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const filter = this.getAttribute('data-filter');
                setDetectionFilter(filter);
            });
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        switch(e.code) {
            case 'Space':
                e.preventDefault();
                togglePlayPause();
                break;
            case 'KeyM':
                e.preventDefault();
                if (volumeBtn) volumeBtn.click();
                break;
            case 'KeyF':
                e.preventDefault();
                if (fullscreenBtn) fullscreenBtn.click();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                seekRelative(-10);
                break;
            case 'ArrowRight':
                e.preventDefault();
                seekRelative(10);
                break;
            case 'KeyS':
                e.preventDefault();
                toggleSpeedDropdown();
                break;
            case 'Digit0':
                e.preventDefault();
                selectSpeed(0.25);
                break;
            case 'Digit1':
                e.preventDefault();
                selectSpeed(1);
                break;
            case 'Digit2':
                e.preventDefault();
                selectSpeed(2);
                break;
            case 'Digit4':
                e.preventDefault();
                selectSpeed(4);
                break;
            case 'Digit8':
                e.preventDefault();
                selectSpeed(8);
                break;
            case 'Digit9':
                e.preventDefault();
                selectSpeed(16);
                break;
            case 'Minus':
                e.preventDefault();
                selectSpeed(20);
                break;
        }
    });

    // Auto-hide controls
    let controlsTimeout;
    const controlsOverlay = document.querySelector('.video-controls-overlay');
    const videoContainer = document.querySelector('.video-player-container');

    function showControls() {
        if (controlsOverlay) controlsOverlay.style.opacity = '1';
        clearTimeout(controlsTimeout);
        controlsTimeout = setTimeout(() => {
            if (isPlaying && controlsOverlay) {
                controlsOverlay.style.opacity = '0';
            }
        }, 3000);
    }

    if (videoContainer) {
        videoContainer.addEventListener('mousemove', showControls);
        videoContainer.addEventListener('mouseleave', () => {
            if (isPlaying && controlsOverlay) {
                controlsOverlay.style.opacity = '0';
            }
        });
    }

    // Handle video errors
    video.addEventListener('error', function(e) {
        console.error('Video error:', e);
        hideLoading();
        
        // Try to load archive URL as fallback
        const cameraData = videoStreams[currentCamera];
        if (cameraData && cameraData.archiveUrl && video.src !== cameraData.archiveUrl) {
            console.log('Falling back to archive URL');
            showLoading('Loading fallback video...');
            video.src = cameraData.archiveUrl;
            video.load();
        } else {
            showNetworkError('Video playback error. Please try again.');
        }
    });
}

// API Functions
async function fetchDataFromAPI() {
    try {
        // Fetch video streams
        const streamsResponse = await fetch(API_ENDPOINTS.videoStreams);
        if (streamsResponse.ok) {
            const streamsData = await streamsResponse.json();
            if (streamsData.status === 'success' && Object.keys(streamsData.data).length > 0) {
                videoStreams = streamsData.data;
                console.log('Updated video streams from API:', videoStreams);
                updateVideoPlayerData();
            }
        }
        
        // Fetch detection events
        const eventsResponse = await fetch(API_ENDPOINTS.detectionEvents);
        if (eventsResponse.ok) {
            const eventsData = await eventsResponse.json();
            if (eventsData.status === 'success' && eventsData.data.length > 0) {
                detectionEvents = eventsData.data;
                console.log('Updated detection events from API:', detectionEvents);
                updateDetectionEvents();
            }
        }
    } catch (error) {
        console.error('Error fetching data from API:', error);
    }
}

// Function to update video player with new data
function updateVideoPlayerData() {
    // Recreate camera tabs with new data
    createCameraTabs();
    
    // Update current camera data
    if (currentCameraData && videoStreams[currentCamera]) {
        currentCameraData = videoStreams[currentCamera];
        initTimeNavigation();
    }
}

// Function to format time ago
function formatTimeAgo(timestamp) {
    const now = new Date();
    
    // Handle both Unix timestamps and video timestamps
    let detectionTime;
    if (timestamp > 1000000000) {
        // Unix timestamp (seconds since epoch)
        detectionTime = new Date(timestamp * 1000);
    } else {
        // Video timestamp (seconds from video start) - treat as recent
        detectionTime = new Date(Date.now() - (timestamp * 1000));
    }
    
    const diffInSeconds = Math.floor((now - detectionTime) / 1000);
    
    if (diffInSeconds < 60) {
        return 'Just now';
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} min ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 2592000) {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 31536000) {
        const months = Math.floor(diffInSeconds / 2592000);
        return `${months} month${months > 1 ? 's' : ''} ago`;
    } else {
        const years = Math.floor(diffInSeconds / 31536000);
        return `${years} year${years > 1 ? 's' : ''} ago`;
    }
}

// Function to sort detection events by timestamp (newest first)
function sortDetectionEvents(events) {
    return events.sort((a, b) => {
        // If both have timestamps, sort by timestamp (newest first)
        if (a.timestamp && b.timestamp) {
            // Handle both Unix timestamps and video timestamps
            const aTime = a.timestamp > 1000000000 ? a.timestamp : Date.now() - (a.timestamp * 1000);
            const bTime = b.timestamp > 1000000000 ? b.timestamp : Date.now() - (b.timestamp * 1000);
            return bTime - aTime;
        }
        // If only one has timestamp, prioritize the one with timestamp
        if (a.timestamp && !b.timestamp) return -1;
        if (!a.timestamp && b.timestamp) return 1;
        // If neither has timestamp, maintain original order
        return 0;
    });
}

// Function to update detection events display
function updateDetectionEvents() {
    const detectionsList = document.querySelector('.detections-list');
    if (!detectionsList) return;
    
    // Sort detection events by timestamp (newest first)
    const sortedEvents = sortDetectionEvents([...detectionEvents]);
    
    // Check if we have new detections (compare with previous count)
    const previousCount = detectionsList.children.length;
    const hasNewDetections = sortedEvents.length > previousCount;
    
    detectionsList.innerHTML = '';
    
    sortedEvents.forEach((detection, index) => {
        const detectionElement = document.createElement('div');
        detectionElement.className = 'detection-item';
        detectionElement.setAttribute('data-camera', detection.camera_id);
        detectionElement.setAttribute('data-detection-id', detection.id);
        detectionElement.setAttribute('data-timestamp', detection.timestamp);
        
        // Format time ago based on timestamp
        const timeAgo = detection.timestamp ? formatTimeAgo(detection.timestamp) : detection.time_ago;
        
        // Add highlight for new detections (first few items)
        const isNew = hasNewDetections && index < 3;
        const newClass = isNew ? 'new-detection' : '';
        
        detectionElement.innerHTML = `
            <div class="detection-thumbnail">
                <img src="${detection.thumbnail}" alt="Detection thumbnail">
                ${isNew ? '<div class="new-indicator">NEW</div>' : ''}
            </div>
            <div class="detection-info">
                <p class="camera-name">${detection.camera_name}</p>
                <p class="time-ago">${timeAgo}</p>
            </div>
            <div class="detection-time">${detection.time_label}</div>
            <div class="status-indicator status-${detection.status}"></div>
        `;
        
        // Add click event listener
        detectionElement.addEventListener('click', function() {
            const cameraId = this.getAttribute('data-camera');
            const detectionId = this.getAttribute('data-detection-id');
            const timestamp = parseInt(this.getAttribute('data-timestamp'));
            
            // Remove active class from all items
            document.querySelectorAll('.detection-item').forEach(i => i.classList.remove('active'));
            // Add active class to clicked item
            this.classList.add('active');
            
            // Update camera tab
            document.querySelectorAll('.camera-tabs button').forEach(tab => {
                if (tab.getAttribute('data-camera') === cameraId) {
                    document.querySelectorAll('.camera-tabs button').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                }
            });
            
            // Switch to camera
            currentCamera = cameraId;
            initVideoPlayerWithCamera(cameraId);
            
            // Seek to detection time if available
            if (timestamp) {
                setTimeout(() => {
                    seekToTime(timestamp);
                }, 1000);
            }
            
            console.log('Selected detection:', detectionId, 'from camera:', cameraId, 'at time:', timestamp);
        });
        
        detectionsList.appendChild(detectionElement);
    });
    
    // Show notification if new detections were added
    if (hasNewDetections) {
        showNewDetectionNotification(sortedEvents.length - previousCount);
    }
}

// Function to show new detection notification
function showNewDetectionNotification(count) {
    // Create or update notification
    let notification = document.getElementById('newDetectionNotification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'newDetectionNotification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--accent-red);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(notification);
    }
    
    notification.textContent = `🆕 ${count} new detection${count > 1 ? 's' : ''} added`;
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, 3000);
}

// Function to start real-time updates
function startRealTimeUpdates(interval = 5000) {
    if (dataUpdateInterval) {
        clearInterval(dataUpdateInterval);
    }
    
    isRealTimeMode = true;
    dataUpdateInterval = setInterval(fetchDataFromAPI, interval);
    console.log('Started real-time updates every', interval, 'ms');
}

// Function to stop real-time updates
function stopRealTimeUpdates() {
    if (dataUpdateInterval) {
        clearInterval(dataUpdateInterval);
        dataUpdateInterval = null;
    }
    isRealTimeMode = false;
    console.log('Stopped real-time updates');
}

// Function to add a detection event via API
async function addDetectionEvent(detectionData) {
    try {
        const response = await fetch(API_ENDPOINTS.addDetection, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(detectionData)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Detection event added:', result);
            return true;
        } else {
            console.error('Failed to add detection event:', response.status);
            return false;
        }
    } catch (error) {
        console.error('Error adding detection event:', error);
        return false;
    }
}

// Function to update camera data via API
async function updateCameraData(cameraId, updateData) {
    try {
        const response = await fetch(API_ENDPOINTS.updateCamera + cameraId + '/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Camera updated:', result);
            return true;
        } else {
            console.error('Failed to update camera:', response.status);
            return false;
        }
    } catch (error) {
        console.error('Error updating camera:', error);
        return false;
    }
}

// Initialize API controls
function initAPIControls() {
    if (toggleRealTimeBtn) {
        // Set initial state to ON (checked)
        isRealTimeMode = true;
        toggleRealTimeBtn.checked = true;
        startRealTimeUpdates(5000); // Start real-time updates
        
        toggleRealTimeBtn.addEventListener('change', () => {
            if (toggleRealTimeBtn.checked) {
                // Turn ON
                isRealTimeMode = true;
                startRealTimeUpdates(5000); // Update every 5 seconds
                if (apiStatus) apiStatus.textContent = 'API: Real-time active';
                console.log('Real-time updates: ON');
            } else {
                // Turn OFF
                isRealTimeMode = false;
                stopRealTimeUpdates();
                if (apiStatus) apiStatus.textContent = 'API: Real-time stopped';
                console.log('Real-time updates: OFF');
            }
        });
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing video player...');
    
    // Initialize global data from window context
    initializeGlobalData();
    
    // Check if we have video streams data
    if (!videoStreams || Object.keys(videoStreams).length === 0) {
        console.warn('No video streams available, showing no sources message');
        return;
    }
    
    console.log('Found video streams:', videoStreams);
    console.log('Current camera:', currentCamera);
    
    // Initialize video player
    initVideoPlayer();
    
    // Initialize API controls
    initAPIControls();
    
    // Initial data fetch
    fetchDataFromAPI();
    
    // Real-time updates will be controlled by the toggle button
});

// Export functions for global access
window.VideoPlayer = {
    initVideoPlayer,
    togglePlayPause,
    seekToTime,
    seekRelative,
    changeSpeed,
    startRealTimeUpdates,
    stopRealTimeUpdates,
    fetchDataFromAPI,
    addDetectionEvent,
    updateCameraData
}; 