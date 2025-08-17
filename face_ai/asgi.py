"""
ASGI config for face_ai application.

This module enables async/await support and parallel processing for face recognition operations.
"""

import os
import asyncio
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from . import async_views

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Get Django ASGI application
django_asgi_app = get_asgi_application()

# This file is now used for configuration only
# The main ASGI routing is handled in backend/asgi.py

# For development/testing, you can still run this directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.asgi:application",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )

# For development/testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "face_ai.asgi:application",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
