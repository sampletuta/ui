# 🔧 Face AI Configuration Guide

## **Milvus Configuration in Django Settings**

All Milvus configuration is now centralized in your Django `settings.py` file for easy management and deployment.

## 📋 **Configuration Options**

### **Basic Connection Settings**
```python
MILVUS_CONFIG = {
    'HOST': 'localhost',           # Milvus server hostname
    'PORT': 9000,                  # Milvus server port
    'CONNECTION_ALIAS': 'default', # Connection alias for multiple instances
}
```

### **Collection Settings**
```python
MILVUS_CONFIG = {
    'COLLECTION_NAME': 'face_embeddings',     # Name of the face embeddings collection
    'COLLECTION_PREFIX': 'surveillance_',     # Prefix for collection names
    'DIMENSION': 512,                         # Face embedding vector dimension
}
```

### **Index Settings**
```python
MILVUS_CONFIG = {
    'METRIC_TYPE': 'COSINE',                  # Similarity metric (COSINE, L2, IP)
    'INDEX_TYPE': 'IVF_FLAT',                # Index type for vector search
    'INDEX_PARAMS': {
        'nlist': 1024                        # Number of clusters for IVF index
    },
}
```

### **Search Settings**
```python
MILVUS_CONFIG = {
    'SEARCH_PARAMS': {
        'nprobe': 10                         # Number of clusters to search
    },
}
```

### **Automation Settings**
```python
MILVUS_CONFIG = {
    'AUTO_CREATE_COLLECTION': True,          # Auto-create collection if missing
    'AUTO_LOAD_COLLECTION': True,            # Auto-load collection for operations
}
```

## 🌍 **Environment Variables**

You can override any setting using environment variables:

```bash
# Connection
export MILVUS_HOST=your-milvus-server.com
export MILVUS_PORT=19530

# Collection
export MILVUS_COLLECTION_NAME=my_face_collection
export MILVUS_DIMENSION=512

# Index
export MILVUS_METRIC_TYPE=COSINE
export MILVUS_INDEX_TYPE=IVF_FLAT
export MILVUS_INDEX_NLIST=2048

# Search
export MILVUS_SEARCH_NPROBE=20

# Automation
export MILVUS_AUTO_CREATE_COLLECTION=True
export MILVUS_AUTO_LOAD_COLLECTION=True
```

## 📁 **Complete Configuration Example**

```python
# In your settings.py
MILVUS_CONFIG = {
    'HOST': os.environ.get('MILVUS_HOST', 'localhost'),
    'PORT': int(os.environ.get('MILVUS_PORT', '9000')),
    'COLLECTION_NAME': os.environ.get('MILVUS_COLLECTION_NAME', 'face_embeddings'),
    'COLLECTION_PREFIX': os.environ.get('MILVUS_COLLECTION_PREFIX', 'surveillance_'),
    'DIMENSION': int(os.environ.get('MILVUS_DIMENSION', '512')),
    'METRIC_TYPE': os.environ.get('MILVUS_METRIC_TYPE', 'COSINE'),
    'INDEX_TYPE': os.environ.get('MILVUS_INDEX_TYPE', 'IVF_FLAT'),
    'INDEX_PARAMS': {
        'nlist': int(os.environ.get('MILVUS_INDEX_NLIST', '1024'))
    },
    'SEARCH_PARAMS': {
        'nprobe': int(os.environ.get('MILVUS_SEARCH_NPROBE', '10'))
    },
    'CONNECTION_ALIAS': os.environ.get('MILVUS_CONNECTION_ALIAS', 'default'),
    'AUTO_CREATE_COLLECTION': os.environ.get('MILVUS_AUTO_CREATE', 'True').lower() == 'true',
    'AUTO_LOAD_COLLECTION': os.environ.get('MILVUS_AUTO_LOAD', 'True').lower() == 'true',
}
```

## 🚀 **Recommended Settings**

### **Development Environment**
```python
MILVUS_CONFIG = {
    'HOST': 'localhost',
    'PORT': 9000,
    'COLLECTION_NAME': 'face_embeddings_dev',
    'DIMENSION': 512,
    'METRIC_TYPE': 'COSINE',
    'INDEX_TYPE': 'IVF_FLAT',
    'INDEX_PARAMS': {'nlist': 1024},
    'SEARCH_PARAMS': {'nprobe': 10},
    'AUTO_CREATE_COLLECTION': True,
    'AUTO_LOAD_COLLECTION': True,
}
```

### **Production Environment**
```python
MILVUS_CONFIG = {
    'HOST': 'your-milvus-cluster.com',
    'PORT': 19530,
    'COLLECTION_NAME': 'face_embeddings_prod',
    'DIMENSION': 512,
    'METRIC_TYPE': 'COSINE',
    'INDEX_TYPE': 'IVF_SQ8',  # Better compression for production
    'INDEX_PARAMS': {'nlist': 2048},  # More clusters for better performance
    'SEARCH_PARAMS': {'nprobe': 20},  # More thorough search
    'AUTO_CREATE_COLLECTION': False,  # Manual control in production
    'AUTO_LOAD_COLLECTION': False,    # Manual control in production
}
```

## 🔍 **Metric Types Explained**

### **COSINE (Recommended for Face Recognition)**
- **Use Case**: Face similarity, text similarity
- **Range**: -1 to 1 (1 = identical, 0 = orthogonal, -1 = opposite)
- **Threshold**: Use 0.6-0.8 for face matching

### **L2 (Euclidean Distance)**
- **Use Case**: General vector similarity
- **Range**: 0 to ∞ (0 = identical, larger = more different)
- **Threshold**: Use 0.1-0.3 for face matching

### **IP (Inner Product)**
- **Use Case**: Neural network outputs
- **Range**: -∞ to ∞
- **Threshold**: Depends on your data

## 📊 **Index Types Explained**

### **IVF_FLAT (Recommended)**
- **Pros**: Good balance of speed and accuracy
- **Cons**: Larger memory usage
- **Best for**: Development and small to medium datasets

### **IVF_SQ8**
- **Pros**: Better memory efficiency, good speed
- **Cons**: Slight accuracy loss
- **Best for**: Production with large datasets

### **HNSW**
- **Pros**: Very fast search
- **Cons**: Slower build time, larger memory
- **Best for**: High-performance requirements

## 🧪 **Testing Configuration**

### **Check Current Configuration**
```python
from face_ai.services.milvus_service import MilvusService

service = MilvusService()
stats = service.get_collection_stats()
print(f"Collection: {stats['collection_name']}")
print(f"Dimension: {stats['dimension']}")
print(f"Metric Type: {stats['metric_type']}")
print(f"Index Type: {stats['index_type']}")
```

### **Test Connection**
```bash
# Test Milvus connection
python3 manage.py shell
>>> from face_ai.services.milvus_service import MilvusService
>>> service = MilvusService()
>>> stats = service.get_collection_stats()
>>> print("Connection successful!")
```

## 🚨 **Important Notes**

1. **Port 9000**: Default for Milvus standalone
2. **Port 19530**: Default for Milvus cluster
3. **COSINE Metric**: Best for face similarity (higher = more similar)
4. **Auto-create**: Automatically creates collections if missing
5. **Auto-load**: Automatically loads collections for operations
6. **Environment Variables**: Override any setting for deployment flexibility

## 🎯 **Quick Start**

1. **Set environment variables** (or use defaults)
2. **Start Milvus** on your configured host/port
3. **Create target with photos** - Face AI processes automatically
4. **Check logs** for processing results

Your face AI system will now use all these centralized settings! 🚀
