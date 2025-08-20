"""
Decorators Module
Contains custom decorators for authentication and access control
"""

from django.shortcuts import redirect

def login_required_source_list(view_func):
    """Custom decorator for source list authentication"""
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return _wrapped_view


