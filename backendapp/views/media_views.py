"""
Media serving views for development when DEBUG=False
"""
import os
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods


@never_cache
@require_http_methods(["GET"])
def serve_media(request, path):
    """
    Serve media files when DEBUG=False
    This is a simple implementation for development purposes only.
    In production, use Nginx or another web server to serve media files.
    """
    # Security check: ensure the path is within media directory
    media_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Normalize the path to prevent directory traversal attacks
    media_path = os.path.normpath(media_path)
    media_root = os.path.normpath(settings.MEDIA_ROOT)
    
    if not media_path.startswith(media_root):
        raise Http404("File not found")
    
    if not os.path.exists(media_path) or not os.path.isfile(media_path):
        raise Http404("File not found")
    
    # Get file extension for content type
    _, ext = os.path.splitext(media_path)
    ext = ext.lower()
    
    # Set content type based on file extension
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
    }
    
    content_type = content_types.get(ext, 'application/octet-stream')
    
    # Read and serve the file
    try:
        with open(media_path, 'rb') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type=content_type)
        response['Content-Length'] = len(content)
        
        # Add cache headers
        response['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
        
        return response
        
    except (IOError, OSError):
        raise Http404("File not found")
