"""
Enhanced Notification Views with Alert Aggregation Support
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta
import logging

from notifications.models import Notification
from backendapp.utils.alert_deduplication import deduplication_service

logger = logging.getLogger(__name__)


@login_required
def notifications_list(request):
    """Enhanced notifications list with deduplication stats"""
    notifications_qs = Notification.objects.filter(recipient=request.user).order_by('-timestamp')
    
    per_page_default = 20
    try:
        per_page = int(request.GET.get('per_page', per_page_default))
    except (TypeError, ValueError):
        per_page = per_page_default
    
    paginator = Paginator(notifications_qs, per_page)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    
    current = page_obj.number
    total = paginator.num_pages
    start = max(1, current - 2)
    end = min(total, current + 2)
    page_range = list(range(start, end + 2))
    
    # Get deduplication stats for admin users
    deduplication_stats = None
    if request.user.is_staff:
        try:
            deduplication_stats = deduplication_service.get_deduplication_stats()
        except Exception as e:
            logger.error(f"Error getting deduplication stats: {e}")
    
    return render(request, 'notifications_list.html', {
        'notifications': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_range': page_range,
        'per_page': per_page,
        'deduplication_stats': deduplication_stats,
    })


@login_required
def notification_detail(request, notification_id):
    """Enhanced notification detail with deduplication context"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    if notification.unread:
        try:
            notification.mark_as_read()
        except Exception:
            pass
    
    # Get related notifications for context (same target, recent timeframe)
    related_notifications = []
    if hasattr(notification, 'target') and notification.target:
        try:
            related_notifications = Notification.objects.filter(
                recipient=request.user,
                target=notification.target,
                timestamp__gte=notification.timestamp - timedelta(hours=1),
                timestamp__lte=notification.timestamp + timedelta(hours=1)
            ).exclude(id=notification.id).order_by('-timestamp')[:5]
        except Exception as e:
            logger.error(f"Error getting related notifications: {e}")
    
    return render(request, 'notification_detail.html', {
        'notification': notification,
        'related_notifications': related_notifications,
    })


@login_required
@require_POST
def configure_deduplication(request):
    """Configure deduplication settings (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        import json
        data = json.loads(request.body) if request.body else {}
        
        # Update settings (this would typically be done through admin interface)
        # For now, we'll just return the current settings
        current_settings = deduplication_service.get_deduplication_stats()
        
        return JsonResponse({
            'success': True,
            'current_settings': current_settings,
            'message': 'Settings retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error configuring deduplication: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def deduplication_stats(request):
    """Get deduplication statistics (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        stats = deduplication_service.get_deduplication_stats()
        
        # Add additional stats if available
        stats.update({
            'cache_backend': 'Redis' if hasattr(request, 'cache') else 'Database',
            'timestamp': timezone.now().isoformat(),
        })
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting deduplication stats: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

