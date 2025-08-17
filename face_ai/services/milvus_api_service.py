import logging
import requests
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from django.conf import settings
import time

logger = logging.getLogger(__name__)

class MilvusAPIService:
    """API-based service for managing face embeddings in Milvus vector database"""
    
    def __init__(self, api_base_url=None, api_key=None, timeout=30):
        # Get configuration from Django settings
        milvus_config = getattr(settings, 'MILVUS_API_CONFIG', {})
        
        self.api_base_url = api_base_url or milvus_config.get('API_BASE_URL', 'http://localhost:8001')
        self.api_key = api_key or milvus_config.get('API_KEY', '')
        self.timeout = timeout or milvus_config.get('TIMEOUT', 30)
        self.collection_name = milvus_config.get('COLLECTION_NAME', 'watchlist')
        
        # API endpoints
        self.endpoints = {
            'search': f'{self.api_base_url}/api/milvus/search',
            'add': f'{self.api_base_url}/api/milvus/add',
            'delete': f'{self.api_base_url}/api/milvus/delete',
            'update': f'{self.api_base_url}/api/milvus/update',
            'status': f'{self.api_base_url}/api/milvus/status',
            'stats': f'{self.api_base_url}/api/milvus/stats',
            'query': f'{self.api_base_url}/api/milvus/query',
            'health': f'{self.api_base_url}/api/milvus/health'
        }
        
        # Headers for authentication
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else '',
            'User-Agent': 'MilvusAPIService/1.0'
        }
        
        logger.info(f"Initialized Milvus API Service with base URL: {self.api_base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make HTTP request to Milvus API"""
        try:
            url = endpoint
            kwargs = {
                'headers': self.headers,
                'timeout': self.timeout
            }
            
            if method.upper() == 'GET':
                if params:
                    kwargs['params'] = params
                response = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                if data:
                    kwargs['json'] = data
                response = requests.post(url, **kwargs)
            elif method.upper() == 'DELETE':
                if data:
                    kwargs['json'] = data
                response = requests.delete(url, **kwargs)
            elif method.upper() == 'PUT':
                if data:
                    kwargs['json'] = data
                response = requests.put(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check response status
            response.raise_for_status()
            
            # Parse JSON response
            try:
                result = response.json()
                logger.debug(f"API Response: {result}")
                return result
            except json.JSONDecodeError:
                logger.warning(f"Non-JSON response from API: {response.text}")
                return {'success': True, 'data': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_health(self) -> Dict:
        """Check if the Milvus API is healthy"""
        try:
            result = self._make_request('GET', self.endpoints['health'])
            return result
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_collection_status(self) -> Dict:
        """Check collection status via API"""
        try:
            data = {
                'collection_name': self.collection_name
            }
            result = self._make_request('POST', self.endpoints['status'], data)
            return result
        except Exception as e:
            logger.error(f"Failed to get collection status: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics via API"""
        try:
            data = {
                'collection_name': self.collection_name
            }
            result = self._make_request('POST', self.endpoints['stats'], data)
            return result
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {'success': False, 'error': str(e)}
    
    def search_similar_faces(self, query_embedding: np.ndarray, top_k: int = 10, 
                           threshold: float = 0.6) -> List[Dict]:
        """Search for similar faces via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'query_embedding': query_embedding.tolist(),
                'top_k': top_k,
                'threshold': threshold,
                'output_fields': ['target_id', 'photo_id', 'confidence_score', 'created_at']
            }
            
            result = self._make_request('POST', self.endpoints['search'], data)
            
            if result.get('success') and 'data' in result:
                return result['data']
            else:
                logger.error(f"Search API returned error: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to search similar faces: {e}")
            return []
    
    def search_similar_targets(self, query_embedding: np.ndarray, top_k: int = 10, 
                              threshold: float = 0.6) -> List[Dict]:
        """Search for similar targets using normalized embeddings via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'query_embedding': query_embedding.tolist(),
                'top_k': top_k,
                'threshold': threshold,
                'output_fields': ['target_id', 'confidence_score', 'created_at'],
                'search_type': 'targets'  # Indicate we want target-based search
            }
            
            result = self._make_request('POST', self.endpoints['search'], data)
            
            if result.get('success') and 'data' in result:
                return result['data']
            else:
                logger.error(f"Target search API returned error: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to search similar targets: {e}")
            return []
    
    def insert_face_embeddings(self, embeddings_data: List[Dict]) -> List[int]:
        """Insert face embeddings via API (legacy method - now creates normalized embeddings)"""
        try:
            # Group embeddings by target_id
            target_embeddings = {}
            target_confidence_scores = {}
            
            for data in embeddings_data:
                target_id = str(data['target_id'])
                if target_id not in target_embeddings:
                    target_embeddings[target_id] = []
                    target_confidence_scores[target_id] = []
                
                target_embeddings[target_id].append(data['embedding'])
                target_confidence_scores[target_id].append(data['confidence_score'])
            
            # Create normalized embeddings for each target
            primary_keys = []
            for target_id, embeddings in target_embeddings.items():
                confidence_scores = target_confidence_scores[target_id]
                
                # Use the normalized embedding method instead
                milvus_id = self.insert_normalized_target_embedding(
                    target_id=target_id,
                    embeddings=embeddings,
                    confidence_scores=confidence_scores
                )
                
                if milvus_id:
                    primary_keys.append(milvus_id)
                    logger.info(f"Created normalized embedding for target {target_id} via API")
                else:
                    logger.warning(f"Failed to create normalized embedding for target {target_id}")
            
            return primary_keys
                
        except Exception as e:
            logger.error(f"Failed to insert embeddings: {e}")
            return []
    
    def insert_normalized_target_embedding(self, target_id: str, embeddings: List[np.ndarray], 
                                         confidence_scores: List[float] = None) -> Optional[int]:
        """Insert a single embedding for a target via API"""
        try:
            if not embeddings:
                logger.warning(f"No embeddings provided for target {target_id}")
                return None
            
            # Smart embedding strategy:
            # - If 1 image: use the single embedding directly
            # - If 2+ images: average and normalize
            if len(embeddings) == 1:
                # Single image: use embedding as-is (no averaging needed)
                final_embedding = embeddings[0]
                avg_confidence = confidence_scores[0] if confidence_scores else 0.5
                logger.info(f"Target {target_id} has 1 image - using single embedding directly")
            else:
                # Multiple images: average and normalize for better representation
                avg_embedding = np.mean(embeddings, axis=0)
                final_embedding = avg_embedding / np.linalg.norm(avg_embedding)
                avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.5
                logger.info(f"Target {target_id} has {len(embeddings)} images - using averaged normalized embedding")
            
            data = {
                'collection_name': self.collection_name,
                'embedding_type': 'normalized_target',
                'target_id': target_id,
                'photo_id': f"norm_{target_id[:8]}",  # Short identifier for normalized embeddings
                'embedding': final_embedding.tolist(),
                'confidence_score': avg_confidence,
                'metadata': {
                    'num_images': len(embeddings),
                    'embedding_strategy': 'single' if len(embeddings) == 1 else 'averaged_normalized',
                    'avg_confidence': avg_confidence,
                    'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            result = self._make_request('POST', self.endpoints['add'], data)
            
            if result.get('success') and 'data' in result:
                milvus_id = result['data'].get('primary_keys', [None])[0]
                logger.info(f"Inserted normalized embedding for target {target_id} via API (Milvus ID: {milvus_id})")
                return milvus_id
            else:
                logger.error(f"Insert normalized embedding API returned error: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to insert normalized target embedding: {e}")
            return None
    
    def get_target_normalized_embedding(self, target_id: str) -> Optional[np.ndarray]:
        """Get the normalized embedding for a specific target via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'query_type': 'target_embedding',
                'target_id': target_id
            }
            
            result = self._make_request('POST', self.endpoints['query'], data)
            
            if result.get('success') and 'data' in result and result['data']:
                embedding_data = result['data'][0]
                embedding = np.array(embedding_data['embedding'])
                logger.info(f"Found normalized embedding for target {target_id} via API")
                return embedding
            else:
                logger.warning(f"No normalized embedding found for target {target_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get normalized embedding for target {target_id}: {e}")
            return None
    
    def get_photo_milvus_id(self, photo_id: str) -> Optional[int]:
        """Get the Milvus vector ID for a specific photo via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'query_type': 'photo_id',
                'photo_id': photo_id
            }
            
            result = self._make_request('POST', self.endpoints['query'], data)
            
            if result.get('success') and 'data' in result and result['data']:
                vector_id = result['data'][0]['id']
                logger.info(f"Found Milvus ID {vector_id} for photo {photo_id} via API")
                return vector_id
            else:
                logger.warning(f"No Milvus embedding found for photo {photo_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get Milvus ID for photo {photo_id}: {e}")
            return None
    
    def search_similar_faces_by_milvus_id(self, milvus_id: int, top_k: int = 10, 
                                        threshold: float = 0.6) -> List[Dict]:
        """Search for similar faces using a Milvus vector ID as query via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'search_type': 'by_milvus_id',
                'milvus_id': milvus_id,
                'top_k': top_k,
                'threshold': threshold
            }
            
            result = self._make_request('POST', self.endpoints['search'], data)
            
            if result.get('success') and 'data' in result:
                return result['data']
            else:
                logger.error(f"Search by Milvus ID API returned error: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to search by Milvus ID {milvus_id}: {e}")
            return []
    
    def delete_face_embedding(self, vector_id: int) -> bool:
        """Delete a specific face embedding by vector ID via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'delete_type': 'by_vector_id',
                'vector_id': vector_id
            }
            
            result = self._make_request('DELETE', self.endpoints['delete'], data)
            
            if result.get('success'):
                logger.info(f"Deleted embedding with vector ID {vector_id} via API")
                return True
            else:
                logger.error(f"Delete API returned error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete embedding {vector_id}: {e}")
            return False
    
    def delete_embeddings_by_photo_id(self, photo_id: str) -> int:
        """Delete all embeddings for a specific photo via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'delete_type': 'by_photo_id',
                'photo_id': photo_id
            }
            
            result = self._make_request('DELETE', self.endpoints['delete'], data)
            
            if result.get('success') and 'data' in result:
                deleted_count = result['data'].get('deleted_count', 0)
                logger.info(f"Deleted {deleted_count} embeddings for photo {photo_id} via API")
                return deleted_count
            else:
                logger.error(f"Delete by photo ID API returned error: {result.get('error', 'Unknown error')}")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to delete embeddings for photo {photo_id}: {e}")
            return 0
    
    def delete_embeddings_by_target_id(self, target_id: str) -> int:
        """Delete all embeddings for a specific target via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'delete_type': 'by_target_id',
                'target_id': target_id
            }
            
            result = self._make_request('DELETE', self.endpoints['delete'], data)
            
            if result.get('success') and 'data' in result:
                deleted_count = result['data'].get('deleted_count', 0)
                logger.info(f"Deleted {deleted_count} embeddings for target {target_id} via API")
                return deleted_count
            else:
                logger.error(f"Delete by target ID API returned error: {result.get('error', 'Unknown error')}")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to delete embeddings for target {target_id}: {e}")
            return 0
    
    def update_embedding(self, vector_id: int, updates: Dict) -> bool:
        """Update an existing embedding via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'vector_id': vector_id,
                'updates': updates
            }
            
            result = self._make_request('PUT', self.endpoints['update'], data)
            
            if result.get('success'):
                logger.info(f"Updated embedding {vector_id} via API")
                return True
            else:
                logger.error(f"Update API returned error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update embedding {vector_id}: {e}")
            return False
    
    def get_embeddings_by_target(self, target_id: str) -> List[Dict]:
        """Get all embeddings for a specific target via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'query_type': 'by_target_id',
                'target_id': target_id
            }
            
            result = self._make_request('POST', self.endpoints['query'], data)
            
            if result.get('success') and 'data' in result:
                return result['data']
            else:
                logger.error(f"Query by target ID API returned error: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get embeddings for target {target_id}: {e}")
            return []
    
    def get_embeddings_by_photo(self, photo_id: str) -> List[Dict]:
        """Get all embeddings for a specific photo via API"""
        try:
            data = {
                'collection_name': self.collection_name,
                'query_type': 'by_photo_id',
                'photo_id': photo_id
            }
            
            result = self._make_request('POST', self.endpoints['query'], data)
            
            if result.get('success') and 'data' in result:
                return result['data']
            else:
                logger.error(f"Query by photo ID API returned error: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get embeddings for photo {photo_id}: {e}")
            return []
    
    def batch_operations(self, operations: List[Dict]) -> Dict:
        """Perform multiple operations in a single API call"""
        try:
            data = {
                'collection_name': self.collection_name,
                'operations': operations
            }
            
            result = self._make_request('POST', f'{self.api_base_url}/api/milvus/batch', data)
            
            if result.get('success'):
                logger.info(f"Completed {len(operations)} batch operations via API")
                return result
            else:
                logger.error(f"Batch operations API returned error: {result.get('error', 'Unknown error')}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to perform batch operations: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_collection(self, collection_config: Dict) -> bool:
        """Create a new collection via API"""
        try:
            data = {
                'collection_name': collection_config.get('name', self.collection_name),
                'dimension': collection_config.get('dimension', 512),
                'metric_type': collection_config.get('metric_type', 'COSINE'),
                'index_type': collection_config.get('index_type', 'IVF_FLAT'),
                'index_params': collection_config.get('index_params', {'nlist': 1024})
            }
            
            result = self._make_request('POST', f'{self.api_base_url}/api/milvus/collection/create', data)
            
            if result.get('success'):
                logger.info(f"Created collection {data['collection_name']} via API")
                return True
            else:
                logger.error(f"Create collection API returned error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False
    
    def drop_collection(self, collection_name: str = None) -> bool:
        """Drop a collection via API"""
        try:
            data = {
                'collection_name': collection_name or self.collection_name
            }
            
            result = self._make_request('DELETE', f'{self.api_base_url}/api/milvus/collection/drop', data)
            
            if result.get('success'):
                logger.info(f"Dropped collection {data['collection_name']} via API")
                return True
            else:
                logger.error(f"Drop collection API returned error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            return False
    
    def close_connection(self):
        """Close API service (no actual connection to close)"""
        logger.info("Milvus API Service closed (no connection to close)")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_connection()
