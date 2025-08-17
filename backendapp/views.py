"""
Views Module - Refactored for Better Organization

This file now imports all views from the organized views package.
The original large views.py file has been broken down into logical modules:

- auth_views.py: Authentication and user management
- dashboard_views.py: Dashboard and main functionality  
- target_views.py: Target management and operations
- case_views.py: Case management
- search_views.py: Search functionality
- face_verification_views.py: Face verification services
- notification_views.py: Notification management
- user_management_views.py: User administration
- utils.py: Utility functions and helpers

All views are imported below to maintain backward compatibility.
"""

# Import all views from the organized modules
from .views import *

# This maintains backward compatibility - all existing imports will continue to work
