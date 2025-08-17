"""
Target Integration Service Wrapper.

This wrapper provides a unified interface for both synchronous and asynchronous
target integration operations, automatically choosing the best method based on context.
"""

import logging
import asyncio
from typing import List, Dict, Optional
from django.conf import settings

from .target_integration import TargetIntegrationService
from .async_target_integration import AsyncTargetIntegrationService

logger = logging.getLogger(__name__)

class TargetIntegrationWrapper:
    """
    Wrapper service that provides both sync and async interfaces for target integration.
    
    This allows existing code to continue working while enabling async operations
    for better performance and parallel processing.
    """
    
    def __init__(self, use_async: bool = True, max_workers: int = 4):
        """
        Initialize the wrapper service.
        
        Args:
            use_async: Whether to use async services (default: True)
            max_workers: Maximum number of parallel workers for async operations
        """
        self.use_async = use_async
        self.max_workers = max_workers
        
        # Initialize services
        if self.use_async:
            try:
                self.async_service = AsyncTargetIntegrationService(max_workers=max_workers)
                logger.info(f"Async target integration service initialized with {max_workers} workers")
            except Exception as e:
                logger.warning(f"Failed to initialize async service, falling back to sync: {e}")
                self.use_async = False
        
        if not self.use_async:
            self.sync_service = TargetIntegrationService()
            logger.info("Synchronous target integration service initialized")
    
    def process_target_photo(self, target_photo, target_id: str) -> Dict:
        """
        Process a single target photo (sync interface).
        
        Args:
            target_photo: TargetPhoto instance
            target_id: ID of the target
            
        Returns:
            Processing results dictionary
        """
        if self.use_async:
            # Run async method in sync context
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.async_service.process_target_photo_async(target_photo, target_id)
                )
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Async processing failed, falling back to sync: {e}")
                return self.sync_service.process_target_photo(target_photo, target_id)
        else:
            return self.sync_service.process_target_photo(target_photo, target_id)
    
    def process_target_photos_batch(self, target_photos: List, target_id: str) -> Dict:
        """
        Process multiple target photos in batch (sync interface).
        
        Args:
            target_photos: List of TargetPhoto instances
            target_id: ID of the target
            
        Returns:
            Batch processing results dictionary
        """
        if self.use_async:
            # Run async method in sync context
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.async_service.process_target_photos_batch_async(target_photos, target_id)
                )
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Async batch processing failed, falling back to sync: {e}")
                return self.sync_service.process_target_photos_batch(target_photos, target_id)
        else:
            return self.sync_service.process_target_photos_batch(target_photos, target_id)
    
    def update_target_normalized_embedding(self, target_id: str) -> Dict:
        """
        Update a target's normalized embedding (sync interface).
        
        Args:
            target_id: ID of the target
            
        Returns:
            Update results dictionary
        """
        if self.use_async:
            # Run async method in sync context
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.async_service.update_target_normalized_embedding_async(target_id)
                )
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Async update failed, falling back to sync: {e}")
                return self.sync_service.update_target_normalized_embedding(target_id)
        else:
            return self.sync_service.update_target_normalized_embedding(target_id)
    
    def get_target_face_summary(self, target_id: str) -> Dict:
        """
        Get a summary of face processing for a target (sync interface).
        
        Args:
            target_id: ID of the target
            
        Returns:
            Summary results dictionary
        """
        if self.use_async:
            # Run async method in sync context
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.async_service.get_target_face_summary_async(target_id)
                )
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Async summary failed, falling back to sync: {e}")
                return self.sync_service.get_target_face_summary(target_id)
        else:
            return self.sync_service.get_target_face_summary(target_id)
    
    async def process_target_photo_async(self, target_photo, target_id: str) -> Dict:
        """
        Process a single target photo asynchronously.
        
        Args:
            target_photo: TargetPhoto instance
            target_id: ID of the target
            
        Returns:
            Processing results dictionary
        """
        if self.use_async:
            return await self.async_service.process_target_photo_async(target_photo, target_id)
        else:
            # Fallback to sync in async context
            return self.sync_service.process_target_photo(target_photo, target_id)
    
    async def process_target_photos_batch_async(self, target_photos: List, target_id: str) -> Dict:
        """
        Process multiple target photos asynchronously in batch.
        
        Args:
            target_photos: List of TargetPhoto instances
            target_id: ID of the target
            
        Returns:
            Batch processing results dictionary
        """
        if self.use_async:
            return await self.async_service.process_target_photos_batch_async(target_photos, target_id)
        else:
            # Fallback to sync in async context
            return self.sync_service.process_target_photos_batch(target_photos, target_id)
    
    async def update_target_normalized_embedding_async(self, target_id: str) -> Dict:
        """
        Update a target's normalized embedding asynchronously.
        
        Args:
            target_id: ID of the target
            
        Returns:
            Update results dictionary
        """
        if self.use_async:
            return await self.async_service.update_target_normalized_embedding_async(target_id)
        else:
            # Fallback to sync in async context
            return self.sync_service.update_target_normalized_embedding(target_id)
    
    async def get_target_face_summary_async(self, target_id: str) -> Dict:
        """
        Get a summary of face processing for a target asynchronously.
        
        Args:
            target_id: ID of the target
            
        Returns:
            Summary results dictionary
        """
        if self.use_async:
            return await self.async_service.get_target_face_summary_async(target_id)
        else:
            # Fallback to sync in async context
            return self.sync_service.get_target_face_summary(target_id)
    
    def cleanup_target_embeddings(self, target_id: str) -> Dict:
        """
        Clean up all embeddings for a target (sync interface).
        
        Args:
            target_id: ID of the target
            
        Returns:
            Cleanup results dictionary
        """
        if self.use_async:
            # Run async method in sync context
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.async_service.cleanup_target_embeddings_async(target_id)
                )
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Async cleanup failed, falling back to sync: {e}")
                # Fallback to sync method if available
                return {'success': False, 'error': 'Cleanup not available in sync mode'}
        else:
            # Fallback to sync method if available
            return {'success': False, 'error': 'Cleanup not available in sync mode'}
    
    async def cleanup_target_embeddings_async(self, target_id: str) -> Dict:
        """
        Clean up all embeddings for a target asynchronously.
        
        Args:
            target_id: ID of the target
            
        Returns:
            Cleanup results dictionary
        """
        if self.use_async:
            return await self.async_service.cleanup_target_embeddings_async(target_id)
        else:
            # Fallback to sync in async context
            return {'success': False, 'error': 'Cleanup not available in sync mode'}
    
    def get_service_info(self) -> Dict:
        """
        Get information about the current service configuration.
        
        Returns:
            Service information dictionary
        """
        return {
            'use_async': self.use_async,
            'max_workers': self.max_workers,
            'service_type': 'async' if self.use_async else 'sync',
            'capabilities': {
                'parallel_processing': self.use_async,
                'batch_processing': True,
                'real_time_processing': self.use_async,
                'fallback_support': True
            }
        }
