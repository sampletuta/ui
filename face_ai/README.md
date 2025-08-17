# Face AI Recognition App

A lightweight Django app for face detection, embedding generation, and verification using InsightFace, with vector storage in Milvus.

## 🎯 Purpose

This app provides **three core face recognition capabilities** without storing any data in Django models:

1. **🔍 Face Detection** - Check if images contain faces
2. **📊 Face Embedding** - Generate 512-dimensional face vectors
3. **✅ Face Verification** - Compare two faces with age/gender estimation

**Plus automatic integration** with your existing target creation process!

## ✨ Key Features

- 🔍 **Face Detection**: Using InsightFace for accurate face detection
- 📊 **Embedding Generation**: 512-dimensional face embeddings
- ✅ **Face Verification**: Compare faces with similarity scoring
- 👥 **Age & Gender**: Automatic age and gender estimation
- 💾 **Vector Storage**: Milvus vector database for similarity search
- 🚫 **No Database Models**: Pure processing service, no Django storage
- 🔗 **Clean API**: Simple REST endpoints for all operations
- 🔄 **Automatic Integration**: Photos processed automatically when targets are created

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Ensure Milvus is Running
```bash
# Milvus should be running on localhost:9000
```

### 3. Use the APIs

#### API 1: Face Detection
```bash
curl -X POST http://localhost:8000/face-ai/api/face/detect/ \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/path/to/image.jpg"
  }'
```

#### API 2: Face Embedding Generation
```bash
curl -X POST http://localhost:8000/face-ai/api/face/embedding/ \
  -H "Content-Type: application/json" \
  -d '{
    "image_paths": [
      "/path/to/image1.jpg",
      "/path/to/image2.jpg"
    ]
  }'
```

#### API 3: Face Verification
```bash
curl -X POST http://localhost:8000/face-ai/api/face/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "image1_base64": "base64_encoded_image_1",
    "image2_base64": "base64_encoded_image_2",
    "confidence_threshold": 70.0
  }'
```

## 🔄 **Automatic Target Integration**

### **What Happens Automatically:**

When you create, update, or delete watchlist photos:

1. **Photo Upload** → TargetPhoto object created → **Face AI processes automatically**
2. **Photo Update** → Photo modified → **Face AI recomputes all embeddings for target**
3. **Photo Deletion** → Photo removed → **Face AI removes embeddings from Milvus**
4. **Multiple Photos** → All photos processed → **Normalized embeddings stored**

### **Complete Automation Flow:**

```
📸 Photo Added → 🔍 Face Detection → 📊 Embedding Generation → 💾 Milvus Storage
📝 Photo Updated → 🔄 Recompute All → 📊 Normalized Embeddings → 💾 Milvus Update  
🗑️ Photo Deleted → 🧹 Cleanup → 🗑️ Remove Embeddings → 💾 Milvus Cleanup
```

### **Integration Points:**

- **Target Creation**: `add_target_to_case` view automatically processes photos
- **Django Signals**: Photos processed even if created programmatically
- **Photo Updates**: Automatically recomputes all embeddings for normalization
- **Photo Deletions**: Automatically removes corresponding embeddings from Milvus
- **Management Commands**: Process existing photos retroactively

### **Example Workflow:**

```python
# In your existing target creation form
# When photos are uploaded, this happens automatically:

# 1. TargetPhoto objects are created
# 2. Face AI service processes each photo
# 3. Face embeddings are stored in Milvus with photo_id tracking
# 4. Success messages show processing results

# When photos are updated:
# 1. All photos for the target are reprocessed
# 2. Normalized embeddings are computed across all photos
# 3. Updated embeddings are stored in Milvus

# When photos are deleted:
# 1. Corresponding embeddings are automatically removed from Milvus
# 2. No orphaned data left behind

# No changes needed to your existing code!
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/face-ai/api/face/detect/` | **API 1**: Detect faces in image |
| `POST` | `/face-ai/api/face/embedding/` | **API 2**: Generate face embeddings |
| `POST` | `/face-ai/api/face/verify/` | **API 3**: Verify faces with age/gender |
| `GET` | `/face-ai/api/face/milvus/status/` | Check Milvus status |
| `DELETE` | `/face-ai/api/face/delete/` | Delete embeddings |

## 🔧 API Details

### API 1: Face Detection
**Purpose**: Check if an image contains faces

**Input**:
```json
{
  "image_path": "/path/to/image.jpg"
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "faces_detected": 2,
    "faces": [
      {
        "bbox": [100, 150, 200, 250],
        "confidence": 0.95,
        "age": 25,
        "gender": "male"
      }
    ],
    "message": "Found 2 face(s)"
  }
}
```

### API 2: Face Embedding Generation
**Purpose**: Generate embeddings for multiple images (all must have faces)

**Input**:
```json
{
  "image_paths": [
    "/path/to/image1.jpg",
    "/path/to/image2.jpg"
  ]
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "total_embeddings": 3,
    "embeddings": [
      {
        "image_path": "/path/to/image1.jpg",
        "embedding": [0.1, 0.2, 0.3, ...],
        "confidence_score": 0.95,
        "bbox": [100, 150, 200, 250],
        "age": 25,
        "gender": "male"
      }
    ],
    "failed_images": []
  }
}
```

### API 3: Face Verification
**Purpose**: Compare two faces with age/gender estimation

**Input**:
```json
{
  "image1_base64": "base64_encoded_image_1",
  "image2_base64": "base64_encoded_image_2",
  "confidence_threshold": 70.0
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "faces_match": true,
    "similarity_score": 85.67,
    "confidence_threshold": 70.0,
    "threshold_met": true,
    "face1": {
      "age": 25,
      "gender": "male",
      "confidence": 0.95
    },
    "face2": {
      "age": 26,
      "gender": "male",
      "confidence": 0.92
    },
    "message": "Faces match with 85.67% similarity"
  }
}
```

## 🔌 Integration

### With Your Existing Models
- **Targets_watchlist**: Provides target IDs for face processing
- **TargetPhoto**: Images are processed but not stored by this app
- **No New Models**: This app creates zero database tables

### Example Integration
```python
# In your existing view
from face_ai.services.face_detection import FaceDetectionService

def process_target_image(request, target_id):
    service = FaceDetectionService()
    
    # API 1: Check if image has faces
    detection_result = service.detect_faces_in_image("/path/to/image.jpg")
    
    if detection_result['faces_detected'] > 0:
        # API 2: Generate embeddings
        embedding_result = service.generate_face_embeddings(["/path/to/image.jpg"])
        
        if embedding_result['success']:
            # Store embeddings in Milvus
            # No Django models created
            return JsonResponse(embedding_result)
```

## 🛠️ Management Commands

### Process Existing Photos
```bash
# Process all existing photos
python3 manage.py process_existing_photos

# Process photos for specific target
python3 manage.py process_existing_photos --target-id "uuid-here"

# Dry run to see what would be processed
python3 manage.py process_existing_photos --dry-run
```

## ⚙️ Configuration

### **All Configuration in Django Settings**
All Milvus configuration is now centralized in your `backend/settings.py` file:

```python
MILVUS_CONFIG = {
    'HOST': 'localhost',           # Milvus server hostname
    'PORT': 9000,                  # Milvus server port (your requirement)
    'COLLECTION_NAME': 'face_embeddings',
    'DIMENSION': 512,              # Face embedding dimension
    'METRIC_TYPE': 'COSINE',       # Similarity metric
    'INDEX_TYPE': 'IVF_FLAT',      # Index type
    'AUTO_CREATE_COLLECTION': True, # Auto-create if missing
    'AUTO_LOAD_COLLECTION': True,   # Auto-load for operations
}
```

### **Environment Variables**
Override any setting using environment variables:
```bash
export MILVUS_HOST=your-server.com
export MILVUS_PORT=19530
export MILVUS_COLLECTION_NAME=my_collection
```

### **Milvus Connection**
- **Host**: `localhost` (default, configurable)
- **Port**: `9000` (default, configurable)
- **Collection**: `face_embeddings` (configurable)
- **Dimension**: 512 (configurable)
- **Providers**: CPU (configurable for GPU)
- **Features**: Face detection, embedding, age, gender

📖 **See `face_ai/CONFIGURATION.md` for complete configuration guide**

## 📊 Performance

- **Face Detection**: 1-2 seconds per image
- **Embedding Generation**: 0.5-1 second per face
- **Face Verification**: 1-2 seconds for comparison
- **Age/Gender Estimation**: Included in detection time
- **Milvus Search**: <100ms for similarity queries
- **Automatic Processing**: Background processing with user feedback

## 🚨 Important Notes

1. **Authentication Required**: All endpoints need user login
2. **CSRF Protection**: POST/DELETE requests need CSRF tokens
3. **Image Paths**: Must be full file system paths for APIs 1 & 2
4. **Base64 Images**: Required for API 3 (face verification)
5. **Face Requirement**: API 2 requires all images to have faces
6. **Confidence Threshold**: API 3 uses 0-100 scale (default 50)
7. **Automatic Processing**: Photos processed automatically when targets created
8. **Milvus Required**: Must be running on localhost:9000

## 🐛 Troubleshooting

### Common Issues
- **Milvus Connection Failed**: Check if Milvus is running on port 9000
- **Image Not Found**: Verify image path is correct and accessible
- **Face Detection Failed**: Ensure image contains detectable faces
- **Base64 Error**: Check if base64 string is valid for API 3
- **Auto-processing Failed**: Check Django logs for signal errors

### Logs
Check Django logs for detailed error information. The app logs all major operations.

## 📚 Dependencies

- `insightface>=0.7.3` - Face detection, embedding, age, gender
- `pymilvus>=2.3.0` - Milvus vector database client
- `opencv-python>=4.8.0` - Image processing
- `numpy>=1.24.0` - Numerical operations
- `Pillow>=10.0.0` - Image handling

## 🎉 Ready to Use!

The app now provides three focused APIs for face recognition **plus automatic integration**:

1. **Detect faces** in images
2. **Generate embeddings** for faces  
3. **Verify faces** with age/gender estimation
4. **Automatic processing** when targets are created

**No changes needed to your existing target creation workflow!** 🎯
