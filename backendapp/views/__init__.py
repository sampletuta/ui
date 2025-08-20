# Views Package - Import all view functions for backward compatibility

# Authentication Views
from .auth_views import (
    login,
    custom_login,
    logout_view,
    logout,
    signup,
    profile,
    settings_view,
    handle_failed_login,
    handle_successful_login,
)

# Dashboard Views
from .dashboard_views import (
    dashboard,
    backend,
)

# Target Management Views
from .target_views import (
    list_watchlist,
    target_profile,
    edit_target,
    delete_target,
    add_images,
    delete_image,
)

# Case Management Views
from .case_views import (
    case_list,
    case_create,
    case_detail,
    case_edit,
    case_delete,
    add_target_to_case,
)

# Search Views
from .search_views import (
    advanced_search,
    quick_search,
    milvus_search,
    search_results_advanced,
    search_history,
    video_face_search,
    start_video_face_search,
    search_status,
    search_results,
    upload_chunk,
    milvus_search_legacy,
)

# Face Verification Views
from .face_verification_views import (
    face_verification,
    face_verification_preview,
    face_verification_watchlist,
    handle_mode1_verification,
    handle_mode2_verification,
)

# Notification Views
from .notification_views import (
    mark_all_notifications_read,
    mark_notification_read,
    clear_notifications,
    delete_notification,
    notifications_list,
    notification_detail,
)

# User Management Views
from .user_management_views import (
    user_list,
    user_create,
    user_update,
    user_delete,
    user_unlock,
    user_profile,
    api_user_status,
)



# Utility Views and Functions
from .utils import (
    is_admin,
    is_case_manager,
    is_operator,
    is_staff_or_admin,
    create_search_map,
    create_results_map,
    haversine_distance,
    execute_advanced_search,
    execute_quick_search,
)

# Make all views available at package level
__all__ = [
    # Authentication
    'login', 'custom_login', 'logout_view', 'logout', 'signup', 'profile', 'settings_view',
    'handle_failed_login', 'handle_successful_login',
    
    # Dashboard
    'dashboard', 'backend',
    
    # Target Management
    'list_watchlist', 'target_profile', 'edit_target', 'delete_target', 'add_images', 'delete_image',
    
    # Case Management
    'case_list', 'case_create', 'case_detail', 'case_edit', 'case_delete', 'add_target_to_case',
    
    # Search
    'advanced_search', 'quick_search', 'milvus_search', 'search_results_advanced', 'search_history',
    'video_face_search', 'start_video_face_search', 'search_status', 'search_results', 'upload_chunk',
    'milvus_search_legacy',
    
    # Face Verification
    'face_verification', 'face_verification_preview', 'face_verification_watchlist',
    'handle_mode1_verification', 'handle_mode2_verification',
    
    # Notifications
    'mark_all_notifications_read', 'mark_notification_read', 'clear_notifications',
    'delete_notification', 'notifications_list', 'notification_detail',
    
    # User Management
    'user_list', 'user_create', 'user_update', 'user_delete', 'user_unlock', 'user_profile', 'api_user_status',
    
    # Utilities
    'is_admin', 'is_case_manager', 'is_operator', 'is_staff_or_admin',
    'create_search_map', 'create_results_map', 'haversine_distance',
    'execute_advanced_search', 'execute_quick_search',
]
