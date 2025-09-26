"""
Source List Views Module
Handles source listing and filtering using the Source Management Service
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .decorators import login_required_source_list
from ..services import SourceManagementService

logger = logging.getLogger(__name__)

@login_required_source_list
def source_list(request):
    """List sources using the Source Management Service"""
    source_service = SourceManagementService()

    # Get filter parameters
    source_type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    zone_filter = request.GET.get('zone', '')
    page_number = request.GET.get('page', 1)

    try:
        # Build filters for API call
        filters = {}
        if source_type_filter:
            filters['type'] = source_type_filter
        if status_filter:
            filters['is_active'] = status_filter == 'active'
        if zone_filter:
            filters['zone'] = zone_filter

        # Get sources from API
        result = source_service.get_sources(filters)

        if result['success']:
            sources = result['data']

            # Apply client-side search filtering
            if search_query:
                search_lower = search_query.lower()
                sources = [
                    source for source in sources
                    if (search_lower in source.get('name', '').lower() or
                        search_lower in source.get('description', '').lower() or
                        search_lower in source.get('location', '').lower())
                ]

            # Pagination
            paginator = Paginator(sources, 20)  # 20 sources per page
            page_obj = paginator.get_page(page_number)

            # Get unique zones for filter dropdown
            zones = sorted(set(
                source.get('configuration', {}).get('zone', '')
                for source in sources
                if source.get('configuration', {}).get('zone')
            ))

            # Statistics
            total_sources = len(sources)
            active_sources = sum(1 for source in sources if source.get('is_active', True))
            camera_sources = sum(1 for source in sources if source.get('type') == 'camera')
            stream_sources = sum(1 for source in sources if source.get('type') == 'stream')
            file_sources = sum(1 for source in sources if source.get('type') == 'file')

            context = {
                'page_obj': page_obj,
                'sources': page_obj,
                'source_type_filter': source_type_filter,
                'status_filter': status_filter,
                'search_query': search_query,
                'zone_filter': zone_filter,
                'zones': zones,
                'total_sources': total_sources,
                'active_sources': active_sources,
                'camera_sources': camera_sources,
                'stream_sources': stream_sources,
                'file_sources': file_sources,
                'title': 'Source Management'
            }

            return render(request, 'source_management/source_list.html', context)
        else:
            logger.error(f"Error getting sources from API: {result.get('error')}")
            messages.error(request, f'Error retrieving sources: {result.get("error")}')
            return render(request, 'source_management/source_list.html', {
                'sources': [],
                'title': 'Source Management'
            })

    except Exception as e:
        logger.error(f"Error in source list: {e}")
        messages.error(request, f'Error retrieving sources: {str(e)}')
        return render(request, 'source_management/source_list.html', {
            'sources': [],
            'title': 'Source Management'
        })

@login_required_source_list
def dashboard(request):
    """Dashboard view using the Source Management Service"""
    source_service = SourceManagementService()

    try:
        # Get all sources for dashboard statistics
        result = source_service.get_sources()

        if result['success']:
            sources = result['data']

            # Calculate statistics
            total_sources = len(sources)
            active_sources = sum(1 for source in sources if source.get('is_active', True))
            camera_sources = sum(1 for source in sources if source.get('type') == 'camera')
            stream_sources = sum(1 for source in sources if source.get('type') == 'stream')
            file_sources = sum(1 for source in sources if source.get('type') == 'file')

            # Get recent sources (last 5)
            recent_sources = sorted(sources, key=lambda x: x.get('created_at', ''), reverse=True)[:5]

            # Get sources by zone
            zone_stats = {}
            for source in sources:
                zone = source.get('configuration', {}).get('zone', 'Unassigned')
                if zone not in zone_stats:
                    zone_stats[zone] = {'total': 0, 'active': 0}
                zone_stats[zone]['total'] += 1
                if source.get('is_active', True):
                    zone_stats[zone]['active'] += 1

            # Service health check
            service_health = source_service.health()

            context = {
                'total_sources': total_sources,
                'active_sources': active_sources,
                'camera_sources': camera_sources,
                'stream_sources': stream_sources,
                'file_sources': file_sources,
                'recent_sources': recent_sources,
                'zone_stats': zone_stats,
                'service_health': service_health,
                'title': 'Source Management Dashboard'
            }

            return render(request, 'source_management/dashboard.html', context)
        else:
            logger.error(f"Error getting sources for dashboard: {result.get('error')}")
            messages.error(request, f'Error loading dashboard: {result.get("error")}')
            return render(request, 'source_management/dashboard.html', {
                'total_sources': 0,
                'active_sources': 0,
                'camera_sources': 0,
                'stream_sources': 0,
                'file_sources': 0,
                'recent_sources': [],
                'zone_stats': {},
                'title': 'Source Management Dashboard'
            })

    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'source_management/dashboard.html', {
            'total_sources': 0,
            'active_sources': 0,
            'camera_sources': 0,
            'stream_sources': 0,
            'file_sources': 0,
            'recent_sources': [],
            'zone_stats': {},
            'title': 'Source Management Dashboard'
        })
