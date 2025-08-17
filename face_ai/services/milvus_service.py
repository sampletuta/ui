import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from pymilvus import connections, Collection, utility
from django.conf import settings

logger = logging.getLogger(__name__)

class MilvusService:
    """Service for managing face embeddings in Milvus vector database"""
    
    def __init__(self, host=None, port=None):
        # Get configuration from Django settings
        milvus_config = getattr(settings, 'MILVUS_CONFIG', {})
        
        self.host = host or milvus_config.get('HOST', 'localhost')
        self.port = port or milvus_config.get('PORT', 19530)
        self.connection_alias = milvus_config.get('CONNECTION_ALIAS', 'default')
        self.collection_name = milvus_config.get('COLLECTION_NAME', 'watchlist')
        self.dimension = milvus_config.get('DIMENSION', 512)
        self.metric_type = milvus_config.get('METRIC_TYPE', 'COSINE')
        self.index_type = milvus_config.get('INDEX_TYPE', 'IVF_FLAT')
        self.index_params = milvus_config.get('INDEX_PARAMS', {'nlist': 1024})
        self.search_params = milvus_config.get('SEARCH_PARAMS', {'nprobe': 10})
        self.auto_create_collection = milvus_config.get('AUTO_CREATE_COLLECTION', True)
        self.auto_load_collection = milvus_config.get('AUTO_LOAD_COLLECTION', True)
        
        self._ensure_connection()
        
        # Auto-create collection if enabled
        if self.auto_create_collection:
            self.create_collection_if_not_exists()
    
    def _ensure_connection(self):
        """Ensure connection to Milvus"""
        try:
            # Check if connection already exists
            if not connections.has_connection(self.connection_alias):
                connections.connect(
                    alias=self.connection_alias,
                    host=self.host,
                    port=self.port
                )
                logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            else:
                logger.info("Milvus connection already established")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def create_collection_if_not_exists(self):
        """Create Milvus collection if it doesn't exist"""
        try:
            if utility.has_collection(self.collection_name):
                logger.info(f"Collection {self.collection_name} already exists")
                self.collection = Collection(self.collection_name)
                return
            
            from pymilvus import FieldSchema, CollectionSchema, DataType
            
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="target_id", dtype=DataType.VARCHAR, max_length=36),
                FieldSchema(name="photo_id", dtype=DataType.VARCHAR, max_length=36),  # Added photo_id
                FieldSchema(name="confidence_score", dtype=DataType.FLOAT),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50)
            ]
            
            schema = CollectionSchema(fields, description="Face embeddings for targets")
            
            # Create collection
            self.collection = Collection(self.collection_name, schema)
            
            # Create index for vector field using settings
            index_params = {
                "metric_type": self.metric_type,
                "index_type": self.index_type,
                "params": self.index_params
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)
            
            logger.info(f"Created collection {self.collection_name} with {self.metric_type} index")
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            # If collection creation fails, try to get existing collection
            try:
                if utility.has_collection(self.collection_name):
                    logger.info(f"Using existing collection {self.collection_name}")
                    self.collection = Collection(self.collection_name)
                else:
                    raise e
            except Exception:
                raise e
    
    def insert_face_embeddings(self, embeddings_data: List[Dict]) -> List[int]:
        """Insert face embeddings into Milvus collection"""
        try:
            # Prepare data for insertion
            embeddings = []
            target_ids = []
            photo_ids = []  # Added photo_ids
            confidence_scores = []
            created_ats = []
            
            for data in embeddings_data:
                embeddings.append(data['embedding'])
                target_ids.append(str(data['target_id']))
                photo_ids.append(str(data['photo_id']))  # Store photo_id
                confidence_scores.append(data['confidence_score'])
                created_ats.append(data.get('created_at', ''))
            
            # Insert data
            insert_result = self.collection.insert([
                embeddings,
                target_ids,
                photo_ids,  # Include photo_ids
                confidence_scores,
                created_ats
            ])
            
            logger.info(f"Inserted {len(embeddings_data)} embeddings into Milvus")
            return insert_result.primary_keys
            
        except Exception as e:
            logger.error(f"Failed to insert embeddings: {e}")
            return []
    
    def insert_normalized_target_embedding(self, target_id: str, embeddings: List[np.ndarray], 
                                         confidence_scores: List[float] = None) -> Optional[int]:
        """Insert a single embedding for a target based on their images"""
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
            
            # Remove any existing embeddings for this target
            self.delete_embeddings_by_target_id(target_id)
            
            # Insert the embedding
            # Use a short identifier for normalized embeddings to avoid length issues
            normalized_photo_id = f"norm_{target_id[:8]}"  # Use first 8 chars of target_id
            insert_result = self.collection.insert([
                [final_embedding.tolist()],
                [target_id],
                [normalized_photo_id],  # Short identifier for normalized embeddings
                [avg_confidence],
                ['']
            ])
            
            logger.info(f"Inserted embedding for target {target_id} based on {len(embeddings)} images")
            return insert_result.primary_keys[0] if insert_result.primary_keys else None
            
        except Exception as e:
            logger.error(f"Failed to insert normalized target embedding: {e}")
            return None
    
    def get_target_normalized_embedding(self, target_id: str) -> Optional[np.ndarray]:
        """Get the normalized embedding for a specific target"""
        try:
            # Try to load collection if needed
            try:
                if self.auto_load_collection:
                    self.collection.load()
            except Exception as load_error:
                logger.warning(f"Failed to load collection, trying without loading: {load_error}")
            
            # Search for the target's normalized embedding
            expr = f'target_id == "{target_id}"'
            results = self.collection.query(
                expr=expr,
                output_fields=["id", "embedding", "target_id", "confidence_score"]
            )
            
            if results and len(results) > 0:
                # Return the first result's embedding
                embedding = np.array(results[0]['embedding'])
                logger.info(f"Found normalized embedding for target {target_id}")
                return embedding
            else:
                logger.warning(f"No normalized embedding found for target {target_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get normalized embedding for target {target_id}: {e}")
            return None
    
    def search_similar_faces(self, query_embedding: np.ndarray, top_k: int = 10, 
                           threshold: float = 0.6) -> List[Dict]:
        """Search for similar faces in Milvus"""
        try:
            # Load collection if auto-load is enabled
            if self.auto_load_collection:
                self.collection.load()
            
            # Prepare search parameters from settings
            search_params = {
                "metric_type": self.metric_type,
                "params": self.search_params
            }
            
            # Perform search
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["target_id", "photo_id", "confidence_score", "created_at"]
            )
            
            # Process results
            similar_faces = []
            for hits in results:
                for hit in hits:
                    if hit.score >= threshold:
                        similar_faces.append({
                            'id': hit.id,  # Add vector ID
                            'target_id': hit.entity.get('target_id'),
                            'photo_id': hit.entity.get('photo_id'),  # Include photo_id
                            'similarity': hit.score,  # Rename for consistency
                            'confidence': hit.entity.get('confidence_score', 0.0),
                            'created_at': hit.entity.get('created_at')
                        })
            
            return similar_faces
            
        except Exception as e:
            logger.error(f"Failed to search similar faces: {e}")
            return []
    
    def get_photo_milvus_id(self, photo_id: str) -> Optional[int]:
        """Get the Milvus vector ID for a specific photo"""
        try:
            # Try to load collection if needed
            try:
                if self.auto_load_collection:
                    self.collection.load()
            except Exception as load_error:
                logger.warning(f"Failed to load collection, trying without loading: {load_error}")
                # Continue without loading if there are issues
            
            logger.info(f"Searching for photo_id: {photo_id} in Milvus collection")
            
            # Search for the photo in the collection
            expr = f'photo_id == "{photo_id}"'
            logger.info(f"Milvus query expression: {expr}")
            
            results = self.collection.query(
                expr=expr,
                output_fields=["id", "embedding", "target_id", "photo_id", "confidence_score"]
            )
            
            logger.info(f"Milvus query returned {len(results) if results else 0} results")
            
            if results and len(results) > 0:
                # Return the first result's vector ID
                vector_id = results[0]['id']
                logger.info(f"Found Milvus ID {vector_id} for photo {photo_id}")
                return vector_id
            else:
                logger.warning(f"No Milvus embedding found for photo {photo_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get Milvus ID for photo {photo_id}: {e}")
            return None
    
    def search_similar_faces_by_milvus_id(self, milvus_id: int, top_k: int = 10, 
                                        threshold: float = 0.6) -> List[Dict]:
        """Search for similar faces using a Milvus vector ID as query"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            
            logger.info(f"Searching for similar faces using Milvus ID: {milvus_id}")
            
            # First, get the embedding for the given Milvus ID
            expr = f"id == {milvus_id}"
            logger.info(f"Milvus query expression: {expr}")
            
            query_results = self.collection.query(
                expr=expr,
                output_fields=["embedding"]
            )
            
            logger.info(f"Milvus query returned {len(query_results) if query_results else 0} results")
            
            if not query_results or len(query_results) == 0:
                logger.warning(f"No embedding found for Milvus ID {milvus_id}")
                return []
            
            # Get the embedding vector
            query_embedding = np.array(query_results[0]['embedding'])
            logger.info(f"Retrieved embedding vector with shape: {query_embedding.shape}")
            
            # Now search for similar faces using this embedding
            search_results = self.search_similar_faces(query_embedding, top_k, threshold)
            logger.info(f"Similarity search returned {len(search_results)} results")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search by Milvus ID {milvus_id}: {e}")
            return []
    
    def search_similar_targets(self, query_embedding: np.ndarray, top_k: int = 10, 
                              threshold: float = 0.6) -> List[Dict]:
        """Search for similar targets using normalized embeddings"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            
            logger.info(f"Searching for similar targets using normalized embeddings")
            
            # Prepare search parameters from settings
            search_params = {
                "metric_type": self.metric_type,
                "params": self.search_params
            }
            
            # Perform search
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["target_id", "confidence_score", "created_at"]
            )
            
            # Process results
            similar_targets = []
            for hits in results:
                for hit in hits:
                    if hit.score >= threshold:
                        similar_targets.append({
                            'id': hit.id,
                            'target_id': hit.entity.get('target_id'),
                            'similarity': hit.score,
                            'confidence': hit.entity.get('confidence_score', 0.0),
                            'created_at': hit.entity.get('created_at')
                        })
            
            logger.info(f"Found {len(similar_targets)} similar targets above threshold {threshold}")
            return similar_targets
            
        except Exception as e:
            logger.error(f"Failed to search similar targets: {e}")
            return []
    
    def delete_face_embedding(self, vector_id: int) -> bool:
        """Delete a specific face embedding by vector ID"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            expr = f"id == {vector_id}"
            self.collection.delete(expr)
            logger.info(f"Deleted embedding with vector ID {vector_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete embedding {vector_id}: {e}")
            return False
    
    def delete_embeddings_by_photo_id(self, photo_id: str) -> int:
        """Delete all embeddings for a specific photo"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            expr = f'photo_id == "{photo_id}"'
            delete_result = self.collection.delete(expr)
            deleted_count = len(delete_result.primary_keys) if delete_result.primary_keys else 0
            logger.info(f"Deleted {deleted_count} embeddings for photo {photo_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete embeddings for photo {photo_id}: {e}")
            return 0
    
    def delete_embeddings_by_target_id(self, target_id: str) -> int:
        """Delete all embeddings for a specific target"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            expr = f'target_id == "{target_id}"'
            delete_result = self.collection.delete(expr)
            deleted_count = len(delete_result.primary_keys) if delete_result.primary_keys else 0
            logger.info(f"Deleted {deleted_count} embeddings for target {target_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete embeddings for target {target_id}: {e}")
            return 0
    
    def check_collection_status(self) -> Dict:
        """Check if collection is properly loaded and accessible"""
        try:
            if not utility.has_collection(self.collection_name):
                return {
                    'status': 'error',
                    'message': f'Collection {self.collection_name} does not exist',
                    'collection_name': self.collection_name
                }
            
            # Try to get collection
            self.collection = Collection(self.collection_name)
            
            # Try to load collection with error handling
            try:
                # First check if collection is already loaded
                try:
                    # Try to get stats without loading
                    stats = self.collection.get_statistics()
                    logger.info(f"Collection {self.collection_name} already loaded, stats: {stats}")
                    return {
                        'status': 'success',
                        'message': f'Collection {self.collection_name} is already accessible',
                        'collection_name': self.collection_name,
                        'stats': stats
                    }
                except Exception:
                    # Collection not loaded, try to load it
                    pass
                
                # Try to load collection
                self.collection.load()
                logger.info(f"Collection {self.collection_name} loaded successfully")
                
                # Get basic stats
                stats = self.collection.get_statistics()
                logger.info(f"Collection stats: {stats}")
                
                return {
                    'status': 'success',
                    'message': f'Collection {self.collection_name} is accessible',
                    'collection_name': self.collection_name,
                    'stats': stats
                }
                
            except Exception as e:
                logger.error(f"Failed to load collection {self.collection_name}: {e}")
                
                # Try to release and reload collection
                try:
                    self.collection.release()
                    logger.info(f"Released collection {self.collection_name}")
                    
                    # Wait a moment and try again
                    import time
                    time.sleep(1)
                    
                    self.collection.load()
                    logger.info(f"Collection {self.collection_name} reloaded successfully")
                    
                    stats = self.collection.get_statistics()
                    return {
                        'status': 'success',
                        'message': f'Collection {self.collection_name} reloaded and accessible',
                        'collection_name': self.collection_name,
                        'stats': stats
                    }
                    
                except Exception as reload_error:
                    logger.error(f"Failed to reload collection {self.collection_name}: {reload_error}")
                    
                    # Try to work without loading the collection
                    try:
                        logger.info("Attempting to work without loading collection")
                        # Try a simple query without loading
                        test_results = self.collection.query(
                            expr="id >= 0",
                            limit=1,
                            output_fields=["id"]
                        )
                        if test_results:
                            logger.info("Collection accessible without loading")
                            return {
                                'status': 'warning',
                                'message': f'Collection accessible with limited functionality: {str(e)}',
                                'collection_name': self.collection_name
                            }
                    except Exception as query_error:
                        logger.error(f"Collection not accessible even without loading: {query_error}")
                    
                    return {
                        'status': 'error',
                        'message': f'Failed to load/reload collection: {str(e)}',
                        'collection_name': self.collection_name
                    }
                
        except Exception as e:
            logger.error(f"Error checking collection status: {e}")
            return {
                'status': 'error',
                'message': f'Error checking collection: {str(e)}',
                'collection_name': self.collection_name
            }
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        try:
            if not utility.has_collection(self.collection_name):
                return {
                    'collection_name': self.collection_name,
                    'exists': False,
                    'total_vectors': 0,
                    'dimension': self.dimension,
                    'metric_type': self.metric_type,
                    'index_type': self.index_type
                }
            
            self.collection = Collection(self.collection_name)
            
            # Handle different Milvus versions
            try:
                # Try newer API first
                stats = self.collection.get_statistics()
                total_vectors = int(stats['row_count'])
            except (AttributeError, KeyError):
                try:
                    # Fallback to older API
                    total_vectors = self.collection.num_entities
                except AttributeError:
                    # Final fallback
                    total_vectors = 0
            
            return {
                'collection_name': self.collection_name,
                'exists': True,
                'total_vectors': total_vectors,
                'dimension': self.dimension,
                'metric_type': self.metric_type,
                'index_type': self.index_type,
                'index_status': 'indexed' if self.collection.has_index() else 'no_index',
                'connection': {
                    'host': self.host,
                    'port': self.port,
                    'alias': self.connection_alias
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                'collection_name': self.collection_name,
                'exists': False,
                'error': str(e),
                'connection': {
                    'host': self.host,
                    'port': self.port,
                    'alias': self.connection_alias
                }
            }
    
    def get_embeddings_by_target(self, target_id: str) -> List[Dict]:
        """Get all embeddings for a specific target"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            expr = f'target_id == "{target_id}"'
            
            results = self.collection.query(
                expr=expr,
                output_fields=["id", "photo_id", "confidence_score", "created_at"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get embeddings for target {target_id}: {e}")
            return []
    
    def get_embeddings_by_photo(self, photo_id: str) -> List[Dict]:
        """Get all embeddings for a specific photo"""
        try:
            if self.auto_load_collection:
                self.collection.load()
            expr = f'photo_id == "{photo_id}"'
            
            results = self.collection.query(
                expr=expr,
                output_fields=["id", "target_id", "confidence_score", "created_at"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get embeddings for photo {photo_id}: {e}")
            return []
    
    def close_connection(self):
        """Close Milvus connection"""
        try:
            if connections.has_connection(self.connection_alias):
                connections.disconnect(self.connection_alias)
                logger.info("Milvus connection closed")
        except Exception as e:
            logger.error(f"Failed to close Milvus connection: {e}")
