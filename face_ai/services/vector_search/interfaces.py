"""
Vector Search Interfaces

Defines the core interfaces and data models for the vector search service.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import numpy as np
from datetime import datetime


class SearchStatus(Enum):
    """Search operation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(Enum):
    """Distance metric types"""
    COSINE = "COSINE"
    EUCLIDEAN = "EUCLIDEAN"
    IP = "IP"  # Inner Product


class IndexType(Enum):
    """Index types for vector search"""
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    IVF_PQ = "IVF_PQ"
    HNSW = "HNSW"
    ANNOY = "ANNOY"


@dataclass
class SearchRequest:
    """Search request parameters"""
    query_vector: np.ndarray
    top_k: int = 10
    threshold: float = 0.6
    metric_type: MetricType = MetricType.COSINE
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True
    timeout: Optional[float] = None
    request_id: Optional[str] = None


@dataclass
class SearchResult:
    """Individual search result"""
    id: Union[str, int]
    score: float
    distance: float
    metadata: Dict[str, Any]
    vector: Optional[np.ndarray] = None


@dataclass
class SearchResponse:
    """Complete search response"""
    results: List[SearchResult]
    total_found: int
    search_time_ms: float
    request_id: Optional[str] = None
    status: SearchStatus = SearchStatus.COMPLETED
    error: Optional[str] = None


@dataclass
class CollectionInfo:
    """Collection information"""
    name: str
    dimension: int
    total_vectors: int
    metric_type: MetricType
    index_type: IndexType
    is_loaded: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class HealthStatus:
    """Service health status"""
    is_healthy: bool
    status: str
    last_check: datetime
    connection_status: str
    collection_status: str
    performance_metrics: Dict[str, float]


class VectorSearchInterface(ABC):
    """Abstract interface for vector search operations"""
    
    @abstractmethod
    async def search(self, request: SearchRequest) -> SearchResponse:
        """Perform vector search"""
        pass
    
    @abstractmethod
    async def insert_vectors(self, vectors: List[np.ndarray], 
                           metadata: List[Dict[str, Any]]) -> List[Union[str, int]]:
        """Insert vectors into the collection"""
        pass
    
    @abstractmethod
    async def delete_vectors(self, ids: List[Union[str, int]]) -> int:
        """Delete vectors by IDs"""
        pass
    
    @abstractmethod
    async def update_vector(self, vector_id: Union[str, int], 
                          vector: np.ndarray, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a vector and its metadata"""
        pass
    
    @abstractmethod
    async def get_collection_info(self) -> CollectionInfo:
        """Get collection information"""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check service health"""
        pass
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int, 
                              metric_type: MetricType = MetricType.COSINE,
                              index_type: IndexType = IndexType.IVF_FLAT) -> bool:
        """Create a new collection"""
        pass
    
    @abstractmethod
    async def drop_collection(self, name: str) -> bool:
        """Drop a collection"""
        pass


