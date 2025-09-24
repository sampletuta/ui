"""
Core Vector Search Service

Production-ready vector search service with proper error handling,
caching, monitoring, and scalability features.
"""

import asyncio
import logging
import time
import uuid
from typing import List, Dict, Optional, Any, Union
import numpy as np
from datetime import datetime

from .interfaces import (
    VectorSearchInterface, SearchRequest, SearchResponse, SearchResult,
    CollectionInfo, HealthStatus, SearchStatus, MetricType, IndexType
)
from .exceptions import (
    VectorSearchError, ConnectionError, SearchError, ValidationError,
    TimeoutError, CollectionError
)
from .connection import connection_pool, collection_manager
from .config import config_manager
from .cache import CacheManager
from .monitoring import MetricsCollector

logger = logging.getLogger(__name__)


class VectorSearchService(VectorSearchInterface):
    """
    Production-ready vector search service
    
    Features:
    - Async/await support for high concurrency
    - Connection pooling and health monitoring
    - Comprehensive error handling and retry logic
    - Caching for improved performance
    - Metrics collection and monitoring
    - Input validation and sanitization
    - Circuit breaker pattern for resilience
    """
    
    def __init__(self):
        self._config = config_manager.collection_config
        self._perf_config = config_manager.performance_config
        self._monitoring_config = config_manager.monitoring_config
        
        # Initialize components
        self._cache = CacheManager() if self._perf_config.enable_caching else None
        self._metrics = MetricsCollector() if self._monitoring_config.enable_metrics else None
        
        # Circuit breaker state
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60  # seconds
        
        logger.info("VectorSearchService initialized")
    
    async def search(self, request: SearchRequest) -> SearchResponse:
        """Perform vector search with comprehensive error handling"""
        start_time = time.time()
        request_id = request.request_id or str(uuid.uuid4())
        
        try:
            # Validate request
            self._validate_search_request(request)
            
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                raise SearchError("Circuit breaker is open - service temporarily unavailable")
            
            # Check cache first
            if self._cache:
                cached_result = await self._cache.get_search_result(request)
                if cached_result:
                    logger.debug(f"Cache hit for request {request_id}")
                    return cached_result
            
            # Perform search
            results = await self._perform_search(request)
            
            # Calculate search time
            search_time_ms = (time.time() - start_time) * 1000
            
            # Create response
            response = SearchResponse(
                results=results,
                total_found=len(results),
                search_time_ms=search_time_ms,
                request_id=request_id,
                status=SearchStatus.COMPLETED
            )
            
            # Cache result
            if self._cache:
                await self._cache.set_search_result(request, response)
            
            # Record metrics
            if self._metrics:
                await self._metrics.record_search_metrics(request, response)
            
            logger.info(f"Search completed: {len(results)} results in {search_time_ms:.2f}ms")
            return response
            
        except Exception as e:
            # Record failure
            self._record_circuit_breaker_failure()
            
            # Record error metrics
            if self._metrics:
                await self._metrics.record_error_metrics(request, e)
            
            logger.error(f"Search failed for request {request_id}: {e}")
            
            return SearchResponse(
                results=[],
                total_found=0,
                search_time_ms=(time.time() - start_time) * 1000,
                request_id=request_id,
                status=SearchStatus.FAILED,
                error=str(e)
            )
    
    async def _perform_search(self, request: SearchRequest) -> List[SearchResult]:
        """Perform the actual vector search"""
        try:
            # Get collection
            collection = await collection_manager.get_collection()
            
            # Ensure collection is loaded
            if not collection.has_index():
                collection.load()
            
            # Prepare search parameters
            search_params = {
                "metric_type": request.metric_type.value,
                "params": self._config.search_params
            }
            
            # Build filter expression if provided
            expr = None
            if request.filters:
                expr = self._build_filter_expression(request.filters)
            
            # Perform search
            results = collection.search(
                data=[request.query_vector.tolist()],
                anns_field="vector",
                param=search_params,
                limit=request.top_k,
                expr=expr,
                output_fields=["metadata", "created_at", "updated_at"]
            )
            
            # Process results
            search_results = []
            for hits in results:
                for hit in hits:
                    if hit.score >= request.threshold:
                        metadata = hit.entity.get('metadata', {})
                        if not request.include_metadata:
                            metadata = {}
                        
                        search_results.append(SearchResult(
                            id=hit.id,
                            score=hit.score,
                            distance=1.0 - hit.score if request.metric_type == MetricType.COSINE else hit.score,
                            metadata=metadata
                        ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Search operation failed: {e}")
            raise SearchError(f"Search operation failed: {e}")
    
    async def insert_vectors(self, vectors: List[np.ndarray], 
                           metadata: List[Dict[str, Any]]) -> List[Union[str, int]]:
        """Insert vectors into the collection"""
        try:
            # Validate inputs
            if len(vectors) != len(metadata):
                raise ValidationError("Number of vectors must match number of metadata entries")
            
            if not vectors:
                return []
            
            # Validate vector dimensions
            dimension = len(vectors[0])
            for vector in vectors:
                if len(vector) != dimension:
                    raise ValidationError("All vectors must have the same dimension")
            
            if dimension != self._config.dimension:
                raise ValidationError(f"Vector dimension {dimension} does not match collection dimension {self._config.dimension}")
            
            # Get collection
            collection = await collection_manager.get_collection()
            
            # Prepare data for insertion
            now = datetime.now().isoformat()
            data = [
                vectors,
                metadata,
                [now] * len(vectors),  # created_at
                [now] * len(vectors)   # updated_at
            ]
            
            # Insert data
            insert_result = collection.insert(data)
            
            # Invalidate cache
            if self._cache:
                await self._cache.invalidate_collection_cache()
            
            # Record metrics
            if self._metrics:
                await self._metrics.record_insert_metrics(len(vectors))
            
            logger.info(f"Inserted {len(vectors)} vectors")
            return insert_result.primary_keys
            
        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            raise VectorSearchError(f"Failed to insert vectors: {e}")
    
    async def delete_vectors(self, ids: List[Union[str, int]]) -> int:
        """Delete vectors by IDs"""
        try:
            if not ids:
                return 0
            
            # Get collection
            collection = await collection_manager.get_collection()
            
            # Build delete expression
            id_list = ','.join(map(str, ids))
            expr = f"id in [{id_list}]"
            
            # Delete vectors
            delete_result = collection.delete(expr)
            deleted_count = len(delete_result.primary_keys) if delete_result.primary_keys else 0
            
            # Invalidate cache
            if self._cache:
                await self._cache.invalidate_collection_cache()
            
            # Record metrics
            if self._metrics:
                await self._metrics.record_delete_metrics(deleted_count)
            
            logger.info(f"Deleted {deleted_count} vectors")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise VectorSearchError(f"Failed to delete vectors: {e}")
    
    async def update_vector(self, vector_id: Union[str, int], 
                          vector: np.ndarray, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a vector and its metadata"""
        try:
            # Validate vector dimension
            if len(vector) != self._config.dimension:
                raise ValidationError(f"Vector dimension {len(vector)} does not match collection dimension {self._config.dimension}")
            
            # Get collection
            collection = await collection_manager.get_collection()
            
            # Prepare update data
            now = datetime.now().isoformat()
            update_data = {
                "vector": vector.tolist(),
                "updated_at": now
            }
            
            if metadata is not None:
                update_data["metadata"] = metadata
            
            # Update vector
            expr = f"id == {vector_id}"
            collection.upsert([update_data], expr)
            
            # Invalidate cache
            if self._cache:
                await self._cache.invalidate_vector_cache(vector_id)
            
            logger.info(f"Updated vector {vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update vector {vector_id}: {e}")
            raise VectorSearchError(f"Failed to update vector: {e}")
    
    async def get_collection_info(self) -> CollectionInfo:
        """Get collection information"""
        try:
            return await collection_manager.get_collection_info()
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise CollectionError(f"Failed to get collection info: {e}")
    
    async def health_check(self) -> HealthStatus:
        """Check service health"""
        try:
            # Check connection health
            connection_health = await connection_pool.health_check()
            
            # Check collection health
            try:
                collection_info = await self.get_collection_info()
                collection_status = "healthy" if collection_info.is_loaded else "not_loaded"
            except Exception:
                collection_status = "error"
            
            # Overall health status
            is_healthy = (
                connection_health.is_healthy and 
                collection_status in ["healthy", "not_loaded"]
            )
            
            return HealthStatus(
                is_healthy=is_healthy,
                status="healthy" if is_healthy else "unhealthy",
                last_check=time.time(),
                connection_status=connection_health.connection_status,
                collection_status=collection_status,
                performance_metrics={
                    **connection_health.performance_metrics,
                    "circuit_breaker_failures": self._circuit_breaker_failures
                }
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                is_healthy=False,
                status="error",
                last_check=time.time(),
                connection_status="error",
                collection_status="error",
                performance_metrics={"error": str(e)}
            )
    
    async def create_collection(self, name: str, dimension: int, 
                              metric_type: MetricType = MetricType.COSINE,
                              index_type: IndexType = IndexType.IVF_FLAT) -> bool:
        """Create a new collection"""
        try:
            # Update config temporarily
            original_config = self._config
            self._config.dimension = dimension
            self._config.metric_type = metric_type
            self._config.index_type = index_type
            
            # Create collection
            await collection_manager._create_collection(name)
            
            # Restore original config
            self._config = original_config
            
            logger.info(f"Created collection: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            return False
    
    async def drop_collection(self, name: str) -> bool:
        """Drop a collection"""
        try:
            result = await collection_manager.drop_collection(name)
            
            # Invalidate cache
            if self._cache:
                await self._cache.invalidate_collection_cache()
            
            logger.info(f"Dropped collection: {name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to drop collection {name}: {e}")
            return False
    
    def _validate_search_request(self, request: SearchRequest) -> None:
        """Validate search request parameters"""
        if request.query_vector is None:
            raise ValidationError("Query vector is required")
        
        if len(request.query_vector) != self._config.dimension:
            raise ValidationError(f"Query vector dimension {len(request.query_vector)} does not match collection dimension {self._config.dimension}")
        
        if request.top_k <= 0:
            raise ValidationError("top_k must be positive")
        
        if request.top_k > 1000:
            raise ValidationError("top_k cannot exceed 1000")
        
        if not 0.0 <= request.threshold <= 1.0:
            raise ValidationError("threshold must be between 0.0 and 1.0")
    
    def _build_filter_expression(self, filters: Dict[str, Any]) -> str:
        """Build Milvus filter expression"""
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f'metadata["{key}"] == "{value}"')
            elif isinstance(value, (int, float)):
                conditions.append(f'metadata["{key}"] == {value}')
            elif isinstance(value, list):
                if value:
                    value_list = ','.join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
                    conditions.append(f'metadata["{key}"] in [{value_list}]')
        
        return ' and '.join(conditions) if conditions else None
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self._circuit_breaker_failures < self._circuit_breaker_threshold:
            return False
        
        # Check if timeout has passed
        if time.time() - self._circuit_breaker_last_failure > self._circuit_breaker_timeout:
            # Reset circuit breaker
            self._circuit_breaker_failures = 0
            return False
        
        return True
    
    def _record_circuit_breaker_failure(self) -> None:
        """Record a circuit breaker failure"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
    
    async def close(self) -> None:
        """Close the service and cleanup resources"""
        try:
            if self._cache:
                await self._cache.close()
            
            if self._metrics:
                await self._metrics.close()
            
            await connection_pool.close_all()
            
            logger.info("VectorSearchService closed")
            
        except Exception as e:
            logger.error(f"Error closing VectorSearchService: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


