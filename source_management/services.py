import requests
import logging
from django.conf import settings

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
