"""
Vector Search Exceptions

Custom exceptions for the vector search service.
"""


class VectorSearchError(Exception):
    """Base exception for vector search operations"""
    pass


class ConnectionError(VectorSearchError):
    """Connection-related errors"""
    pass


class SearchError(VectorSearchError):
    """Search operation errors"""
    pass


class CollectionError(VectorSearchError):
    """Collection management errors"""
    pass


class ValidationError(VectorSearchError):
    """Input validation errors"""
    pass


class TimeoutError(VectorSearchError):
    """Operation timeout errors"""
    pass


class AuthenticationError(VectorSearchError):
    """Authentication/authorization errors"""
    pass


class RateLimitError(VectorSearchError):
    """Rate limiting errors"""
    pass


class ConfigurationError(VectorSearchError):
    """Configuration-related errors"""
    pass


