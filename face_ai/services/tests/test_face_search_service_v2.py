"""
Comprehensive Test Suite for Face Search Service V2

Tests the redesigned face search service with proper mocking and edge case coverage.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO
from PIL import Image

from face_ai.services.face_search_service_v2 import FaceSearchService
from face_ai.services.vector_search.interfaces import SearchResponse, SearchResult, SearchStatus


class TestFaceSearchServiceV2:
    """Test suite for FaceSearchServiceV2"""
    
    @pytest.fixture
    async def service(self):
        """Create a test service instance"""
        with patch('face_ai.services.face_search_service_v2.FaceDetectionService') as mock_detection, \
             patch('face_ai.services.face_search_service_v2.FaceEmbeddingService') as mock_embedding, \
             patch('face_ai.services.face_search_service_v2.VectorSearchService') as mock_vector, \
             patch('face_ai.services.face_search_service_v2.ReRanker') as mock_reranker:
            
            # Mock the services
            mock_detection.return_value = Mock()
            mock_embedding.return_value = Mock()
            mock_vector.return_value = Mock()
            mock_reranker.return_value = Mock()
            
            service = FaceSearchService()
            yield service
            await service.close()
    
    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing"""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Create a mock file object
        mock_file = Mock()
        mock_file.chunks.return_value = [img_bytes.getvalue()]
        mock_file.name = 'test_image.jpg'
        mock_file.size = len(img_bytes.getvalue())
        
        return mock_file
    
    @pytest.fixture
    def sample_embedding(self):
        """Create a sample face embedding"""
        return np.random.rand(512).astype(np.float32)
    
    @pytest.mark.asyncio
    async def test_search_faces_in_image_success(self, service, sample_image_file):
        """Test successful face search in image"""
        # Mock face detection
        service.face_detection.detect_faces_in_image.return_value = {
            'success': True,
            'faces_detected': 1,
            'faces': [{
                'bbox': [10, 10, 50, 50],
                'confidence': 0.9
            }]
        }
        
        # Mock embedding generation
        service.face_embedding.generate_embedding_from_image.return_value = np.random.rand(512)
        
        # Mock vector search
        mock_search_response = SearchResponse(
            results=[
                SearchResult(
                    id="test_id",
                    score=0.8,
                    distance=0.2,
                    metadata={'target_id': 'target_1', 'photo_id': 'photo_1'}
                )
            ],
            total_found=1,
            search_time_ms=150.0,
            status=SearchStatus.COMPLETED
        )
        service.vector_search.search.return_value = mock_search_response
        
        # Mock target info
        service._get_target_info = AsyncMock(return_value={
            'name': 'Test Target',
            'category': 'Test',
            'status': 'Active'
        })
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.search_faces_in_image(sample_image_file)
        
        assert result['success'] is True
        assert result['total_faces_detected'] == 1
        assert len(result['search_results']) == 1
        assert result['search_results'][0]['total_similar'] == 1
        assert 'request_id' in result
    
    @pytest.mark.asyncio
    async def test_search_faces_in_image_no_faces(self, service, sample_image_file):
        """Test face search when no faces are detected"""
        # Mock face detection with no faces
        service.face_detection.detect_faces_in_image.return_value = {
            'success': True,
            'faces_detected': 0,
            'faces': []
        }
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.search_faces_in_image(sample_image_file)
        
        assert result['success'] is False
        assert 'No faces detected' in result['error']
        assert result['total_similar_faces'] == 0
    
    @pytest.mark.asyncio
    async def test_search_faces_in_image_detection_failure(self, service, sample_image_file):
        """Test face search when face detection fails"""
        # Mock face detection failure
        service.face_detection.detect_faces_in_image.return_value = {
            'success': False,
            'error': 'Detection failed',
            'faces_detected': 0,
            'faces': []
        }
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.search_faces_in_image(sample_image_file)
        
        assert result['success'] is False
        assert 'Detection failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_search_faces_by_embedding_success(self, service, sample_embedding):
        """Test successful face search by embedding"""
        # Mock vector search
        mock_search_response = SearchResponse(
            results=[
                SearchResult(
                    id="test_id",
                    score=0.8,
                    distance=0.2,
                    metadata={'target_id': 'target_1', 'photo_id': 'photo_1'}
                )
            ],
            total_found=1,
            search_time_ms=150.0,
            status=SearchStatus.COMPLETED
        )
        service.vector_search.search.return_value = mock_search_response
        
        # Mock target info
        service._get_target_info = AsyncMock(return_value={
            'name': 'Test Target',
            'category': 'Test',
            'status': 'Active'
        })
        
        result = await service.search_faces_by_embedding(sample_embedding)
        
        assert result['success'] is True
        assert result['total_similar_faces'] == 1
        assert len(result['search_results']) == 1
        assert 'request_id' in result
    
    @pytest.mark.asyncio
    async def test_search_faces_by_embedding_none_input(self, service):
        """Test face search by embedding with None input"""
        result = await service.search_faces_by_embedding(None)
        
        assert result['success'] is False
        assert 'No face embedding provided' in result['error']
    
    @pytest.mark.asyncio
    async def test_verify_faces_success(self, service, sample_image_file):
        """Test successful face verification"""
        # Mock face detection for both images
        service.face_detection.detect_faces_in_image.return_value = {
            'success': True,
            'faces_detected': 1,
            'faces': [{
                'bbox': [10, 10, 50, 50],
                'confidence': 0.9
            }]
        }
        
        # Mock embedding generation
        service.face_embedding.generate_embedding_from_image.return_value = np.random.rand(512)
        
        # Mock face verification
        service.face_embedding.verify_faces_with_embeddings.return_value = {
            'is_same_person': True,
            'similarity_score': 0.85
        }
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.verify_faces(sample_image_file, sample_image_file)
        
        assert result['success'] is True
        assert result['verification_result']['is_same_person'] is True
        assert result['verification_result']['similarity_score'] == 0.85
        assert 'request_id' in result
    
    @pytest.mark.asyncio
    async def test_verify_faces_no_faces_detected(self, service, sample_image_file):
        """Test face verification when no faces are detected"""
        # Mock face detection with no faces
        service.face_detection.detect_faces_in_image.return_value = {
            'success': True,
            'faces_detected': 0,
            'faces': []
        }
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.verify_faces(sample_image_file, sample_image_file)
        
        assert result['success'] is False
        assert 'No faces detected' in result['error']
    
    @pytest.mark.asyncio
    async def test_get_service_info_success(self, service):
        """Test getting service information"""
        # Mock component info
        service.face_detection.get_model_info.return_value = {
            'model_name': 'Yunet',
            'version': '1.0'
        }
        
        service.face_embedding.get_model_info.return_value = {
            'model_name': 'Facenet',
            'version': '1.0'
        }
        
        # Mock vector search info
        from face_ai.services.vector_search.interfaces import CollectionInfo, HealthStatus, MetricType, IndexType
        from datetime import datetime
        
        mock_collection_info = CollectionInfo(
            name="test_collection",
            dimension=512,
            total_vectors=1000,
            metric_type=MetricType.COSINE,
            index_type=IndexType.IVF_FLAT,
            is_loaded=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_health_status = HealthStatus(
            is_healthy=True,
            status="healthy",
            last_check=1234567890,
            connection_status="connected",
            collection_status="healthy",
            performance_metrics={}
        )
        
        service.vector_search.get_collection_info.return_value = mock_collection_info
        service.vector_search.health_check.return_value = mock_health_status
        
        info = await service.get_service_info()
        
        assert info['service_name'] == 'FaceSearchService'
        assert info['version'] == '2.0.0'
        assert info['status'] == 'operational'
        assert 'detection_model' in info
        assert 'embedding_model' in info
        assert 'vector_database' in info
        assert 'health_status' in info
    
    @pytest.mark.asyncio
    async def test_get_service_info_error(self, service):
        """Test getting service information when there's an error"""
        # Mock error in getting collection info
        service.vector_search.get_collection_info.side_effect = Exception("Connection failed")
        
        info = await service.get_service_info()
        
        assert info['service_name'] == 'FaceSearchService'
        assert info['version'] == '2.0.0'
        assert info['status'] == 'error'
        assert 'Connection failed' in info['error']
    
    @pytest.mark.asyncio
    async def test_input_validation(self, service):
        """Test input validation"""
        # Test None image file
        with pytest.raises(Exception):  # Should raise ValidationError
            await service.search_faces_in_image(None)
        
        # Test invalid top_k
        mock_file = Mock()
        mock_file.chunks.return_value = [b'test']
        
        with patch('tempfile.NamedTemporaryFile'):
            with pytest.raises(Exception):  # Should raise ValidationError
                await service.search_faces_in_image(mock_file, top_k=0)
        
        # Test invalid confidence threshold
        with patch('tempfile.NamedTemporaryFile'):
            with pytest.raises(Exception):  # Should raise ValidationError
                await service.search_faces_in_image(mock_file, confidence_threshold=1.5)
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        with patch('face_ai.services.face_search_service_v2.FaceDetectionService'), \
             patch('face_ai.services.face_search_service_v2.FaceEmbeddingService'), \
             patch('face_ai.services.face_search_service_v2.VectorSearchService'), \
             patch('face_ai.services.face_search_service_v2.ReRanker'):
            
            async with FaceSearchService() as service:
                assert isinstance(service, FaceSearchService)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_search(self, service, sample_image_file):
        """Test error handling in search operations"""
        # Mock face detection success but embedding generation failure
        service.face_detection.detect_faces_in_image.return_value = {
            'success': True,
            'faces_detected': 1,
            'faces': [{
                'bbox': [10, 10, 50, 50],
                'confidence': 0.9
            }]
        }
        
        service.face_embedding.generate_embedding_from_image.return_value = None
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.search_faces_in_image(sample_image_file)
        
        # Should still succeed but with no results for this face
        assert result['success'] is True
        assert result['total_faces_detected'] == 1
        assert len(result['search_results']) == 0  # No results due to embedding failure
    
    @pytest.mark.asyncio
    async def test_multiple_faces_processing(self, service, sample_image_file):
        """Test processing multiple faces in an image"""
        # Mock face detection with multiple faces
        service.face_detection.detect_faces_in_image.return_value = {
            'success': True,
            'faces_detected': 2,
            'faces': [
                {
                    'bbox': [10, 10, 50, 50],
                    'confidence': 0.9
                },
                {
                    'bbox': [60, 60, 100, 100],
                    'confidence': 0.8
                }
            ]
        }
        
        # Mock embedding generation
        service.face_embedding.generate_embedding_from_image.return_value = np.random.rand(512)
        
        # Mock vector search
        mock_search_response = SearchResponse(
            results=[
                SearchResult(
                    id="test_id",
                    score=0.8,
                    distance=0.2,
                    metadata={'target_id': 'target_1', 'photo_id': 'photo_1'}
                )
            ],
            total_found=1,
            search_time_ms=150.0,
            status=SearchStatus.COMPLETED
        )
        service.vector_search.search.return_value = mock_search_response
        
        # Mock target info
        service._get_target_info = AsyncMock(return_value={
            'name': 'Test Target',
            'category': 'Test',
            'status': 'Active'
        })
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = Mock()
            mock_temp_file.name = '/tmp/test.jpg'
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            
            with patch('os.unlink'):
                result = await service.search_faces_in_image(sample_image_file)
        
        assert result['success'] is True
        assert result['total_faces_detected'] == 2
        assert len(result['search_results']) == 2  # One result per face
        assert len(result['query_faces']) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


