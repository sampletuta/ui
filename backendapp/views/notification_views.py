"""
Notification Views Module
Handles notification management, marking as read, and deletion
"""

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from datetime import timedelta
import logging

from notifications.models import Notification

logger = logging.getLogger(__name__)

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user and redirect back."""
    try:
        request.user.notifications.unread().mark_all_as_read()
    except Exception:
        try:
            Notification.objects.filter(recipient=request.user, unread=True).update(unread=False)
        except Exception:
            pass
    next_url = request.META.get('HTTP_REFERER') or '/inbox/notifications/'
    return redirect(next_url)

@login_required
@require_POST
def mark_notification_read(request):
    """Mark a single notification as read for the current user (AJAX)."""
    notification_id = request.POST.get('id') or request.POST.get('notification_id')
    if not notification_id:
        return JsonResponse({'success': False, 'error': 'Missing id'}, status=400)
    
    try:
        nid = int(notification_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid id'}, status=400)
    
    try:
        notification = Notification.objects.get(id=nid, recipient=request.user)
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    
    try:
        notification.mark_as_read()
    except Exception:
        try:
            notification.unread = False
            notification.save(update_fields=['unread'])
        except Exception:
            return JsonResponse({'success': False, 'error': 'Failed to mark as read'}, status=500)
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def clear_notifications(request):
    """Bulk clear notifications for the current user.
    Actions:
      - action=all: delete all notifications
      - action=read: delete only read notifications
      - action=older_than_days&days=N: delete notifications older than N days
      - action=keep_latest&keep=N&scope=all|read: keep latest N (by timestamp desc), delete the rest in scope
    """
    action = request.POST.get('action')
    if not action:
        return JsonResponse({'success': False, 'error': 'Missing action'}, status=400)
    
    qs = Notification.objects.filter(recipient=request.user)
    
    try:
        if action == 'all':
            deleted, _ = qs.delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        
        if action == 'read':
            deleted, _ = qs.filter(unread=False).delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        
        if action == 'older_than_days':
            days_raw = request.POST.get('days')
            try:
                days = int(days_raw)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Invalid days'}, status=400)
            cutoff = timezone.now() - timedelta(days=days)
            deleted, _ = qs.filter(timestamp__lt=cutoff).delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        
        if action == 'keep_latest':
            keep_raw = request.POST.get('keep')
            scope = (request.POST.get('scope') or 'read').lower()
            try:
                keep = int(keep_raw)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Invalid keep'}, status=400)
            
            scope_qs = qs if scope == 'all' else qs.filter(unread=False)
            ids_to_keep = list(scope_qs.order_by('-timestamp').values_list('id', flat=True)[:keep])
            
            if not ids_to_keep:
                # nothing to keep; delete per scope
                deleted, _ = scope_qs.delete()
                return JsonResponse({'success': True, 'deleted': deleted})
            
            deleted, _ = scope_qs.exclude(id__in=ids_to_keep).delete()
            return JsonResponse({'success': True, 'deleted': deleted})
        
        return JsonResponse({'success': False, 'error': 'Unknown action'}, status=400)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def delete_notification(request):
    """Delete a single notification for the current user (hard delete)."""
    notification_id = request.POST.get('id') or request.POST.get('notification_id')
    if not notification_id:
        return JsonResponse({'success': False, 'error': 'Missing id'}, status=400)
    
    try:
        nid = int(notification_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid id'}, status=400)
    
    try:
        deleted, _ = Notification.objects.filter(id=nid, recipient=request.user).delete()
        if deleted:
            return JsonResponse({'success': True, 'deleted': deleted})
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def notifications_list(request):
    """List notifications for the current user."""
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
    
    return render(request, 'notifications_list.html', {
        'notifications': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_range': page_range,
        'per_page': per_page,
    })

@login_required
def notification_detail(request, notification_id):
    """Detail page for a single notification; marks as read and shows metadata."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    if notification.unread:
        try:
            notification.mark_as_read()
        except Exception:
            pass
    
    return render(request, 'notification_detail.html', {
        'notification': notification,
    })
