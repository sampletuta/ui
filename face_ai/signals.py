from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

# Simple processing lock to prevent duplicate processing
_processing_targets = set()

@receiver(post_save, sender='backendapp.TargetPhoto')
def auto_process_target_photo(sender, instance, created, **kwargs):
    """
    Automatically process target photos and update the target's normalized embedding
    when they are created or updated
    """
    if instance.image:
        target_id = str(instance.person.id)
        
        # Check if target is already being processed to prevent duplicates
        if target_id in _processing_targets:
            logger.info(f"Target {target_id} is already being processed, skipping duplicate signal")
            return
        
        try:
            from .services.target_integration import TargetIntegrationService
            
            # Add target to processing set
            _processing_targets.add(target_id)
            
            # Initialize face AI service (use sync service for signals)
            face_service = TargetIntegrationService()
            
            # Get count of existing photos for this target
            from backendapp.models import TargetPhoto
            existing_photos_count = TargetPhoto.objects.filter(person_id=target_id).count()
            
            logger.info(f"Processing {'new' if created else 'updated'} photo for target {target_id} (total photos: {existing_photos_count})")
            
            # Update the target's normalized embedding with all photos
            result = face_service.update_target_normalized_embedding(target_id)
            
            if result['success']:
                if result.get('normalized_embedding_id'):
                    logger.info(
                        f"Updated normalized embedding for target {target_id}: "
                        f"embedding ID {result['normalized_embedding_id']} with {result.get('total_photos', 0)} photos "
                        f"(strategy: {result.get('embedding_strategy', 'unknown')})"
                    )
                else:
                    logger.info(
                        f"Updated target {target_id} but no faces found in any photos"
                    )
            else:
                logger.warning(
                    f"Update of normalized embedding failed for target {target_id}: {result.get('error')}"
                )
                
        except ImportError:
            logger.warning("Face AI service not available for auto-processing")
        except Exception as e:
            logger.error(f"Auto-processing failed for target {target_id}: {e}")
        finally:
            # Remove target from processing set
            _processing_targets.discard(target_id)

# REMOVED: prevent_last_image_deletion signal that blocks deletion of last image

@receiver(post_delete, sender='backendapp.TargetPhoto')
def auto_update_after_photo_deletion(sender, instance, **kwargs):
    """
    Automatically update the target's normalized embedding after a photo is deleted
    """
    target_id = str(instance.person.id)
    
    # Check if target is already being processed to prevent duplicates
    if target_id in _processing_targets:
        logger.info(f"Target {target_id} is already being processed, skipping duplicate signal")
        return
    
    try:
        from .services.target_integration import TargetIntegrationService
        
        # Add target to processing set
        _processing_targets.add(target_id)
        
        # Initialize face AI service (use sync service for signals)
        face_service = TargetIntegrationService()
        
        # Get count of remaining photos for this target
        from backendapp.models import TargetPhoto
        remaining_photos_count = TargetPhoto.objects.filter(person_id=target_id).count()
        
        logger.info(f"Processing deleted photo for target {target_id} (remaining photos: {remaining_photos_count})")
        
        # Update the target's normalized embedding without the deleted photo
        result = face_service.update_target_normalized_embedding(target_id)
        
        if result['success']:
            if result.get('normalized_embedding_id'):
                logger.info(
                    f"Updated normalized embedding for target {target_id} after deletion: "
                    f"embedding ID {result['normalized_embedding_id']} with {result.get('total_photos', 0)} photos "
                    f"(strategy: {result.get('embedding_strategy', 'unknown')})"
                )
            elif result.get('embeddings_removed'):
                logger.info(
                    f"Removed all embeddings for target {target_id} after last photo deletion: "
                    f"{result['embeddings_removed']} embeddings removed"
                )
        else:
            logger.warning(
                f"Update of normalized embedding failed after deletion for target {target_id}: {result.get('error')}"
            )
            
    except ImportError:
        logger.warning("Face AI service not available for auto-processing after photo deletion")
    except Exception as e:
        logger.error(f"Auto-update after photo deletion failed for target {target_id}: {e}")
    finally:
        # Remove target from processing set
        _processing_targets.discard(target_id)

@receiver(post_save, sender='backendapp.Targets_watchlist')
def auto_process_existing_photos(sender, instance, created, **kwargs):
    """
    When a target is created, process any existing photos to create normalized embedding
    """
    if created:
        target_id = str(instance.id)
        
        # Check if target is already being processed to prevent duplicates
        if target_id in _processing_targets:
            logger.info(f"Target {target_id} is already being processed, skipping duplicate signal")
            return
        
        try:
            from .services.target_integration import TargetIntegrationService
            
            # Add target to processing set
            _processing_targets.add(target_id)
            
            # Get all photos for this target
            photos = instance.images.all()
            
            if photos.exists():
                # Initialize face AI service (use sync service for signals)
                face_service = TargetIntegrationService()
                
                # Process all photos to create normalized embedding
                result = face_service.process_target_photos_batch(photos, target_id)
                
                if result['success']:
                    logger.info(
                        f"Auto-processed {result['processed_photos']} existing photos for new target {target_id}: "
                        f"normalized embedding created with ID {result.get('normalized_embedding_id', 'N/A')}"
                    )
                else:
                    logger.warning(
                        f"Auto-processing existing photos failed for target {target_id}: {result.get('error')}"
                    )
            else:
                logger.info(f"New target {target_id} created with no photos - no processing needed")
                
        except ImportError:
            logger.warning("Face AI service not available for auto-processing existing photos")
        except Exception as e:
            logger.error(f"Auto-processing existing photos failed for target {target_id}: {e}")
        finally:
            # Remove target from processing set
            _processing_targets.discard(target_id)

@receiver(pre_delete, sender='backendapp.Targets_watchlist')
def cleanup_target_embeddings(sender, instance, **kwargs):
    """
    Clean up all embeddings for a target when the target is deleted
    """
    target_id = str(instance.id)
    
    try:
        from .services.target_integration import TargetIntegrationService
        
        # Initialize service
        face_service = TargetIntegrationService()
        
        # Remove all embeddings for this target
        deleted_count = face_service.milvus_service.delete_embeddings_by_target_id(target_id)
        
        logger.info(
            f"Cleaned up {deleted_count} embeddings for deleted target {target_id}"
        )
        
    except ImportError:
        logger.warning("Face AI service not available for target deletion cleanup")
    except Exception as e:
        logger.error(f"Failed to clean up embeddings for deleted target {target_id}: {e}")
    finally:
        # Remove any processing locks for this target
        global _processing_targets
        _processing_targets.discard(target_id)
