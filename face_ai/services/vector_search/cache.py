"""
Cache Management

Provides caching functionality for vector search operations to improve performance.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, List
import numpy as np
from .interfaces import SearchRequest, SearchResponse
from .config import config_manager

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for vector search operations"""
    
    def __init__(self):
        self._config = config_manager.performance_config
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        
        logger.info("CacheManager initialized")
    
    async def get_search_result(self, request: SearchRequest) -> Optional[SearchResponse]:
        """Get cached search result"""
        try:
            cache_key = self._generate_cache_key(request)
            
            async with self._lock:
                if cache_key in self._cache:
                    cache_entry = self._cache[cache_key]
                    
                    # Check if cache entry is still valid
                    if time.time() - cache_entry['timestamp'] < self._config.cache_ttl:
                        self._access_times[cache_key] = time.time()
                        logger.debug(f"Cache hit for key: {cache_key}")
                        return cache_entry['response']
                    else:
                        # Remove expired entry
                        del self._cache[cache_key]
                        self._access_times.pop(cache_key, None)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached result: {e}")
            return None
    
    async def set_search_result(self, request: SearchRequest, response: SearchResponse) -> None:
        """Cache search result"""
        try:
            cache_key = self._generate_cache_key(request)
            
            async with self._lock:
                # Check cache size limit
                if len(self._cache) >= self._config.cache_max_size:
                    await self._evict_oldest_entries()
                
                # Store cache entry
                self._cache[cache_key] = {
                    'response': response,
                    'timestamp': time.time()
                }
                self._access_times[cache_key] = time.time()
                
                logger.debug(f"Cached result for key: {cache_key}")
                
        except Exception as e:
            logger.error(f"Error caching result: {e}")
    
    async def invalidate_collection_cache(self) -> None:
        """Invalidate all collection-related cache entries"""
        try:
            async with self._lock:
                # Remove all cache entries
                self._cache.clear()
                self._access_times.clear()
                
                logger.info("Collection cache invalidated")
                
        except Exception as e:
            logger.error(f"Error invalidating collection cache: {e}")
    
    async def invalidate_vector_cache(self, vector_id: str) -> None:
        """Invalidate cache entries related to a specific vector"""
        try:
            async with self._lock:
                # Remove cache entries that might contain this vector
                keys_to_remove = []
                for key in self._cache.keys():
                    if str(vector_id) in key:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._access_times.pop(key, None)
                
                logger.debug(f"Invalidated cache for vector {vector_id}")
                
        except Exception as e:
            logger.error(f"Error invalidating vector cache: {e}")
    
    async def _evict_oldest_entries(self) -> None:
        """Evict oldest cache entries to make room"""
        try:
            # Sort by access time and remove oldest entries
            sorted_entries = sorted(self._access_times.items(), key=lambda x: x[1])
            
            # Remove oldest 10% of entries
            evict_count = max(1, len(sorted_entries) // 10)
            
            for key, _ in sorted_entries[:evict_count]:
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
            
            logger.debug(f"Evicted {evict_count} cache entries")
            
        except Exception as e:
            logger.error(f"Error evicting cache entries: {e}")
    
    def _generate_cache_key(self, request: SearchRequest) -> str:
        """Generate cache key for search request"""
        try:
            # Create a hash of the request parameters
            key_data = {
                'vector': request.query_vector.tolist(),
                'top_k': request.top_k,
                'threshold': request.threshold,
                'metric_type': request.metric_type.value,
                'filters': request.filters,
                'include_metadata': request.include_metadata
            }
            
            key_string = json.dumps(key_data, sort_keys=True)
            return hashlib.md5(key_string.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            return str(hash(str(request)))
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            async with self._lock:
                return {
                    'total_entries': len(self._cache),
                    'max_size': self._config.cache_max_size,
                    'ttl': self._config.cache_ttl,
                    'hit_rate': 0.0,  # Would need to track hits/misses
                    'memory_usage': len(str(self._cache))  # Rough estimate
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    async def close(self) -> None:
        """Close cache manager and cleanup"""
        try:
            async with self._lock:
                self._cache.clear()
                self._access_times.clear()
                
            logger.info("CacheManager closed")
            
        except Exception as e:
            logger.error(f"Error closing CacheManager: {e}")


