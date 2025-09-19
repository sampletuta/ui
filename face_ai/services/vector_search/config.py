"""
Configuration Management

Handles configuration loading and validation for the vector search service.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .interfaces import MetricType, IndexType
from .exceptions import ConfigurationError


@dataclass
class MilvusConfig:
    """Milvus connection configuration"""
    host: str = "localhost"
    port: int = 19530
    user: Optional[str] = None
    password: Optional[str] = None
    database: str = "default"
    connection_alias: str = "default"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class CollectionConfig:
    """Collection configuration"""
    name: str = "face_embeddings"
    dimension: int = 512
    metric_type: MetricType = MetricType.COSINE
    index_type: IndexType = IndexType.IVF_FLAT
    index_params: Dict[str, Any] = None
    search_params: Dict[str, Any] = None
    auto_create: bool = True
    auto_load: bool = True
    max_capacity: int = 1000000


@dataclass
class PerformanceConfig:
    """Performance tuning configuration"""
    connection_pool_size: int = 10
    max_connections: int = 100
    batch_size: int = 1000
    search_timeout: float = 30.0
    insert_timeout: float = 60.0
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds
    cache_max_size: int = 10000


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration"""
    enable_metrics: bool = True
    enable_tracing: bool = False
    log_level: str = "INFO"
    log_requests: bool = True
    log_responses: bool = False
    metrics_interval: int = 60  # seconds
    health_check_interval: int = 300  # seconds


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self):
        self._milvus_config: Optional[MilvusConfig] = None
        self._collection_config: Optional[CollectionConfig] = None
        self._performance_config: Optional[PerformanceConfig] = None
        self._monitoring_config: Optional[MonitoringConfig] = None
    
    def load_from_django_settings(self) -> None:
        """Load configuration from Django settings"""
        try:
            from django.conf import settings
            
            # Load Milvus configuration
            milvus_settings = getattr(settings, 'MILVUS_CONFIG', {})
            self._milvus_config = MilvusConfig(
                host=milvus_settings.get('HOST', 'localhost'),
                port=milvus_settings.get('PORT', 19530),
                user=milvus_settings.get('USER'),
                password=milvus_settings.get('PASSWORD'),
                database=milvus_settings.get('DATABASE', 'default'),
                connection_alias=milvus_settings.get('CONNECTION_ALIAS', 'default'),
                timeout=milvus_settings.get('TIMEOUT', 30.0),
                max_retries=milvus_settings.get('MAX_RETRIES', 3),
                retry_delay=milvus_settings.get('RETRY_DELAY', 1.0)
            )
            
            # Load collection configuration
            collection_settings = getattr(settings, 'COLLECTION_CONFIG', {})
            self._collection_config = CollectionConfig(
                name=collection_settings.get('NAME', 'face_embeddings'),
                dimension=collection_settings.get('DIMENSION', 512),
                metric_type=MetricType(collection_settings.get('METRIC_TYPE', 'COSINE')),
                index_type=IndexType(collection_settings.get('INDEX_TYPE', 'IVF_FLAT')),
                index_params=collection_settings.get('INDEX_PARAMS', {'nlist': 1024}),
                search_params=collection_settings.get('SEARCH_PARAMS', {'nprobe': 10}),
                auto_create=collection_settings.get('AUTO_CREATE', True),
                auto_load=collection_settings.get('AUTO_LOAD', True),
                max_capacity=collection_settings.get('MAX_CAPACITY', 1000000)
            )
            
            # Load performance configuration
            perf_settings = getattr(settings, 'PERFORMANCE_CONFIG', {})
            self._performance_config = PerformanceConfig(
                connection_pool_size=perf_settings.get('CONNECTION_POOL_SIZE', 10),
                max_connections=perf_settings.get('MAX_CONNECTIONS', 100),
                batch_size=perf_settings.get('BATCH_SIZE', 1000),
                search_timeout=perf_settings.get('SEARCH_TIMEOUT', 30.0),
                insert_timeout=perf_settings.get('INSERT_TIMEOUT', 60.0),
                enable_caching=perf_settings.get('ENABLE_CACHING', True),
                cache_ttl=perf_settings.get('CACHE_TTL', 3600),
                cache_max_size=perf_settings.get('CACHE_MAX_SIZE', 10000)
            )
            
            # Load monitoring configuration
            monitoring_settings = getattr(settings, 'MONITORING_CONFIG', {})
            self._monitoring_config = MonitoringConfig(
                enable_metrics=monitoring_settings.get('ENABLE_METRICS', True),
                enable_tracing=monitoring_settings.get('ENABLE_TRACING', False),
                log_level=monitoring_settings.get('LOG_LEVEL', 'INFO'),
                log_requests=monitoring_settings.get('LOG_REQUESTS', True),
                log_responses=monitoring_settings.get('LOG_RESPONSES', False),
                metrics_interval=monitoring_settings.get('METRICS_INTERVAL', 60),
                health_check_interval=monitoring_settings.get('HEALTH_CHECK_INTERVAL', 300)
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from Django settings: {e}")
    
    def load_from_env(self) -> None:
        """Load configuration from environment variables"""
        self._milvus_config = MilvusConfig(
            host=os.getenv('MILVUS_HOST', 'localhost'),
            port=int(os.getenv('MILVUS_PORT', '19530')),
            user=os.getenv('MILVUS_USER'),
            password=os.getenv('MILVUS_PASSWORD'),
            database=os.getenv('MILVUS_DATABASE', 'default'),
            connection_alias=os.getenv('MILVUS_CONNECTION_ALIAS', 'default'),
            timeout=float(os.getenv('MILVUS_TIMEOUT', '30.0')),
            max_retries=int(os.getenv('MILVUS_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('MILVUS_RETRY_DELAY', '1.0'))
        )
        
        self._collection_config = CollectionConfig(
            name=os.getenv('COLLECTION_NAME', 'face_embeddings'),
            dimension=int(os.getenv('COLLECTION_DIMENSION', '512')),
            metric_type=MetricType(os.getenv('COLLECTION_METRIC_TYPE', 'COSINE')),
            index_type=IndexType(os.getenv('COLLECTION_INDEX_TYPE', 'IVF_FLAT')),
            auto_create=os.getenv('COLLECTION_AUTO_CREATE', 'true').lower() == 'true',
            auto_load=os.getenv('COLLECTION_AUTO_LOAD', 'true').lower() == 'true',
            max_capacity=int(os.getenv('COLLECTION_MAX_CAPACITY', '1000000'))
        )
    
    def validate_config(self) -> None:
        """Validate configuration parameters"""
        if not self._milvus_config:
            raise ConfigurationError("Milvus configuration not loaded")
        
        if not self._collection_config:
            raise ConfigurationError("Collection configuration not loaded")
        
        if self._milvus_config.port <= 0 or self._milvus_config.port > 65535:
            raise ConfigurationError("Invalid port number")
        
        if self._collection_config.dimension <= 0:
            raise ConfigurationError("Invalid dimension")
        
        if self._collection_config.max_capacity <= 0:
            raise ConfigurationError("Invalid max capacity")
    
    @property
    def milvus_config(self) -> MilvusConfig:
        if not self._milvus_config:
            raise ConfigurationError("Milvus configuration not loaded")
        return self._milvus_config
    
    @property
    def collection_config(self) -> CollectionConfig:
        if not self._collection_config:
            raise ConfigurationError("Collection configuration not loaded")
        return self._collection_config
    
    @property
    def performance_config(self) -> PerformanceConfig:
        if not self._performance_config:
            raise ConfigurationError("Performance configuration not loaded")
        return self._performance_config
    
    @property
    def monitoring_config(self) -> MonitoringConfig:
        if not self._monitoring_config:
            raise ConfigurationError("Monitoring configuration not loaded")
        return self._monitoring_config


# Global configuration manager instance
config_manager = ConfigManager()
