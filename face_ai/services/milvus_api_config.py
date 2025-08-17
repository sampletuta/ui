"""
Configuration for Milvus API Service

This file contains configuration options for the Milvus API service.
You can override these settings in your Django settings.py file.
"""

# Default Milvus API configuration
DEFAULT_MILVUS_API_CONFIG = {
    # API server configuration
    'API_BASE_URL': 'http://localhost:8001',
    'API_KEY': '',  # Leave empty for no authentication
    'TIMEOUT': 30,  # Request timeout in seconds
    
    # Collection configuration
    'COLLECTION_NAME': 'watchlist',
    
    # Retry configuration
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1,  # seconds
    
    # Batch operation configuration
    'BATCH_SIZE': 100,
    'BATCH_TIMEOUT': 60,  # seconds
    
    # Logging configuration
    'LOG_LEVEL': 'INFO',
    'LOG_REQUESTS': True,
    'LOG_RESPONSES': False,
    
    # Health check configuration
    'HEALTH_CHECK_INTERVAL': 300,  # seconds
    'HEALTH_CHECK_TIMEOUT': 10,    # seconds
}

# API endpoint paths (relative to base URL)
MILVUS_API_ENDPOINTS = {
    'search': '/api/milvus/search',
    'add': '/api/milvus/add',
    'delete': '/api/milvus/delete',
    'update': '/api/milvus/update',
    'status': '/api/milvus/status',
    'stats': '/api/milvus/stats',
    'query': '/api/milvus/query',
    'health': '/api/milvus/health',
    'batch': '/api/milvus/batch',
    'collection': {
        'create': '/api/milvus/collection/create',
        'drop': '/api/milvus/collection/drop',
        'list': '/api/milvus/collection/list',
        'info': '/api/milvus/collection/info'
    }
}

# HTTP status codes and their meanings
HTTP_STATUS_CODES = {
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    204: 'No Content',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    307: 'Temporary Redirect',
    308: 'Permanent Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    409: 'Conflict',
    422: 'Unprocessable Entity',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout'
}

# Error messages for common scenarios
ERROR_MESSAGES = {
    'connection_failed': 'Failed to connect to Milvus API server',
    'timeout': 'Request timed out',
    'authentication_failed': 'Authentication failed',
    'collection_not_found': 'Collection not found',
    'invalid_embedding': 'Invalid embedding data',
    'insufficient_permissions': 'Insufficient permissions',
    'rate_limited': 'Rate limit exceeded',
    'server_error': 'Internal server error',
    'invalid_request': 'Invalid request data',
    'embedding_not_found': 'Embedding not found'
}

# Success messages
SUCCESS_MESSAGES = {
    'embedding_inserted': 'Embedding inserted successfully',
    'embedding_updated': 'Embedding updated successfully',
    'embedding_deleted': 'Embedding deleted successfully',
    'search_completed': 'Search completed successfully',
    'collection_created': 'Collection created successfully',
    'collection_dropped': 'Collection dropped successfully',
    'health_check_passed': 'Health check passed',
    'batch_operations_completed': 'Batch operations completed successfully'
}

# Validation rules
VALIDATION_RULES = {
    'embedding_dimension': {
        'min': 64,
        'max': 2048,
        'default': 512
    },
    'confidence_score': {
        'min': 0.0,
        'max': 1.0,
        'default': 0.5
    },
    'threshold': {
        'min': 0.0,
        'max': 1.0,
        'default': 0.6
    },
    'top_k': {
        'min': 1,
        'max': 1000,
        'default': 10
    },
    'batch_size': {
        'min': 1,
        'max': 10000,
        'default': 100
    }
}

# Performance tuning parameters
PERFORMANCE_CONFIG = {
    'connection_pool_size': 10,
    'max_connections': 100,
    'keep_alive_timeout': 60,
    'request_timeout': 30,
    'response_timeout': 60,
    'max_retries': 3,
    'backoff_factor': 0.3,
    'circuit_breaker_threshold': 5,
    'circuit_breaker_timeout': 60
}

# Monitoring and metrics
MONITORING_CONFIG = {
    'enable_metrics': True,
    'metrics_interval': 60,  # seconds
    'enable_tracing': False,
    'tracing_sample_rate': 0.1,
    'enable_health_checks': True,
    'health_check_interval': 300,  # seconds
    'enable_performance_logging': True,
    'performance_log_threshold': 1000  # milliseconds
}
