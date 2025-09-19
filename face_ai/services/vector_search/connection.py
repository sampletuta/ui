"""
Connection Management

Handles Milvus connection pooling, health checks, and connection lifecycle.
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from contextlib import asynccontextmanager
from pymilvus import connections, Collection, utility
from .config import config_manager
from .exceptions import ConnectionError, TimeoutError
from .interfaces import HealthStatus, CollectionInfo, MetricType, IndexType

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Manages Milvus connection pool"""
    
    def __init__(self):
        self._connections: Dict[str, bool] = {}
        self._active_connections: Set[str] = set()
        self._lock = asyncio.Lock()
        self._config = config_manager.milvus_config
    
    async def get_connection(self, alias: Optional[str] = None) -> str:
        """Get a connection from the pool"""
        alias = alias or self._config.connection_alias
        
        async with self._lock:
            if alias not in self._connections:
                await self._create_connection(alias)
            
            if not self._connections[alias]:
                await self._reconnect(alias)
            
            self._active_connections.add(alias)
            return alias
    
    async def release_connection(self, alias: str) -> None:
        """Release a connection back to the pool"""
        async with self._lock:
            self._active_connections.discard(alias)
    
    async def _create_connection(self, alias: str) -> None:
        """Create a new connection"""
        try:
            connections.connect(
                alias=alias,
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                db_name=self._config.database,
                timeout=self._config.timeout
            )
            self._connections[alias] = True
            logger.info(f"Created Milvus connection: {alias}")
        except Exception as e:
            self._connections[alias] = False
            logger.error(f"Failed to create Milvus connection {alias}: {e}")
            raise ConnectionError(f"Failed to create connection: {e}")
    
    async def _reconnect(self, alias: str) -> None:
        """Reconnect to Milvus"""
        try:
            if connections.has_connection(alias):
                connections.disconnect(alias)
            
            await self._create_connection(alias)
            logger.info(f"Reconnected to Milvus: {alias}")
        except Exception as e:
            logger.error(f"Failed to reconnect to Milvus {alias}: {e}")
            raise ConnectionError(f"Failed to reconnect: {e}")
    
    async def health_check(self) -> HealthStatus:
        """Check connection health"""
        try:
            alias = await self.get_connection()
            
            # Test basic connectivity
            if not connections.has_connection(alias):
                return HealthStatus(
                    is_healthy=False,
                    status="disconnected",
                    last_check=asyncio.get_event_loop().time(),
                    connection_status="disconnected",
                    collection_status="unknown",
                    performance_metrics={}
                )
            
            # Test query capability
            collections = utility.list_collections()
            
            await self.release_connection(alias)
            
            return HealthStatus(
                is_healthy=True,
                status="healthy",
                last_check=asyncio.get_event_loop().time(),
                connection_status="connected",
                collection_status="accessible",
                performance_metrics={
                    "active_connections": len(self._active_connections),
                    "total_connections": len(self._connections)
                }
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                is_healthy=False,
                status="unhealthy",
                last_check=asyncio.get_event_loop().time(),
                connection_status="error",
                collection_status="error",
                performance_metrics={"error": str(e)}
            )
    
    async def close_all(self) -> None:
        """Close all connections"""
        async with self._lock:
            for alias in list(self._connections.keys()):
                try:
                    if connections.has_connection(alias):
                        connections.disconnect(alias)
                    logger.info(f"Closed Milvus connection: {alias}")
                except Exception as e:
                    logger.error(f"Failed to close connection {alias}: {e}")
            
            self._connections.clear()
            self._active_connections.clear()


class CollectionManager:
    """Manages Milvus collections"""
    
    def __init__(self, connection_pool: ConnectionPool):
        self._connection_pool = connection_pool
        self._collections: Dict[str, Collection] = {}
        self._config = config_manager.collection_config
        self._lock = asyncio.Lock()
    
    async def get_collection(self, name: Optional[str] = None) -> Collection:
        """Get a collection instance"""
        name = name or self._config.name
        
        async with self._lock:
            if name not in self._collections:
                await self._load_collection(name)
            
            return self._collections[name]
    
    async def _load_collection(self, name: str) -> None:
        """Load a collection"""
        try:
            alias = await self._connection_pool.get_connection()
            
            if not utility.has_collection(name):
                if self._config.auto_create:
                    await self._create_collection(name)
                else:
                    raise ConnectionError(f"Collection {name} does not exist")
            
            collection = Collection(name)
            
            # Auto-load if configured
            if self._config.auto_load:
                try:
                    collection.load()
                except Exception as e:
                    logger.warning(f"Failed to auto-load collection {name}: {e}")
            
            self._collections[name] = collection
            await self._connection_pool.release_connection(alias)
            
            logger.info(f"Loaded collection: {name}")
            
        except Exception as e:
            logger.error(f"Failed to load collection {name}: {e}")
            raise ConnectionError(f"Failed to load collection: {e}")
    
    async def _create_collection(self, name: str) -> None:
        """Create a new collection"""
        try:
            from pymilvus import FieldSchema, CollectionSchema, DataType
            
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self._config.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="updated_at", dtype=DataType.VARCHAR, max_length=50)
            ]
            
            schema = CollectionSchema(fields, description=f"Vector collection: {name}")
            
            # Create collection
            collection = Collection(name, schema)
            
            # Create index
            index_params = {
                "metric_type": self._config.metric_type.value,
                "index_type": self._config.index_type.value,
                "params": self._config.index_params
            }
            collection.create_index(field_name="vector", index_params=index_params)
            
            logger.info(f"Created collection: {name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise ConnectionError(f"Failed to create collection: {e}")
    
    async def get_collection_info(self, name: Optional[str] = None) -> CollectionInfo:
        """Get collection information"""
        name = name or self._config.name
        
        try:
            alias = await self._connection_pool.get_connection()
            
            if not utility.has_collection(name):
                await self._connection_pool.release_connection(alias)
                raise ConnectionError(f"Collection {name} does not exist")
            
            collection = Collection(name)
            
            # Get collection stats
            try:
                stats = collection.get_statistics()
                total_vectors = int(stats.get('row_count', 0))
            except (AttributeError, KeyError):
                total_vectors = 0
            
            # Check if collection is loaded
            is_loaded = collection.has_index()
            
            await self._connection_pool.release_connection(alias)
            
            return CollectionInfo(
                name=name,
                dimension=self._config.dimension,
                total_vectors=total_vectors,
                metric_type=self._config.metric_type,
                index_type=self._config.index_type,
                is_loaded=is_loaded,
                created_at=asyncio.get_event_loop().time(),  # Placeholder
                updated_at=asyncio.get_event_loop().time()  # Placeholder
            )
            
        except Exception as e:
            logger.error(f"Failed to get collection info for {name}: {e}")
            raise ConnectionError(f"Failed to get collection info: {e}")
    
    async def drop_collection(self, name: str) -> bool:
        """Drop a collection"""
        try:
            alias = await self._connection_pool.get_connection()
            
            if utility.has_collection(name):
                utility.drop_collection(name)
                logger.info(f"Dropped collection: {name}")
            
            # Remove from cache
            async with self._lock:
                self._collections.pop(name, None)
            
            await self._connection_pool.release_connection(alias)
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop collection {name}: {e}")
            return False


# Global instances
connection_pool = ConnectionPool()
collection_manager = CollectionManager(connection_pool)
