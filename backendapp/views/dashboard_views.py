"""
Dashboard Views Module
Handles main dashboard and backend functionality
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from datetime import date
import logging

from ..forms import TargetsWatchlistForm
from ..models import TargetPhoto, Targets_watchlist, Case

logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    """Main dashboard view with statistics and recent activity"""
    total_targets = Targets_watchlist.objects.count()
    total_cases = Case.objects.count()
    total_images = TargetPhoto.objects.count()
    recent_targets = Targets_watchlist.objects.select_related('case').order_by('-created_at')[:5]
    
    # Status distribution for chart
    status_counts = list(Targets_watchlist.objects.values('case_status').annotate(count=Count('id')))
    gender_counts = list(Targets_watchlist.objects.values('gender').annotate(count=Count('id')))
    recent_cases = Case.objects.select_related('created_by').order_by('-created_at')[:5]

    # Monthly trend data (last 7 months including current)
    def add_months(d, months):
        year = d.year + (d.month - 1 + months) // 12
        month = (d.month - 1 + months) % 12 + 1
        day = min(d.day, 28)  # avoid end-of-month pitfalls
        return date(year, month, day)

    now = timezone.now().date()
    months_labels = []
    targets_month_counts = []
    cases_month_counts = []
    images_month_counts = []
    
    for i in range(6, -1, -1):  # 7 points
        mdate = add_months(now.replace(day=1), -i)
        months_labels.append(mdate.strftime('%b %Y'))
        targets_month_counts.append(
            Targets_watchlist.objects.filter(created_at__year=mdate.year, created_at__month=mdate.month).count()
        )
        cases_month_counts.append(
            Case.objects.filter(created_at__year=mdate.year, created_at__month=mdate.month).count()
        )
        images_month_counts.append(
            TargetPhoto.objects.filter(uploaded_at__year=mdate.year, uploaded_at__month=mdate.month).count()
        )
    
    return render(request, 'dashboard.html', {
        'total_targets': total_targets,
        'total_cases': total_cases,
        'total_images': total_images,
        'recent_targets': recent_targets,
        'status_counts': status_counts,
        'gender_counts': gender_counts,
        'recent_cases': recent_cases,
        'months_labels': months_labels,
        'targets_month_counts': targets_month_counts,
        'cases_month_counts': cases_month_counts,
        'images_month_counts': images_month_counts,
    })

@login_required
def backend(request):
    """Backend view for adding targets to watchlist"""
    if request.method == 'POST':
        form = TargetsWatchlistForm(request.POST, request.FILES)
        if form.is_valid():
            watchlist = form.save(commit=False)
            watchlist.created_by = request.user
            watchlist.save()
            
            try:
                from notifications.signals import notify
                notify.send(request.user, recipient=watchlist.created_by, verb='added target', target=watchlist)
            except Exception:
                pass
            
            # Handle multiple image uploads using validated files from the form
            images = form.cleaned_data.get('images') or []
            uploaded_count = 0
            for image in images:
                if getattr(image, 'name', None):
                    try:
                        TargetPhoto.objects.create(person=watchlist, image=image, uploaded_by=request.user)
                        uploaded_count += 1
                        try:
                            notify.send(request.user, recipient=watchlist.created_by, verb='uploaded images', target=watchlist, action_object=watchlist)
                        except Exception:
                            pass
                    except Exception as e:
                        messages.error(request, f'Failed to upload {getattr(image, "name", "image")}: {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, 'Target added successfully with images!')
            else:
                messages.warning(request, 'Target added, but no images were uploaded.')
            return redirect('list_watchlist')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TargetsWatchlistForm()
    return render(request, 'add_watchlist.html', {'form': form})
