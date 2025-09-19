# Add these settings to your Django settings.py file

# Milvus Configuration for the new Vector Search Service
MILVUS_CONFIG = {
    'HOST': 'localhost',
    'PORT': 19530,
    'USER': None,  # Set if Milvus requires authentication
    'PASSWORD': None,  # Set if Milvus requires authentication
    'DATABASE': 'default',
    'CONNECTION_ALIAS': 'default',
    'TIMEOUT': 30.0,
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1.0
}

# Collection Configuration
COLLECTION_CONFIG = {
    'NAME': 'face_embeddings',
    'DIMENSION': 512,  # Must match your face embedding dimension
    'METRIC_TYPE': 'COSINE',  # COSINE, EUCLIDEAN, or IP
    'INDEX_TYPE': 'IVF_FLAT',  # IVF_FLAT, IVF_SQ8, IVF_PQ, HNSW, ANNOY
    'INDEX_PARAMS': {'nlist': 1024},  # Adjust based on your data size
    'SEARCH_PARAMS': {'nprobe': 10},  # Adjust for accuracy vs speed
    'AUTO_CREATE': True,
    'AUTO_LOAD': True,
    'MAX_CAPACITY': 1000000
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    'CONNECTION_POOL_SIZE': 10,
    'MAX_CONNECTIONS': 100,
    'BATCH_SIZE': 1000,
    'SEARCH_TIMEOUT': 30.0,
    'INSERT_TIMEOUT': 60.0,
    'ENABLE_CACHING': True,
    'CACHE_TTL': 3600,  # Cache results for 1 hour
    'CACHE_MAX_SIZE': 10000
}

# Monitoring Configuration
MONITORING_CONFIG = {
    'ENABLE_METRICS': True,
    'ENABLE_TRACING': False,
    'LOG_LEVEL': 'INFO',
    'LOG_REQUESTS': True,
    'LOG_RESPONSES': False,
    'METRICS_INTERVAL': 60,  # seconds
    'HEALTH_CHECK_INTERVAL': 300  # seconds
}
