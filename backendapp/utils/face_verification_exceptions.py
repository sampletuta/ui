"""
Face Verification Exception Handling Utilities
Provides comprehensive exception handling for face verification operations
"""

import logging
from typing import Dict, Any, Optional
from django.contrib import messages

logger = logging.getLogger(__name__)

class FaceVerificationExceptionHandler:
    """Handles exceptions in face verification operations with detailed logging and user feedback"""
    
    @staticmethod
    def handle_service_unavailable(service_name: str, error: Exception, request=None) -> Dict[str, Any]:
        """Handle service unavailability exceptions"""
        error_msg = f"{service_name} service is not available: {str(error)}"
        logger.error(f"Service unavailable: {service_name} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'service_unavailable',
            'service': service_name,
            'details': str(error)
        }
    
    @staticmethod
    def handle_import_error(module_name: str, error: ImportError, request=None) -> Dict[str, Any]:
        """Handle import errors for required modules"""
        error_msg = f"Required module '{module_name}' is not available: {str(error)}"
        logger.error(f"Import error: {module_name} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'import_error',
            'module': module_name,
            'details': str(error)
        }
    
    @staticmethod
    def handle_face_detection_error(image_name: str, error: Exception, request=None) -> Dict[str, Any]:
        """Handle face detection errors"""
        error_msg = f"Face detection failed for {image_name}: {str(error)}"
        logger.error(f"Face detection error: {image_name} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'face_detection_error',
            'image': image_name,
            'details': str(error)
        }
    
    @staticmethod
    def handle_verification_error(image1_name: str, image2_name: str, error: Exception, request=None) -> Dict[str, Any]:
        """Handle face verification errors"""
        error_msg = f"Face verification failed between {image1_name} and {image2_name}: {str(error)}"
        logger.error(f"Face verification error: {image1_name} vs {image2_name} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'verification_error',
            'image1': image1_name,
            'image2': image2_name,
            'details': str(error)
        }
    
    @staticmethod
    def handle_milvus_error(operation: str, error: Exception, request=None) -> Dict[str, Any]:
        """Handle Milvus vector database errors"""
        error_msg = f"Milvus operation '{operation}' failed: {str(error)}"
        logger.error(f"Milvus error: {operation} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'milvus_error',
            'operation': operation,
            'details': str(error)
        }
    
    @staticmethod
    def handle_database_error(operation: str, error: Exception, request=None) -> Dict[str, Any]:
        """Handle database operation errors"""
        error_msg = f"Database operation '{operation}' failed: {str(error)}"
        logger.error(f"Database error: {operation} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'database_error',
            'operation': operation,
            'details': str(error)
        }
    
    @staticmethod
    def handle_validation_error(field: str, value: Any, error: Exception, request=None) -> Dict[str, Any]:
        """Handle input validation errors"""
        error_msg = f"Validation error for {field}: {str(error)}"
        logger.error(f"Validation error: {field} = {value} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'validation_error',
            'field': field,
            'value': str(value),
            'details': str(error)
        }
    
    @staticmethod
    def handle_unexpected_error(operation: str, error: Exception, request=None) -> Dict[str, Any]:
        """Handle unexpected errors"""
        error_msg = f"Unexpected error during {operation}: {str(error)}"
        logger.error(f"Unexpected error: {operation} - {error}")
        
        if request:
            messages.error(request, error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error',
            'operation': operation,
            'details': str(error)
        }
    
    @staticmethod
    def format_error_for_user(error_data: Dict[str, Any]) -> str:
        """Format error data into user-friendly messages"""
        error_type = error_data.get('error_type', 'unknown')
        
        if error_type == 'service_unavailable':
            return f"Service temporarily unavailable. Please try again later. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'import_error':
            return f"System configuration issue. Please contact support. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'face_detection_error':
            return f"Unable to detect faces in the image. Please ensure the image contains clear, visible faces. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'verification_error':
            return f"Face verification failed. Please check image quality and try again. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'milvus_error':
            return f"Vector database error. Please try again later. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'database_error':
            return f"Database error. Please try again later. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'validation_error':
            return f"Invalid input data. Please check your input and try again. (Error: {error_data.get('details', 'Unknown')})"
        elif error_type == 'unexpected_error':
            return f"An unexpected error occurred. Please try again or contact support. (Error: {error_data.get('details', 'Unknown')})"
        else:
            return f"An error occurred: {error_data.get('error', 'Unknown error')}"
    
    @staticmethod
    def log_error_with_context(error: Exception, context: Dict[str, Any], operation: str):
        """Log error with additional context information"""
        context_str = ', '.join([f"{k}={v}" for k, v in context.items()])
        logger.error(f"Error in {operation} with context [{context_str}]: {error}")
    
    @staticmethod
    def create_error_response(error_data: Dict[str, Any], status_code: int = 500) -> Dict[str, Any]:
        """Create a standardized error response"""
        return {
            'success': False,
            'error': error_data.get('error', 'Unknown error'),
            'error_type': error_data.get('error_type', 'unknown'),
            'timestamp': error_data.get('timestamp'),
            'details': error_data.get('details', {}),
            'status_code': status_code
        }

def safe_face_verification_operation(operation_name: str, request=None):
    """Decorator for safe face verification operations with comprehensive error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ImportError as e:
                module_name = str(e).split("'")[1] if "'" in str(e) else "unknown"
                return FaceVerificationExceptionHandler.handle_import_error(module_name, e, request)
            except Exception as e:
                return FaceVerificationExceptionHandler.handle_unexpected_error(operation_name, e, request)
        return wrapper
    return decorator
