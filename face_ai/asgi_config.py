"""
ASGI Configuration for Face AI Application.

This module provides configuration settings for async/await support and parallel processing.
"""

import os
from typing import Dict, Any

# ASGI Application Settings
ASGI_APP_NAME = 'face_ai'
ASGI_APP_HOST = os.getenv('FACE_AI_ASGI_HOST', '0.0.0.0')
ASGI_APP_PORT = int(os.getenv('FACE_AI_ASGI_PORT', 8001))
ASGI_APP_RELOAD = os.getenv('FACE_AI_ASGI_RELOAD', 'true').lower() == 'true'

# Parallel Processing Configuration
PARALLEL_CONFIG = {
    'MAX_WORKERS': int(os.getenv('FACE_AI_MAX_WORKERS', 4)),
    'BATCH_SIZE': int(os.getenv('FACE_AI_BATCH_SIZE', 10)),
    'THREAD_POOL_SIZE': int(os.getenv('FACE_AI_THREAD_POOL_SIZE', 8)),
    'PROCESS_POOL_SIZE': int(os.getenv('FACE_AI_PROCESS_POOL_SIZE', 2)),
    'ENABLE_GPU': os.getenv('FACE_AI_ENABLE_GPU', 'false').lower() == 'true',
    'GPU_MEMORY_LIMIT': os.getenv('FACE_AI_GPU_MEMORY_LIMIT', '4GB'),
}

# Face Detection Model Configuration
FACE_MODEL_CONFIG = {
    'MODEL_NAME': os.getenv('FACE_AI_MODEL_NAME', 'buffalo_l'),
    'PROVIDERS': os.getenv('FACE_AI_PROVIDERS', 'CPUExecutionProvider').split(','),
    'DETECTION_SIZE': tuple(map(int, os.getenv('FACE_AI_DETECTION_SIZE', '640,640').split(','))),
    'MIN_FACE_SIZE': int(os.getenv('FACE_AI_MIN_FACE_SIZE', 20)),
    'CONFIDENCE_THRESHOLD': float(os.getenv('FACE_AI_CONFIDENCE_THRESHOLD', 0.5)),
    'EMBEDDING_DIM': int(os.getenv('FACE_AI_EMBEDDING_DIM', 512)),
}

# Milvus Vector Database Configuration
MILVUS_CONFIG = {
    'HOST': os.getenv('MILVUS_HOST', 'localhost'),
    'PORT': int(os.getenv('MILVUS_PORT', 19530)),
    'CONNECTION_ALIAS': os.getenv('MILVUS_CONNECTION_ALIAS', 'default'),
    'COLLECTION_NAME': os.getenv('MILVUS_COLLECTION_NAME', 'watchlist'),
    'DIMENSION': int(os.getenv('MILVUS_DIMENSION', 512)),
    'METRIC_TYPE': os.getenv('MILVUS_METRIC_TYPE', 'COSINE'),
    'INDEX_TYPE': os.getenv('MILVUS_INDEX_TYPE', 'IVF_FLAT'),
    'INDEX_PARAMS': {
        'nlist': int(os.getenv('MILVUS_INDEX_NLIST', 1024))
    },
    'SEARCH_PARAMS': {
        'nprobe': int(os.getenv('MILVUS_SEARCH_NPROBE', 10))
    },
    'AUTO_CREATE_COLLECTION': os.getenv('MILVUS_AUTO_CREATE_COLLECTION', 'true').lower() == 'true',
    'AUTO_LOAD_COLLECTION': os.getenv('MILVUS_AUTO_LOAD_COLLECTION', 'true').lower() == 'true',
}

# Performance Monitoring Configuration
PERFORMANCE_CONFIG = {
    'ENABLE_MONITORING': os.getenv('FACE_AI_ENABLE_MONITORING', 'true').lower() == 'true',
    'LOG_PERFORMANCE': os.getenv('FACE_AI_LOG_PERFORMANCE', 'true').lower() == 'true',
    'METRICS_INTERVAL': int(os.getenv('FACE_AI_METRICS_INTERVAL', 60)),  # seconds
    'MAX_MEMORY_USAGE': os.getenv('FACE_AI_MAX_MEMORY_USAGE', '8GB'),
    'ENABLE_PROFILING': os.getenv('FACE_AI_ENABLE_PROFILING', 'false').lower() == 'true',
}

# Caching Configuration
CACHE_CONFIG = {
    'ENABLE_CACHING': os.getenv('FACE_AI_ENABLE_CACHING', 'true').lower() == 'true',
    'CACHE_TTL': int(os.getenv('FACE_AI_CACHE_TTL', 3600)),  # seconds
    'CACHE_MAX_SIZE': int(os.getenv('FACE_AI_CACHE_MAX_SIZE', 1000)),
    'CACHE_BACKEND': os.getenv('FACE_AI_CACHE_BACKEND', 'memory'),  # memory, redis, memcached
}

# Logging Configuration
LOGGING_CONFIG = {
    'LEVEL': os.getenv('FACE_AI_LOG_LEVEL', 'INFO'),
    'FORMAT': os.getenv('FACE_AI_LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    'FILE': os.getenv('FACE_AI_LOG_FILE', 'face_ai.log'),
    'MAX_SIZE': os.getenv('FACE_AI_LOG_MAX_SIZE', '10MB'),
    'BACKUP_COUNT': int(os.getenv('FACE_AI_LOG_BACKUP_COUNT', 5)),
}

# Security Configuration
SECURITY_CONFIG = {
    'ENABLE_AUTH': os.getenv('FACE_AI_ENABLE_AUTH', 'true').lower() == 'true',
    'API_KEY_HEADER': os.getenv('FACE_AI_API_KEY_HEADER', 'X-API-Key'),
    'RATE_LIMIT': int(os.getenv('FACE_AI_RATE_LIMIT', 100)),  # requests per minute
    'MAX_FILE_SIZE': os.getenv('FACE_AI_MAX_FILE_SIZE', '10MB'),
    'ALLOWED_EXTENSIONS': os.getenv('FACE_AI_ALLOWED_EXTENSIONS', 'jpg,jpeg,png,bmp').split(','),
}

# Development Configuration
DEV_CONFIG = {
    'DEBUG': os.getenv('FACE_AI_DEBUG', 'false').lower() == 'true',
    'ENABLE_HOT_RELOAD': os.getenv('FACE_AI_HOT_RELOAD', 'true').lower() == 'true',
    'ENABLE_TESTING': os.getenv('FACE_AI_ENABLE_TESTING', 'false').lower() == 'true',
    'MOCK_SERVICES': os.getenv('FACE_AI_MOCK_SERVICES', 'false').lower() == 'true',
}

def get_config() -> Dict[str, Any]:
    """Get complete configuration dictionary"""
    return {
        'ASGI_APP': {
            'NAME': ASGI_APP_NAME,
            'HOST': ASGI_APP_HOST,
            'PORT': ASGI_APP_PORT,
            'RELOAD': ASGI_APP_RELOAD,
        },
        'PARALLEL': PARALLEL_CONFIG,
        'FACE_MODEL': FACE_MODEL_CONFIG,
        'MILVUS': MILVUS_CONFIG,
        'PERFORMANCE': PERFORMANCE_CONFIG,
        'CACHE': CACHE_CONFIG,
        'LOGGING': LOGGING_CONFIG,
        'SECURITY': SECURITY_CONFIG,
        'DEV': DEV_CONFIG,
    }

def get_parallel_config() -> Dict[str, Any]:
    """Get parallel processing configuration"""
    return PARALLEL_CONFIG

def get_face_model_config() -> Dict[str, Any]:
    """Get face detection model configuration"""
    return FACE_MODEL_CONFIG

def get_milvus_config() -> Dict[str, Any]:
    """Get Milvus configuration"""
    return MILVUS_CONFIG

def get_performance_config() -> Dict[str, Any]:
    """Get performance monitoring configuration"""
    return PERFORMANCE_CONFIG

def get_cache_config() -> Dict[str, Any]:
    """Get caching configuration"""
    return CACHE_CONFIG

def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration"""
    return LOGGING_CONFIG

def get_security_config() -> Dict[str, Any]:
    """Get security configuration"""
    return SECURITY_CONFIG

def get_dev_config() -> Dict[str, Any]:
    """Get development configuration"""
    return DEV_CONFIG

# Environment-specific configurations
def get_production_config() -> Dict[str, Any]:
    """Get production configuration"""
    config = get_config()
    config['DEV']['DEBUG'] = False
    config['DEV']['ENABLE_HOT_RELOAD'] = False
    config['DEV']['ENABLE_TESTING'] = False
    config['DEV']['MOCK_SERVICES'] = False
    config['PERFORMANCE']['ENABLE_PROFILING'] = False
    return config

def get_development_config() -> Dict[str, Any]:
    """Get development configuration"""
    config = get_config()
    config['DEV']['DEBUG'] = True
    config['DEV']['ENABLE_HOT_RELOAD'] = True
    config['DEV']['ENABLE_TESTING'] = True
    config['DEV']['MOCK_SERVICES'] = True
    config['PERFORMANCE']['ENABLE_PROFILING'] = True
    return config

def get_testing_config() -> Dict[str, Any]:
    """Get testing configuration"""
    config = get_config()
    config['DEV']['DEBUG'] = True
    config['DEV']['ENABLE_HOT_RELOAD'] = False
    config['DEV']['ENABLE_TESTING'] = True
    config['DEV']['MOCK_SERVICES'] = True
    config['PERFORMANCE']['ENABLE_PROFILING'] = False
    config['CACHE']['ENABLE_CACHING'] = False
    return config
