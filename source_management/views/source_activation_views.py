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
                    source._create_in_stream_processor()
                    if hasattr(source, 'start_processor_stream'):
                        source.start_processor_stream()
                else:
                    # Deactivate: Stop and remove stream from processor
                    if hasattr(source, 'stop_processor_stream'):
                        source.stop_processor_stream()
                    source._delete_from_stream_processor()
            except Exception as e:
                logger.error(f"Error handling stream processor integration for {source_type} {source.source_id}: {e}")
                # Don't fail the activation/deactivation if stream processor fails
        
        return {
            'success': True,
            'old_status': old_status,
            'new_status': new_status,
            'action': action
        }

@method_decorator(login_required, name='dispatch')
class ActivateSourceView(SourceActivationView):
    """Activate a source"""
    
    def post(self, request, source_id, source_type):
        try:
            source = self.get_source(source_id, source_type)
            
            if source.is_active:
                return JsonResponse({
                    'success': False,
                    'error': 'Source is already active'
                })
            
            result = self.handle_activation_change(source, True, source_type)
            
            messages.success(request, f"{source_type.title()} source '{source.name}' has been activated successfully.")
            
            return JsonResponse({
                'success': True,
                'message': f"{source_type.title()} source activated successfully",
                'source_id': str(source.source_id),
                'source_name': source.name,
                'is_active': source.is_active
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Error activating {source_type} source {source_id}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while activating the source'
            })

@method_decorator(login_required, name='dispatch')
class DeactivateSourceView(SourceActivationView):
    """Deactivate a source"""
    
    def post(self, request, source_id, source_type):
        try:
            source = self.get_source(source_id, source_type)
            
            if not source.is_active:
                return JsonResponse({
                    'success': False,
                    'error': 'Source is already inactive'
                })
            
            result = self.handle_activation_change(source, False, source_type)
            
            messages.success(request, f"{source_type.title()} source '{source.name}' has been deactivated successfully.")
            
            return JsonResponse({
                'success': True,
                'message': f"{source_type.title()} source deactivated successfully",
                'source_id': str(source.source_id),
                'source_name': source.name,
                'is_active': source.is_active
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Error deactivating {source_type} source {source_id}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while deactivating the source'
            })

@method_decorator(login_required, name='dispatch')
class ToggleSourceActivationView(SourceActivationView):
    """Toggle source activation status"""
    
    def post(self, request, source_id, source_type):
        try:
            source = self.get_source(source_id, source_type)
            new_status = not source.is_active
            
            result = self.handle_activation_change(source, new_status, source_type)
            
            action = "activated" if new_status else "deactivated"
            messages.success(request, f"{source_type.title()} source '{source.name}' has been {action} successfully.")
            
            return JsonResponse({
                'success': True,
                'message': f"{source_type.title()} source {action} successfully",
                'source_id': str(source.source_id),
                'source_name': source.name,
                'is_active': source.is_active,
                'action': action
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Error toggling {source_type} source {source_id}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while toggling the source status'
            })

@method_decorator(login_required, name='dispatch')
class BulkActivationView(SourceActivationView):
    """Bulk activate/deactivate multiple sources"""
    
    def post(self, request, source_type):
        try:
            source_ids = request.POST.getlist('source_ids[]')
            action = request.POST.get('action')  # 'activate' or 'deactivate'
            
            if not source_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'No sources selected'
                })
            
            if action not in ['activate', 'deactivate']:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid action. Must be "activate" or "deactivate"'
                })
            
            model_class = self.get_source_model(source_type)
            if not model_class:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid source type: {source_type}'
                })
            
            new_status = action == 'activate'
            updated_sources = []
            errors = []
            
            for source_id in source_ids:
                try:
                    source = get_object_or_404(model_class, source_id=source_id)
                    
                    # Skip if already in desired state
                    if source.is_active == new_status:
                        continue
                    
                    result = self.handle_activation_change(source, new_status, source_type)
                    updated_sources.append({
                        'source_id': str(source.source_id),
                        'source_name': source.name,
                        'is_active': source.is_active
                    })
                    
                except Exception as e:
                    logger.error(f"Error updating {source_type} source {source_id}: {e}")
                    errors.append(f"Failed to update {source_id}: {str(e)}")
            
            action_past = "activated" if new_status else "deactivated"
            messages.success(request, f"{len(updated_sources)} {source_type} sources have been {action_past} successfully.")
            
            if errors:
                messages.warning(request, f"Some sources could not be updated: {'; '.join(errors)}")
            
            return JsonResponse({
                'success': True,
                'message': f"{len(updated_sources)} sources {action_past} successfully",
                'updated_sources': updated_sources,
                'errors': errors,
                'action': action_past
            })
            
        except Exception as e:
            logger.error(f"Error in bulk activation for {source_type}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred during bulk operation'
            })

@login_required
def source_activation_confirmation(request, source_id, source_type, action):
    """Show confirmation page for source activation/deactivation"""
    try:
        model_map = {
            'camera': CameraSource,
            'file': FileSource,
            'stream': StreamSource,
        }
        
        model_class = model_map.get(source_type)
        if not model_class:
            messages.error(request, f"Invalid source type: {source_type}")
            return redirect('source_management:dashboard')
        
        source = get_object_or_404(model_class, source_id=source_id)
        
        if action not in ['activate', 'deactivate']:
            messages.error(request, "Invalid action")
            return redirect('source_management:dashboard')
        
        # Check if already in desired state
        if (action == 'activate' and source.is_active) or (action == 'deactivate' and not source.is_active):
            current_state = "active" if source.is_active else "inactive"
            messages.info(request, f"Source is already {current_state}")
            return redirect('source_management:dashboard')
        
        form = SourceActivationForm(initial={
            'source_id': source_id,
            'source_type': source_type,
            'action': action,
            'source_name': source.name
        })
        
        context = {
            'source': source,
            'source_type': source_type,
            'action': action,
            'form': form,
            'title': f"{action.title()} {source_type.title()} Source",
            'confirmation_message': f"Are you sure you want to {action} the {source_type} source '{source.name}'?"
        }
        
        return render(request, 'source_management/source_activation_confirm.html', context)
        
    except Exception as e:
        logger.error(f"Error in activation confirmation: {e}")
        messages.error(request, "An error occurred")
        return redirect('source_management:dashboard')

@login_required
@require_POST
def confirm_source_activation(request):
    """Handle confirmed source activation/deactivation"""
    try:
        form = SourceActivationForm(request.POST)
        
        if not form.is_valid():
            messages.error(request, "Invalid form data")
            return redirect('source_management:dashboard')
        
        source_id = form.cleaned_data['source_id']
        source_type = form.cleaned_data['source_type']
        action = form.cleaned_data['action']
        
        # Use the toggle view logic
        toggle_view = ToggleSourceActivationView()
        response = toggle_view.post(request, source_id, source_type)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return redirect('source_management:dashboard')
            else:
                messages.error(request, data.get('error', 'Operation failed'))
        else:
            messages.error(request, "Operation failed")
        
        return redirect('source_management:dashboard')
        
    except Exception as e:
        logger.error(f"Error in confirmed activation: {e}")
        messages.error(request, "An error occurred")
        return redirect('source_management:dashboard')

