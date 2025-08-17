"""
Async Milvus Service for parallel processing.

This service provides async-compatible methods for managing face embeddings in Milvus
vector database with support for parallel operations and batch processing.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from pymilvus import connections, Collection, utility
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
from asgiref.sync import sync_to_async
import time

logger = logging.getLogger(__name__)

class AsyncMilvusService:
    """Async service for managing face embeddings in Milvus vector database"""
    
    def __init__(self, host=None, port=None, max_workers=4):
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
        self.max_workers = max_workers
        
        # Thread pool for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # Ensure connection and collection setup
        self._ensure_connection_sync()
        
        # Auto-create collection if enabled
        if self.auto_create_collection:
            self._create_collection_if_not_exists_sync()
    
    async def _ensure_connection_async(self):
        """Ensure connection to Milvus asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.thread_pool,
                self._ensure_connection_sync
            )
        except Exception as e:
            logger.error(f"Failed to ensure async Milvus connection: {e}")
            raise
    
    def _ensure_connection_sync(self):
        """Ensure connection to Milvus (synchronous)"""
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
    
    async def _create_collection_if_not_exists_async(self):
        """Create Milvus collection if it doesn't exist asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.thread_pool,
                self._create_collection_if_not_exists_sync
            )
        except Exception as e:
            logger.error(f"Failed to create collection asynchronously: {e}")
            raise
    
    def _create_collection_if_not_exists_sync(self):
        """Create Milvus collection if it doesn't exist (synchronous)"""
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
                FieldSchema(name="photo_id", dtype=DataType.VARCHAR, max_length=36),
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
    
    async def get_collection_stats_async(self) -> Dict:
        """Get collection statistics asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                self.thread_pool,
                self._get_collection_stats_sync
            )
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats asynchronously: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_collection_stats_sync(self) -> Dict:
        """Get collection statistics (synchronous)"""
        try:
            if not hasattr(self, 'collection'):
                self.collection = Collection(self.collection_name)
            
            # Get collection statistics
            stats = self.collection.get_statistics()
            
            # Get collection info
            schema = self.collection.schema
            fields = [field.name for field in schema.fields]
            
            return {
                'success': True,
                'collection_name': self.collection_name,
                'total_rows': stats.get('row_count', 0),
                'fields': fields,
                'dimension': self.dimension,
                'metric_type': self.metric_type,
                'index_type': self.index_type,
                'connection': {
                    'host': self.host,
                    'port': self.port,
                    'alias': self.connection_alias
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def insert_face_embeddings_parallel(self, embeddings_data: List[Dict]) -> List[int]:
        """Insert face embeddings into Milvus collection with parallel processing"""
        try:
            start_time = time.time()
            
            # Process insertions in parallel batches
            batch_size = 100  # Milvus recommended batch size
            batches = [embeddings_data[i:i + batch_size] for i in range(0, len(embeddings_data), batch_size)]
            
            # Process batches in parallel
            batch_tasks = []
            for batch in batches:
                task = self._insert_batch_async(batch)
                batch_tasks.append(task)
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            all_ids = []
            successful_batches = 0
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch insertion failed: {result}")
                    continue
                
                if result['success']:
                    all_ids.extend(result.get('ids', []))
                    successful_batches += 1
            
            processing_time = time.time() - start_time
            
            logger.info(f"Inserted {len(all_ids)} embeddings in {successful_batches} batches in {processing_time:.2f}s")
            
            return all_ids
            
        except Exception as e:
            logger.error(f"Error in parallel embedding insertion: {e}")
            return []
    
    async def insert_face_embeddings_sequential(self, embeddings_data: List[Dict]) -> List[int]:
        """Insert face embeddings into Milvus collection sequentially"""
        try:
            start_time = time.time()
            
            # Process insertions sequentially
            all_ids = []
            
            for embedding_data in embeddings_data:
                result = await self._insert_single_embedding_async(embedding_data)
                if result['success']:
                    all_ids.extend(result.get('ids', []))
            
            processing_time = time.time() - start_time
            
            logger.info(f"Inserted {len(all_ids)} embeddings sequentially in {processing_time:.2f}s")
            
            return all_ids
            
        except Exception as e:
            logger.error(f"Error in sequential embedding insertion: {e}")
            return []
    
    async def _insert_batch_async(self, batch_data: List[Dict]) -> Dict:
        """Insert a batch of embeddings asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._insert_batch_sync,
                batch_data
            )
            return result
        except Exception as e:
            logger.error(f"Error inserting batch asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'ids': []
            }
    
    async def _insert_single_embedding_async(self, embedding_data: Dict) -> Dict:
        """Insert a single embedding asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._insert_single_embedding_sync,
                embedding_data
            )
            return result
        except Exception as e:
            logger.error(f"Error inserting single embedding asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'ids': []
            }
    
    def _insert_batch_sync(self, batch_data: List[Dict]) -> Dict:
        """Insert a batch of embeddings (synchronous)"""
        try:
            if not hasattr(self, 'collection'):
                self.collection = Collection(self.collection_name)
            
            # Prepare data for insertion
            embeddings = []
            target_ids = []
            photo_ids = []
            confidence_scores = []
            created_ats = []
            
            for data in batch_data:
                embeddings.append(data.get('embedding', []))
                target_ids.append(data.get('target_id', ''))
                photo_ids.append(data.get('photo_id', ''))
                confidence_scores.append(data.get('confidence_score', 0.0))
                created_ats.append(data.get('created_at', ''))
            
            # Insert data
            insert_data = [
                embeddings,
                target_ids,
                photo_ids,
                confidence_scores,
                created_ats
            ]
            
            result = self.collection.insert(insert_data)
            
            return {
                'success': True,
                'ids': result.primary_keys,
                'batch_size': len(batch_data)
            }
            
        except Exception as e:
            logger.error(f"Error inserting batch: {e}")
            return {
                'success': False,
                'error': str(e),
                'ids': []
            }
    
    def _insert_single_embedding_sync(self, embedding_data: Dict) -> Dict:
        """Insert a single embedding (synchronous)"""
        try:
            if not hasattr(self, 'collection'):
                self.collection = Collection(self.collection_name)
            
            # Prepare data for insertion
            embeddings = [embedding_data.get('embedding', [])]
            target_ids = [embedding_data.get('target_id', '')]
            photo_ids = [embedding_data.get('photo_id', '')]
            confidence_scores = [embedding_data.get('confidence_score', 0.0)]
            created_ats = [embedding_data.get('created_at', '')]
            
            # Insert data
            insert_data = [
                embeddings,
                target_ids,
                photo_ids,
                confidence_scores,
                created_ats
            ]
            
            result = self.collection.insert(insert_data)
            
            return {
                'success': True,
                'ids': result.primary_keys
            }
            
        except Exception as e:
            logger.error(f"Error inserting single embedding: {e}")
            return {
                'success': False,
                'error': str(e),
                'ids': []
            }
    
    async def delete_face_embeddings_parallel(self, vector_ids: List[int]) -> int:
        """Delete face embeddings from Milvus by vector IDs with parallel processing"""
        try:
            start_time = time.time()
            
            # Process deletions in parallel batches
            batch_size = 100
            batches = [vector_ids[i:i + batch_size] for i in range(0, len(vector_ids), batch_size)]
            
            # Process batches in parallel
            batch_tasks = []
            for batch in batches:
                task = self._delete_batch_async(batch)
                batch_tasks.append(task)
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            total_deleted = 0
            successful_batches = 0
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch deletion failed: {result}")
                    continue
                
                if result['success']:
                    total_deleted += result.get('deleted_count', 0)
                    successful_batches += 1
            
            processing_time = time.time() - start_time
            
            logger.info(f"Deleted {total_deleted} embeddings in {successful_batches} batches in {processing_time:.2f}s")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error in parallel embedding deletion: {e}")
            return 0
    
    async def delete_face_embeddings_sequential(self, vector_ids: List[int]) -> int:
        """Delete face embeddings from Milvus by vector IDs sequentially"""
        try:
            start_time = time.time()
            
            # Process deletions sequentially
            total_deleted = 0
            
            for vector_id in vector_ids:
                result = await self._delete_single_embedding_async(vector_id)
                if result['success']:
                    total_deleted += result.get('deleted_count', 0)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Deleted {total_deleted} embeddings sequentially in {processing_time:.2f}s")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error in sequential embedding deletion: {e}")
            return 0
    
    async def _delete_batch_async(self, batch_ids: List[int]) -> Dict:
        """Delete a batch of embeddings asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._delete_batch_sync,
                batch_ids
            )
            return result
        except Exception as e:
            logger.error(f"Error deleting batch asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    async def _delete_single_embedding_async(self, vector_id: int) -> Dict:
        """Delete a single embedding asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._delete_single_embedding_sync,
                vector_id
            )
            return result
        except Exception as e:
            logger.error(f"Error deleting single embedding asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    def _delete_batch_sync(self, batch_ids: List[int]) -> Dict:
        """Delete a batch of embeddings (synchronous)"""
        try:
            if not hasattr(self, 'collection'):
                self.collection = Collection(self.collection_name)
            
            # Delete by IDs
            expr = f"id in {batch_ids}"
            result = self.collection.delete(expr)
            
            return {
                'success': True,
                'deleted_count': len(batch_ids),
                'batch_size': len(batch_ids)
            }
            
        except Exception as e:
            logger.error(f"Error deleting batch: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    def _delete_single_embedding_sync(self, vector_id: int) -> Dict:
        """Delete a single embedding (synchronous)"""
        try:
            if not hasattr(self, 'collection'):
                self.collection = Collection(self.collection_name)
            
            # Delete by ID
            expr = f"id == {vector_id}"
            result = self.collection.delete(expr)
            
            return {
                'success': True,
                'deleted_count': 1
            }
            
        except Exception as e:
            logger.error(f"Error deleting single embedding: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    async def search_face_embeddings_async(self, query_embedding: List[float], top_k: int = 10, 
                                          search_params: Dict = None) -> Dict:
        """Search for similar face embeddings asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._search_face_embeddings_sync,
                query_embedding,
                top_k,
                search_params
            )
            return result
        except Exception as e:
            logger.error(f"Error searching embeddings asynchronously: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def _search_face_embeddings_sync(self, query_embedding: List[float], top_k: int = 10, 
                                    search_params: Dict = None) -> Dict:
        """Search for similar face embeddings (synchronous)"""
        try:
            if not hasattr(self, 'collection'):
                self.collection = Collection(self.collection_name)
            
            # Load collection if not loaded
            if not self.collection.is_empty:
                self.collection.load()
            
            # Use default search params if none provided
            if search_params is None:
                search_params = self.search_params
            
            # Perform search
            search_params['metric_type'] = self.metric_type
            search_params['params'] = search_params.get('params', {})
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["target_id", "photo_id", "confidence_score", "created_at"]
            )
            
            # Process results
            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append({
                        'id': hit.id,
                        'distance': hit.distance,
                        'score': hit.score,
                        'target_id': hit.entity.get('target_id', ''),
                        'photo_id': hit.entity.get('photo_id', ''),
                        'confidence_score': hit.entity.get('confidence_score', 0.0),
                        'created_at': hit.entity.get('created_at', '')
                    })
            
            return {
                'success': True,
                'results': search_results,
                'total_results': len(search_results),
                'query_dimension': len(query_embedding)
            }
            
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    async def batch_search_embeddings_async(self, query_embeddings: List[List[float]], top_k: int = 10,
                                           search_params: Dict = None, max_workers: int = None) -> Dict:
        """Batch search for multiple query embeddings with parallel processing"""
        if max_workers is None:
            max_workers = self.max_workers
        
        try:
            start_time = time.time()
            
            # Process searches in parallel
            search_tasks = []
            for query_embedding in query_embeddings:
                task = self.search_face_embeddings_async(query_embedding, top_k, search_params)
                search_tasks.append(task)
            
            # Wait for all searches to complete
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Collect results
            all_results = []
            successful_searches = 0
            
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    logger.error(f"Search {i} failed: {result}")
                    continue
                
                if result['success']:
                    all_results.extend(result.get('results', []))
                    successful_searches += 1
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'total_queries': len(query_embeddings),
                'successful_searches': successful_searches,
                'total_results': len(all_results),
                'results': all_results,
                'processing_time': processing_time,
                'max_workers': max_workers
            }
            
        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_queries': len(query_embeddings)
            }
    
    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
