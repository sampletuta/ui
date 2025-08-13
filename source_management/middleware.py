from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler
from .upload_handlers import VideoFileUploadHandler

class LargeFileUploadMiddleware:
    """
    Middleware to handle large file uploads by configuring custom upload handlers.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check if this is a file upload request
        if request.method == 'POST' and 'video_file' in request.FILES:
            # Configure custom upload handler for video files
            request.upload_handlers = [VideoFileUploadHandler(request)]
            
        response = self.get_response(request)
        return response

class UploadProgressMiddleware:
    """
    Middleware to track upload progress for large files.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Add upload progress tracking for large files
        if request.method == 'POST' and request.content_type and 'multipart/form-data' in request.content_type:
            # Set up progress tracking
            request.upload_progress = {
                'bytes_received': 0,
                'total_size': 0,
                'percentage': 0
            }
            
        response = self.get_response(request)
        return response 