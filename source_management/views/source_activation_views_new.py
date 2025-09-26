"""
Source Activation Views Module
Handles source activation/deactivation using the Source Management Service
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import logging

from ..services import SourceManagementService, VideoProcessingService
from ..forms import SourceActivationForm

logger = logging.getLogger(__name__)

class SourceActivationView(View):
    """Base class for source activation/deactivation using Source Management Service"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_service = SourceManagementService()

    def get_source(self, source_id, source_type):
        """Get the source data from the service"""
        result = self.source_service.get_source(source_id)
        if not result['success']:
            return None
        return result['data']

    def handle_activation_change(self, source_id, new_status, source_type):
        """Handle the activation status change using the API"""
        try:
            if new_status:
                result = self.source_service.activate_source(source_id)
            else:
                result = self.source_service.deactivate_source(source_id)

            if result['success']:
                # Log the change
                action = "activated" if new_status else "deactivated"
                logger.info(f"Source {source_type} {source_id} {action} by user")

                # Handle stream processor integration for camera and stream sources
                if source_type in ['camera', 'stream']:
                    try:
                        source = self.get_source(source_id, source_type)
                        if source and new_status:
                            # Activate: Create or start stream in processor
                            if hasattr(source, '_create_in_stream_processor'):
                                source._create_in_stream_processor()
                            if hasattr(source, 'start_processor_stream'):
                                source.start_processor_stream()
                        elif source and not new_status:
                            # Deactivate: Stop and remove stream from processor
                            if hasattr(source, '_delete_from_stream_processor'):
                                source._delete_from_stream_processor()
                            if hasattr(source, 'stop_processor_stream'):
                                source.stop_processor_stream()
                    except Exception as e:
                        logger.warning(f"Error in stream processor integration: {e}")

                return {'success': True}
            else:
                return {'success': False, 'error': result.get('error')}

        except Exception as e:
            logger.error(f"Error in activation change for {source_type} {source_id}: {e}")
            return {'success': False, 'error': str(e)}

@method_decorator(login_required, name='dispatch')
class ActivateSourceView(SourceActivationView):
    """Activate a source"""

    def post(self, request, source_id, source_type):
        """Activate a source using the API"""
        try:
            result = self.handle_activation_change(source_id, True, source_type)

            if result['success']:
                messages.success(request, f"{source_type.title()} source activated successfully!")
                return redirect('source_management:source_detail', source_id=source_id)
            else:
                messages.error(request, f"Error activating {source_type} source: {result.get('error')}")
                return redirect('source_management:source_list')

        except Exception as e:
            logger.error(f"Error activating {source_type} source {source_id}: {e}")
            messages.error(request, f"Error activating {source_type} source: {str(e)}")
            return redirect('source_management:source_list')

@method_decorator(login_required, name='dispatch')
class DeactivateSourceView(SourceActivationView):
    """Deactivate a source"""

    def post(self, request, source_id, source_type):
        """Deactivate a source using the API"""
        try:
            result = self.handle_activation_change(source_id, False, source_type)

            if result['success']:
                messages.success(request, f"{source_type.title()} source deactivated successfully!")
                return redirect('source_management:source_detail', source_id=source_id)
            else:
                messages.error(request, f"Error deactivating {source_type} source: {result.get('error')}")
                return redirect('source_management:source_list')

        except Exception as e:
            logger.error(f"Error deactivating {source_type} source {source_id}: {e}")
            messages.error(request, f"Error deactivating {source_type} source: {str(e)}")
            return redirect('source_management:source_list')

@method_decorator(login_required, name='dispatch')
class ToggleSourceActivationView(SourceActivationView):
    """Toggle source activation status"""

    def post(self, request, source_id, source_type):
        """Toggle source activation status using the API"""
        try:
            # Get current status
            source = self.get_source(source_id, source_type)
            if not source:
                messages.error(request, f"{source_type.title()} source not found")
                return redirect('source_management:source_list')

            current_status = source.get('is_active', False)
            new_status = not current_status

            result = self.handle_activation_change(source_id, new_status, source_type)

            if result['success']:
                action = "activated" if new_status else "deactivated"
                messages.success(request, f"{source_type.title()} source {action} successfully!")
                return redirect('source_management:source_detail', source_id=source_id)
            else:
                messages.error(request, f"Error toggling {source_type} source: {result.get('error')}")
                return redirect('source_management:source_list')

        except Exception as e:
            logger.error(f"Error toggling {source_type} source {source_id}: {e}")
            messages.error(request, f"Error toggling {source_type} source: {str(e)}")
            return redirect('source_management:source_list')

@method_decorator(login_required, name='dispatch')
class BulkActivationView(SourceActivationView):
    """Bulk activate/deactivate multiple sources"""

    def post(self, request, source_type):
        """Bulk activate/deactivate sources using the API"""
        try:
            source_ids = request.POST.getlist('source_ids')
            action = request.POST.get('action')  # 'activate' or 'deactivate'

            if not source_ids:
                messages.error(request, 'No sources selected')
                return redirect('source_management:source_list')

            if action not in ['activate', 'deactivate']:
                messages.error(request, 'Invalid action')
                return redirect('source_management:source_list')

            new_status = action == 'activate'
            success_count = 0
            error_count = 0

            for source_id in source_ids:
                try:
                    result = self.handle_activation_change(source_id, new_status, source_type)
                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"Error {action}ing source {source_id}: {result.get('error')}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Exception {action}ing source {source_id}: {e}")

            if success_count > 0:
                messages.success(request,
                    f"Successfully {action}d {success_count} {source_type} source(s)" +
                    (f" ({error_count} errors)" if error_count > 0 else "")
                )

            if error_count > 0:
                messages.warning(request, f"Failed to {action} {error_count} source(s)")

            return redirect('source_management:source_list')

        except Exception as e:
            logger.error(f"Error in bulk {action}ion: {e}")
            messages.error(request, f"Error in bulk {action}ion: {str(e)}")
            return redirect('source_management:source_list')

@login_required
def source_activation_confirmation(request, source_id, source_type, action):
    """Show confirmation form for source activation/deactivation"""
    source_service = SourceManagementService()

    try:
        result = source_service.get_source(source_id)

        if result['success']:
            source = result['data']

            if request.method == 'POST':
                form = SourceActivationForm(request.POST)
                if form.is_valid():
                    new_status = action == 'activate'

                    result = source_service.activate_source(source_id) if new_status else source_service.deactivate_source(source_id)

                    if result['success']:
                        status_msg = "activated" if new_status else "deactivated"
                        messages.success(request, f"{source_type.title()} source {status_msg} successfully!")
                        return redirect('source_management:source_detail', source_id=source_id)
                    else:
                        messages.error(request, f"Error {action}ing source: {result.get('error')}")
                else:
                    messages.error(request, 'Please correct the form errors.')
            else:
                form = SourceActivationForm(initial={
                    'source_id': source_id,
                    'source_type': source_type,
                    'action': action,
                    'source_name': source.get('name', 'Unknown')
                })

            context = {
                'form': form,
                'source': source,
                'source_type': source_type,
                'action': action,
                'title': f"{action.title()} Source Confirmation",
                'confirmation_message': f"Are you sure you want to {action} this {source_type} source?"
            }

            return render(request, 'source_management/source_activation_confirm.html', context)
        else:
            messages.error(request, f'Error retrieving source: {result.get("error")}')
            return redirect('source_management:source_list')

    except Exception as e:
        logger.error(f"Error in source activation confirmation {source_id}: {e}")
        messages.error(request, f'Error retrieving source: {str(e)}')
        return redirect('source_management:source_list')

@login_required
@require_POST
def confirm_source_activation(request):
    """Confirm source activation/deactivation"""
    form = SourceActivationForm(request.POST)

    if form.is_valid():
        source_id = form.cleaned_data['source_id']
        source_type = form.cleaned_data['source_type']
        action = form.cleaned_data['action']
        new_status = action == 'activate'

        try:
            source_service = SourceManagementService()
            result = source_service.activate_source(source_id) if new_status else source_service.deactivate_source(source_id)

            if result['success']:
                status_msg = "activated" if new_status else "deactivated"
                messages.success(request, f"{source_type.title()} source {status_msg} successfully!")
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': result.get('error')})

        except Exception as e:
            logger.error(f"Error confirming source activation: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid form data'})
