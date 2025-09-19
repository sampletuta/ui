"""
Vector Search Service Package

This package provides a production-ready vector search service with proper
separation of concerns, error handling, and scalability features.
"""

from .core import VectorSearchService
from .interfaces import VectorSearchInterface, SearchResult, SearchRequest
from .exceptions import VectorSearchError, ConnectionError, SearchError

__all__ = [
    'VectorSearchService',
    'VectorSearchInterface', 
    'SearchResult',
    'SearchRequest',
    'VectorSearchError',
    'ConnectionError',
    'SearchError'
]
