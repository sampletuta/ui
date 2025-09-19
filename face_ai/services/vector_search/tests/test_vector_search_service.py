"""
Comprehensive Test Suite for Vector Search Service

Tests all components with proper mocking and edge case coverage.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from .core import VectorSearchService
from .interfaces import (
    SearchRequest, SearchResponse, SearchResult, SearchStatus,
    MetricType, IndexType, CollectionInfo, HealthStatus
)
from .exceptions import (
    VectorSearchError, ConnectionError, SearchError, ValidationError
)
from .config import config_manager, MilvusConfig, CollectionConfig


class TestVectorSearchService:
    """Test suite for VectorSearchService"""
    
    @pytest.fixture
    async def service(self):
        """Create a test service instance"""
        with patch('face_ai.services.vector_search.core.config_manager') as mock_config:
            mock_config.collection_config = CollectionConfig(
                name="test_collection",
                dimension=512,
                metric_type=MetricType.COSINE,
                index_type=IndexType.IVF_FLAT,
                auto_create=True,
                auto_load=True
            )
            mock_config.performance_config.enable_caching = False
            mock_config.monitoring_config.enable_metrics = False
            
            service = VectorSearchService()
            yield service
            await service.close()
    
    @pytest.fixture
    def sample_vector(self):
        """Create a sample vector for testing"""
        return np.random.rand(512).astype(np.float32)
    
    @pytest.fixture
    def sample_request(self, sample_vector):
        """Create a sample search request"""
        return SearchRequest(
            query_vector=sample_vector,
            top_k=10,
            threshold=0.6,
            metric_type=MetricType.COSINE
        )
    
    @pytest.mark.asyncio
    async def test_search_success(self, service, sample_request):
        """Test successful search operation"""
        # Mock collection and search results
        mock_collection = Mock()
        mock_hit = Mock()
        mock_hit.id = "test_id"
        mock_hit.score = 0.8
        mock_hit.entity = {"metadata": {"name": "test"}, "created_at": "2023-01-01"}
        
        mock_collection.has_index.return_value = True
        mock_collection.search.return_value = [[mock_hit]]
        
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection.return_value = mock_collection
            
            response = await service.search(sample_request)
            
            assert response.status == SearchStatus.COMPLETED
            assert len(response.results) == 1
            assert response.results[0].id == "test_id"
            assert response.results[0].score == 0.8
            assert response.total_found == 1
            assert response.search_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, service, sample_vector):
        """Test search with filters"""
        request = SearchRequest(
            query_vector=sample_vector,
            top_k=5,
            threshold=0.7,
            filters={"category": "person", "status": "active"}
        )
        
        mock_collection = Mock()
        mock_collection.has_index.return_value = True
        mock_collection.search.return_value = []
        
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection.return_value = mock_collection
            
            response = await service.search(request)
            
            # Verify filter expression was built
            mock_collection.search.assert_called_once()
            call_args = mock_collection.search.call_args
            assert 'expr' in call_args.kwargs
            assert 'category' in call_args.kwargs['expr']
            assert 'status' in call_args.kwargs['expr']
    
    @pytest.mark.asyncio
    async def test_search_validation_errors(self, service):
        """Test search request validation"""
        # Test empty vector
        with pytest.raises(ValidationError):
            await service.search(SearchRequest(query_vector=None))
        
        # Test wrong dimension
        wrong_dim_vector = np.random.rand(256).astype(np.float32)
        with pytest.raises(ValidationError):
            await service.search(SearchRequest(query_vector=wrong_dim_vector))
        
        # Test invalid top_k
        sample_vector = np.random.rand(512).astype(np.float32)
        with pytest.raises(ValidationError):
            await service.search(SearchRequest(
                query_vector=sample_vector,
                top_k=0
            ))
        
        # Test invalid threshold
        with pytest.raises(ValidationError):
            await service.search(SearchRequest(
                query_vector=sample_vector,
                threshold=1.5
            ))
    
    @pytest.mark.asyncio
    async def test_insert_vectors_success(self, service):
        """Test successful vector insertion"""
        vectors = [np.random.rand(512).astype(np.float32) for _ in range(3)]
        metadata = [{"name": f"test_{i}"} for i in range(3)]
        
        mock_collection = Mock()
        mock_result = Mock()
        mock_result.primary_keys = ["id1", "id2", "id3"]
        
        mock_collection.insert.return_value = mock_result
        
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection.return_value = mock_collection
            
            result_ids = await service.insert_vectors(vectors, metadata)
            
            assert len(result_ids) == 3
            assert result_ids == ["id1", "id2", "id3"]
            mock_collection.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_insert_vectors_validation(self, service):
        """Test vector insertion validation"""
        vectors = [np.random.rand(512).astype(np.float32) for _ in range(2)]
        metadata = [{"name": "test"}]  # Mismatched length
        
        with pytest.raises(ValidationError):
            await service.insert_vectors(vectors, metadata)
        
        # Test wrong dimension
        wrong_dim_vectors = [np.random.rand(256).astype(np.float32)]
        metadata = [{"name": "test"}]
        
        with pytest.raises(ValidationError):
            await service.insert_vectors(wrong_dim_vectors, metadata)
    
    @pytest.mark.asyncio
    async def test_delete_vectors_success(self, service):
        """Test successful vector deletion"""
        ids = ["id1", "id2", "id3"]
        
        mock_collection = Mock()
        mock_result = Mock()
        mock_result.primary_keys = ids
        mock_collection.delete.return_value = mock_result
        
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection.return_value = mock_collection
            
            deleted_count = await service.delete_vectors(ids)
            
            assert deleted_count == 3
            mock_collection.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_empty_list(self, service):
        """Test deleting empty list"""
        result = await service.delete_vectors([])
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_update_vector_success(self, service):
        """Test successful vector update"""
        vector_id = "test_id"
        new_vector = np.random.rand(512).astype(np.float32)
        metadata = {"name": "updated"}
        
        mock_collection = Mock()
        
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection.return_value = mock_collection
            
            result = await service.update_vector(vector_id, new_vector, metadata)
            
            assert result is True
            mock_collection.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_vector_validation(self, service):
        """Test vector update validation"""
        vector_id = "test_id"
        wrong_dim_vector = np.random.rand(256).astype(np.float32)
        
        with pytest.raises(ValidationError):
            await service.update_vector(vector_id, wrong_dim_vector)
    
    @pytest.mark.asyncio
    async def test_get_collection_info(self, service):
        """Test getting collection information"""
        mock_info = CollectionInfo(
            name="test_collection",
            dimension=512,
            total_vectors=1000,
            metric_type=MetricType.COSINE,
            index_type=IndexType.IVF_FLAT,
            is_loaded=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection_info.return_value = mock_info
            
            info = await service.get_collection_info()
            
            assert info.name == "test_collection"
            assert info.dimension == 512
            assert info.total_vectors == 1000
            assert info.is_loaded is True
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service):
        """Test health check when service is healthy"""
        mock_health = HealthStatus(
            is_healthy=True,
            status="healthy",
            last_check=time.time(),
            connection_status="connected",
            collection_status="healthy",
            performance_metrics={}
        )
        
        with patch('face_ai.services.vector_search.core.connection_pool') as mock_pool:
            mock_pool.health_check.return_value = mock_health
            
            with patch.object(service, 'get_collection_info') as mock_info:
                mock_info.return_value = CollectionInfo(
                    name="test", dimension=512, total_vectors=0,
                    metric_type=MetricType.COSINE, index_type=IndexType.IVF_FLAT,
                    is_loaded=True, created_at=datetime.now(), updated_at=datetime.now()
                )
                
                health = await service.health_check()
                
                assert health.is_healthy is True
                assert health.status == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, service):
        """Test health check when service is unhealthy"""
        mock_health = HealthStatus(
            is_healthy=False,
            status="unhealthy",
            last_check=time.time(),
            connection_status="disconnected",
            collection_status="error",
            performance_metrics={}
        )
        
        with patch('face_ai.services.vector_search.core.connection_pool') as mock_pool:
            mock_pool.health_check.return_value = mock_health
            
            health = await service.health_check()
            
            assert health.is_healthy is False
            assert health.status == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_create_collection(self, service):
        """Test collection creation"""
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm._create_collection = AsyncMock()
            
            result = await service.create_collection(
                name="new_collection",
                dimension=256,
                metric_type=MetricType.EUCLIDEAN,
                index_type=IndexType.HNSW
            )
            
            assert result is True
            mock_cm._create_collection.assert_called_once_with("new_collection")
    
    @pytest.mark.asyncio
    async def test_drop_collection(self, service):
        """Test collection dropping"""
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.drop_collection.return_value = True
            
            result = await service.drop_collection("test_collection")
            
            assert result is True
            mock_cm.drop_collection.assert_called_once_with("test_collection")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, service):
        """Test circuit breaker functionality"""
        # Simulate multiple failures
        for _ in range(6):  # Exceed threshold
            service._record_circuit_breaker_failure()
        
        # Circuit breaker should be open
        assert service._is_circuit_breaker_open() is True
        
        # Test that search fails when circuit breaker is open
        sample_vector = np.random.rand(512).astype(np.float32)
        request = SearchRequest(query_vector=sample_vector)
        
        response = await service.search(request)
        
        assert response.status == SearchStatus.FAILED
        assert "Circuit breaker is open" in response.error
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        with patch('face_ai.services.vector_search.core.config_manager'):
            async with VectorSearchService() as service:
                assert isinstance(service, VectorSearchService)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service, sample_request):
        """Test error handling in search operations"""
        with patch('face_ai.services.vector_search.core.collection_manager') as mock_cm:
            mock_cm.get_collection.side_effect = Exception("Connection failed")
            
            response = await service.search(sample_request)
            
            assert response.status == SearchStatus.FAILED
            assert "Connection failed" in response.error
            assert len(response.results) == 0


class TestConfiguration:
    """Test configuration management"""
    
    def test_milvus_config_defaults(self):
        """Test Milvus configuration defaults"""
        config = MilvusConfig()
        
        assert config.host == "localhost"
        assert config.port == 19530
        assert config.database == "default"
        assert config.timeout == 30.0
        assert config.max_retries == 3
    
    def test_collection_config_defaults(self):
        """Test collection configuration defaults"""
        config = CollectionConfig()
        
        assert config.name == "face_embeddings"
        assert config.dimension == 512
        assert config.metric_type == MetricType.COSINE
        assert config.index_type == IndexType.IVF_FLAT
        assert config.auto_create is True
        assert config.auto_load is True


class TestInterfaces:
    """Test interface definitions"""
    
    def test_search_request_creation(self):
        """Test SearchRequest creation"""
        vector = np.random.rand(512).astype(np.float32)
        request = SearchRequest(
            query_vector=vector,
            top_k=10,
            threshold=0.6,
            metric_type=MetricType.COSINE,
            filters={"category": "person"}
        )
        
        assert request.top_k == 10
        assert request.threshold == 0.6
        assert request.metric_type == MetricType.COSINE
        assert request.filters["category"] == "person"
    
    def test_search_result_creation(self):
        """Test SearchResult creation"""
        result = SearchResult(
            id="test_id",
            score=0.8,
            distance=0.2,
            metadata={"name": "test"}
        )
        
        assert result.id == "test_id"
        assert result.score == 0.8
        assert result.distance == 0.2
        assert result.metadata["name"] == "test"
    
    def test_search_response_creation(self):
        """Test SearchResponse creation"""
        results = [
            SearchResult(id="1", score=0.8, distance=0.2, metadata={}),
            SearchResult(id="2", score=0.7, distance=0.3, metadata={})
        ]
        
        response = SearchResponse(
            results=results,
            total_found=2,
            search_time_ms=150.0,
            request_id="req_123"
        )
        
        assert len(response.results) == 2
        assert response.total_found == 2
        assert response.search_time_ms == 150.0
        assert response.request_id == "req_123"
        assert response.status == SearchStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
