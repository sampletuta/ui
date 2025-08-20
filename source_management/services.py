import requests
import logging
import uuid
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service class to handle communication with the Data Ingestion Service"""
    
    def __init__(self):
        self.config = settings.DATA_INGESTION_SERVICE
        self.base_url = self.config['BASE_URL']
        self.notify_endpoint = self.config['NOTIFY_ENDPOINT']
        self.health_endpoint = self.config['HEALTH_ENDPOINT']
        self.status_endpoint = self.config['STATUS_ENDPOINT']
        self.api_key = self.config.get('API_KEY', '')
        self.timeout = self.config['TIMEOUT']
        
        # Reuse HTTP connections for better performance
        self.session = requests.Session()
    
    def notify_new_source(self, file_source):
        """Notify the data ingestion service about a new video source"""
        try:
            payload = {
                "source_id": str(file_source.source_id),
                "file_url": file_source.api_endpoint,
                "fps": file_source.fps or 30,
                "width": file_source.width or 1920,
                "height": file_source.height or 1080,
            }
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            url = f"{self.base_url}{self.notify_endpoint}"
            response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code in (200, 201, 202):
                logger.info(f"Successfully notified data ingestion service about source {file_source.source_id}")
                return {'success': True, 'message': 'Data ingestion service notified successfully'}
            else:
                logger.warning(f"Failed to notify data ingestion service: {response.status_code}")
                return {'success': False, 'error': f"Service returned status {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error notifying data ingestion service: {e}")
            return {'success': False, 'error': str(e)}
    
    def health(self):
        """Check the health of the data ingestion service"""
        try:
            url = f"{self.base_url}{self.health_endpoint}"
            response = self.session.get(url, timeout=self.timeout)
            return {'url': url, 'ok': response.status_code == 200, 'status_code': response.status_code}
        except Exception as e:
            return {'url': f"{self.base_url}{self.health_endpoint}", 'ok': False, 'error': str(e)}
    
    def get_source_status(self, source_id):
        """Get the processing status of a source"""
        try:
            url = f"{self.base_url}{self.status_endpoint.format(source_id=source_id)}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return {'success': True, 'status': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}


class VideoProcessingService:
    """Service class to handle video processing operations via the Data Ingestion Service"""
    
    def __init__(self):
        # Default to localhost:8001 if not configured (matching the actual service)
        self.base_url = getattr(settings, 'DATA_INGESTION_SERVICE_URL', 'http://localhost:8001')
        self.timeout = getattr(settings, 'DATA_INGESTION_TIMEOUT', 30)
        self.session = requests.Session()
    
    def health(self):
        """Check the health of the data ingestion service"""
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                health_data = response.json()
                return {
                    'url': url,
                    'ok': health_data.get('status') == 'healthy',
                    'status_code': response.status_code,
                    'response': health_data,
                    'status': health_data.get('status'),
                    'version': health_data.get('version'),
                    'timestamp': health_data.get('timestamp')
                }
            else:
                return {
                    'url': url,
                    'ok': False,
                    'status_code': response.status_code,
                    'error': f"Service returned status {response.status_code}"
                }
        except Exception as e:
            return {
                'url': f"{self.base_url}/health",
                'ok': False,
                'error': str(e),
                'status_code': None
            }
    
    def submit_video_processing(self, file_source, target_fps, target_resolution):
        """Submit a video for processing to the data ingestion service"""
        try:
            # Prepare payload according to the actual API schema (SourceRequest)
            # Use the public stream URL so the data ingestion service can access the video without authentication
            public_stream_url = f"http://localhost:8000/source-management/api/public/video/{file_source.access_token}/stream/"
            
            payload = {
                "source_id": str(file_source.source_id),
                "file_url": public_stream_url,
                "fps": target_fps or file_source.fps or 30,
                "width": file_source.width or 1920,
                "height": file_source.height or 1080,
            }
            
            # Submit to data ingestion service for processing using the correct endpoint
            url = f"{self.base_url}/api/sources"
            response = self.session.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code in (200, 201, 202):
                response_data = response.json()
                return {
                    'success': True,
                    'job_id': response_data.get('ingestion_id'),
                    'external_job_id': response_data.get('ingestion_id'),
                    'message': response_data.get('message', 'Video processing job submitted successfully'),
                    'external_service_url': self.base_url,
                    'estimated_completion_time': 'Calculating...'  # Not provided by the API
                }
            else:
                return {
                    'success': False,
                    'error': f"Data ingestion service returned status {response.status_code}",
                    'details': response.text if response.text else 'No response details'
                }
                
        except Exception as e:
            logger.error(f"Error submitting video processing job: {e}")
            return {
                'success': False,
                'error': str(e),
                'details': 'Failed to communicate with data ingestion service'
            }
    
    def get_job_status(self, job_id):
        """Get the status of a processing job from the data ingestion service"""
        try:
            # Use the correct endpoint for getting job details
            url = f"{self.base_url}/api/jobs/{job_id}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'job_id': job_id,
                    'external_job_id': data.get('ingestion_id', job_id),
                    'status': data.get('status', 'unknown'),
                    'external_status': data.get('status', 'unknown'),
                    'response': data
                }
            else:
                return {
                    'success': False,
                    'error': f"Job not found or service error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_source_status(self, source_id):
        """Get the processing status of a source using the correct endpoint"""
        try:
            url = f"{self.base_url}/api/sources/{source_id}/status"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'source_id': source_id,
                    'status': data.get('status', 'unknown'),
                    'progress': data.get('progress', 0),
                    'frames_processed': data.get('frames_processed', 0),
                    'total_frames': data.get('total_frames', 0),
                    'error_message': data.get('error_message'),
                    'response': data
                }
            else:
                return {
                    'success': False,
                    'error': f"Source not found or service error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error getting source status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_job(self, job_id):
        """Cancel a processing job - Note: This endpoint doesn't exist in the current API"""
        try:
            # The current API doesn't support job cancellation
            # Return an appropriate message
            return {
                'success': False,
                'error': 'Job cancellation is not supported by the current data ingestion service API',
                'details': 'The /api/jobs/{ingestion_id} endpoint only supports GET operations'
            }
                
        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return {
                'success': False,
                'error': str(e)
            }
