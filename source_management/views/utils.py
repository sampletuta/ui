"""
Utility functions and decorators for source management views
"""

import os
import re
from django.shortcuts import redirect
from django.http import HttpResponse, StreamingHttpResponse, FileResponse


def _range_streaming_response(request, file_path, content_type='video/mp4', chunk_size=8192):
    """Efficient HTTP range streaming helper for large files."""
    file_size = os.path.getsize(file_path)
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
        if start >= file_size:
            return HttpResponse(status=416)

        def file_iterator(path, start_pos, end_pos, block_size=chunk_size):
            with open(path, 'rb') as f:
                f.seek(start_pos)
                remaining = end_pos - start_pos + 1
                while remaining > 0:
                    data = f.read(min(block_size, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        response = StreamingHttpResponse(file_iterator(file_path, start, end), content_type=content_type)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = str(end - start + 1)
        response.status_code = 206
        return response

    # Full-file streaming using FileResponse for optimal performance
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = str(file_size)
    return response


def login_required_source_list(view_func):
    """Decorator to require login for source list views"""
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return _wrapped_view

