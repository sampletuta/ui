import requests
import json
import uuid
from django.conf import settings
from django.utils import timezone
from .models import VideoProcessingJob
import logging

logger = logging.getLogger(__name__)

class VideoProcessingService:
    """Service class to handle communication with external video processing service"""
    
    def __init__(self):
        self.config = settings.VIDEO_PROCESSING_SERVICE
        self.base_url = self.config['BASE_URL']
        self.submit_endpoint = self.config['SUBMIT_JOB_ENDPOINT']
        self.status_endpoint = self.config['STATUS_ENDPOINT']
        self.api_key = self.config.get('API_KEY', '')
        self.timeout = self.config['TIMEOUT']
        self.health_endpoint = self.config.get('HEALTH_ENDPOINT', '/api/v1/health')
    
    def submit_video_processing(self, file_source, target_fps=None, target_resolution=None):
        """
        Submit a video for processing to the FastPublisher service
        
        Args:
            file_source: FileSource instance
            target_fps: Target frame rate
            target_resolution: Target resolution (e.g., "640x480")
        
        Returns:
            dict: Response from external service
        """
        try:
            # Generate unique job ID
            job_id = f"job-{uuid.uuid4().hex[:8]}"
            
            # Generate access token for this job
            access_token = uuid.uuid4().hex
            
            # Build callback URL for FastPublisher to send results
            callback_url = f"{settings.BASE_URL}/source-management/api/processing-callback/{access_token}/"

            # Create processing job record
            processing_job = VideoProcessingJob.objects.create(
                job_id=job_id,
                source=file_source,
                target_fps=target_fps,
                target_resolution=target_resolution,
                external_service_url=self.base_url,
                callback_url=callback_url,
                access_token=access_token,
                status='pending'
            )
            
            # Prepare payload according to FastPublisher API specification
            processing_params = {}
            if target_fps is not None:
                processing_params["target_fps"] = target_fps
            if target_resolution is not None:
                processing_params["target_resolution"] = target_resolution

            payload = {
                "source_metadata": {
                    "source_id": str(file_source.source_id),
                    "stream_url": f"{settings.BASE_URL}/source-management/api/fastpublisher-video/{file_source.source_id}/",
                    "width": file_source.width or 1920,
                    "height": file_source.height or 1080,
                    "api_endpoint": callback_url,
                    "access_token": access_token
                },
            }
            if processing_params:
                payload["processing_params"] = processing_params
            
            # No-auth service; keep headers minimal
            headers = {
                'Content-Type': 'application/json',
                'X-Job-ID': job_id
            }
            
            # Submit to FastPublisher service
            url = f"{self.base_url}{self.submit_endpoint}"
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code in (200, 202):
                # Success - update job with external response
                response_data = response.json()
                processing_job.external_job_id = response_data.get('job_id', job_id)
                processing_job.external_response = response_data
                processing_job.status = 'processing'
                processing_job.started_at = timezone.now()
                processing_job.save()
                
                logger.info(f"Successfully submitted video processing job {job_id} for source {file_source.source_id}")
                
                return {
                    'success': True,
                    'job_id': job_id,
                    'external_job_id': processing_job.external_job_id,
                    'message': 'Video processing job submitted successfully',
                    'response': response_data,
                    'external_service_url': url
                }
            else:
                # Failed - update job status
                processing_job.status = 'failed'
                processing_job.error_message = f"External service returned status {response.status_code}: {response.text}"
                processing_job.save()
                
                logger.error(f"Failed to submit video processing job {job_id}: {response.status_code} - {response.text}")
                
                return {
                    'success': False,
                    'job_id': job_id,
                    'error': f"External service error: {response.status_code}",
                    'details': response.text,
                    'external_service_url': url
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Request to external service timed out"
            logger.error(f"Timeout submitting video processing job: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'external_service_url': f"{self.base_url}{self.submit_endpoint}"
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Request to external service failed: {str(e)}"
            logger.error(f"Request error submitting video processing job: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'external_service_url': f"{self.base_url}{self.submit_endpoint}"
            }
        except Exception as e:
            error_msg = f"Unexpected error submitting video processing job: {str(e)}"
            logger.error(f"Unexpected error: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'external_service_url': f"{self.base_url}{self.submit_endpoint}"
            }
    
    def get_job_status(self, job_id):
        """
        Get the status of a processing job from external service
        
        Args:
            job_id: Internal job ID
        
        Returns:
            dict: Job status information
        """
        try:
            # Get the processing job
            processing_job = VideoProcessingJob.objects.get(job_id=job_id)
            
            if not processing_job.external_job_id:
                return {
                    'success': False,
                    'error': 'No external job ID available'
                }
            
            # Prepare headers
            headers = {
                'X-Job-ID': processing_job.external_job_id
            }
            
            # Get status from FastPublisher service using source_id
            url = f"{self.base_url}{self.status_endpoint.format(source_id=processing_job.source.source_id)}"
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Update local job status if it has changed
                external_status = status_data.get('status', 'unknown')
                if external_status != processing_job.status:
                    processing_job.update_status(external_status, external_response=status_data)
                
                return {
                    'success': True,
                    'job_id': job_id,
                    'external_job_id': processing_job.external_job_id,
                    'status': processing_job.status,
                    'external_status': external_status,
                    'response': status_data
                }
            else:
                return {
                    'success': False,
                    'error': f"External service returned status {response.status_code}",
                    'details': response.text,
                    'external_service_url': url
                }
                
        except VideoProcessingJob.DoesNotExist:
            return {
                'success': False,
                'error': 'Processing job not found'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Request to external service failed: {str(e)}",
                'external_service_url': f"{self.base_url}{self.status_endpoint}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'external_service_url': f"{self.base_url}{self.status_endpoint}"
            }

    def health(self):
        """Check FastPublisher health."""
        url = f"{self.base_url}{self.health_endpoint}"
        try:
            response = requests.get(url, timeout=self.timeout)
            return {
                'url': url,
                'ok': response.status_code == 200,
                'status_code': response.status_code,
                'response': response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            }
        except requests.exceptions.RequestException as e:
            return {
                'url': url,
                'ok': False,
                'error': str(e)
            }
    
    def cancel_job(self, job_id):
        """
        Cancel a processing job
        
        Args:
            job_id: Internal job ID
        
        Returns:
            dict: Cancellation result
        """
        try:
            processing_job = VideoProcessingJob.objects.get(job_id=job_id)
            
            if processing_job.status in ['completed', 'failed', 'cancelled']:
                return {
                    'success': False,
                    'error': f'Cannot cancel job in {processing_job.status} status'
                }
            
            # Update local status
            processing_job.update_status('cancelled')
            
            logger.info(f"Cancelled video processing job {job_id}")
            
            return {
                'success': True,
                'job_id': job_id,
                'message': 'Job cancelled successfully'
            }
            
        except VideoProcessingJob.DoesNotExist:
            return {
                'success': False,
                'error': 'Processing job not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
