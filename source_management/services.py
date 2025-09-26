import requests
import logging
import uuid
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class SourceManagementService:
    """Service class to handle communication with the Source Management Service"""

    def __init__(self):
        # Use the new Source Management Service
        self.base_url = getattr(settings, 'SOURCE_MANAGEMENT_SERVICE_URL', 'http://localhost:8001')
        self.timeout = getattr(settings, 'SOURCE_MANAGEMENT_TIMEOUT', 30)
        self.session = requests.Session()
        logger.info(f"Source Management Service initialized with base URL: {self.base_url}")

    def health(self):
        """Check the health of the source management service"""
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
                    'service': health_data.get('service')
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

    # Source Management Operations
    def create_source(self, source_data):
        """Create a new source"""
        try:
            url = f"{self.base_url}/api/v1/sources/"
            response = self.session.post(url, json=source_data, timeout=self.timeout)

            if response.status_code == 201:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}", 'details': response.text}

        except Exception as e:
            logger.error(f"Error creating source: {e}")
            return {'success': False, 'error': str(e)}

    def get_sources(self, filters=None):
        """Get all sources with optional filters"""
        try:
            url = f"{self.base_url}/api/v1/sources/"
            params = filters or {}
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            return {'success': False, 'error': str(e)}

    def get_source(self, source_id):
        """Get a specific source by ID"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/"
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def update_source(self, source_id, update_data):
        """Update a source"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/"
            response = self.session.put(url, json=update_data, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error updating source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def delete_source(self, source_id):
        """Delete a source"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/"
            response = self.session.delete(url, timeout=self.timeout)

            if response.status_code == 204:
                return {'success': True}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error deleting source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def activate_source(self, source_id):
        """Activate a source"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/activate/"
            response = self.session.post(url, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error activating source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def deactivate_source(self, source_id):
        """Deactivate a source"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/deactivate/"
            response = self.session.post(url, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error deactivating source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    # Video File Operations
    def initiate_upload(self, source_id, filename, filesize, content_type='video/mp4'):
        """Initiate a file upload"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/files/upload/initiate/"
            payload = {
                'filename': filename,
                'filesize': filesize,
                'content_type': content_type
            }
            response = self.session.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error initiating upload for source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def complete_upload(self, source_id, upload_id):
        """Complete a file upload"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/files/upload/complete/"
            payload = {'upload_id': upload_id}
            response = self.session.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error completing upload for source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def get_video_files(self, source_id):
        """Get video files for a source"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/files/"
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting video files for source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    # Processing Job Operations
    def create_processing_job(self, source_id, job_data):
        """Create a processing job"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/jobs/"
            response = self.session.post(url, json=job_data, timeout=self.timeout)

            if response.status_code == 202:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error creating processing job for source {source_id}: {e}")
            return {'success': False, 'error': str(e)}

    def get_processing_job_status(self, source_id, job_id):
        """Get processing job status"""
        try:
            url = f"{self.base_url}/api/v1/sources/{source_id}/jobs/{job_id}/status/"
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting processing job status for source {source_id}, job {job_id}: {e}")
            return {'success': False, 'error': str(e)}

    def processing_job_callback(self, job_id, status, results=None, error_message=None):
        """Send processing job callback"""
        try:
            url = f"{self.base_url}/api/v1/jobs/callback/"
            payload = {
                'job_id': job_id,
                'status': status,
                'results': results,
                'error_message': error_message
            }
            response = self.session.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                return {'success': True}
            else:
                return {'success': False, 'error': f"Service returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error sending processing callback for job {job_id}: {e}")
            return {'success': False, 'error': str(e)}

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
    """Service class to handle video processing operations via external services"""

    def __init__(self):
        # Use the new Source Management Service for processing jobs
        self.source_service = SourceManagementService()
        # Also keep reference to Data Ingestion Service for external processing
        self.data_ingestion_service = DataIngestionService()

    def health(self):
        """Check the health of both services"""
        source_health = self.source_service.health()
        data_ingestion_health = self.data_ingestion_service.health()

        return {
            'source_management_service': source_health,
            'data_ingestion_service': data_ingestion_health
        }

    def submit_video_processing(self, file_source, target_fps, target_resolution):
        """Submit a video for processing using the new architecture"""
        try:
            # First, create a processing job in the Source Management Service
            job_data = {
                'target_fps': target_fps or file_source.fps or 30,
                'target_resolution': target_resolution or '640x480'
            }

            # If we have a video file, add the video_file_id
            if hasattr(file_source, 'video_file_id'):
                job_data['video_file_id'] = file_source.video_file_id

            source_service_result = self.source_service.create_processing_job(
                str(file_source.source_id),
                job_data
            )

            if not source_service_result['success']:
                return source_service_result

            job_data = source_service_result['data']

            # Then, notify the external data ingestion service if configured
            try:
                data_ingestion_result = self.data_ingestion_service.notify_new_source(file_source)
                if data_ingestion_result['success']:
                    logger.info(f"Successfully notified data ingestion service about processing job {job_data.get('job_id')}")
                else:
                    logger.warning(f"Failed to notify data ingestion service: {data_ingestion_result.get('error')}")
            except Exception as e:
                logger.warning(f"Error notifying data ingestion service: {e}")

            return {
                'success': True,
                'job_id': job_data.get('job_id'),
                'message': 'Video processing job submitted successfully',
                'data_ingestion_notified': True
            }

        except Exception as e:
            logger.error(f"Error submitting video processing job: {e}")
            return {
                'success': False,
                'error': str(e),
                'details': 'Failed to submit video processing job'
            }

    def get_job_status(self, job_id, source_id=None):
        """Get the status of a processing job from the Source Management Service"""
        try:
            # If we have source_id, use it; otherwise, we'll need to find the job
            if source_id:
                result = self.source_service.get_processing_job_status(source_id, job_id)
                if result['success']:
                    return result
            else:
                # Try to find the job by searching through sources
                # This is a simplified approach - in practice, you might want to store the mapping
                return {
                    'success': False,
                    'error': 'Source ID required to get job status'
                }

        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_source_status(self, source_id):
        """Get the processing status of a source using the Source Management Service"""
        try:
            result = self.source_service.get_source(str(source_id))
            if result['success']:
                source_data = result['data']
                return {
                    'success': True,
                    'source_id': source_id,
                    'status': 'active' if source_data.get('is_active', True) else 'inactive',
                    'response': source_data
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Error getting source status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_job(self, job_id, source_id):
        """Cancel a processing job"""
        try:
            # Send callback to mark job as cancelled
            result = self.source_service.processing_job_callback(
                job_id,
                'cancelled',
                error_message='Job cancelled by user'
            )

            if result['success']:
                return {'success': True, 'message': 'Job cancelled successfully'}
            else:
                return result

        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def activate_source(self, source_id):
        """Activate a source"""
        return self.source_service.activate_source(source_id)

    def deactivate_source(self, source_id):
        """Deactivate a source"""
        return self.source_service.deactivate_source(source_id)
