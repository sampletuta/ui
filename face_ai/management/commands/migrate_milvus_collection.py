from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate existing Milvus collection to include photo_id field for proper photo tracking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if collection exists'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it'
        )
    
    def handle(self, *args, **options):
        try:
            from face_ai.services.milvus_service import MilvusService
            
            # Initialize Milvus service
            milvus_service = MilvusService()
            
            # Check current collection status
            current_stats = milvus_service.get_collection_stats()
            
            if not current_stats['exists']:
                self.stdout.write(
                    self.style.WARNING(
                        f"Collection {milvus_service.collection_name} does not exist. "
                        "It will be created automatically when first used."
                    )
                )
                return
            
            self.stdout.write(f"Current collection: {current_stats['collection_name']}")
            self.stdout.write(f"Total vectors: {current_stats['total_vectors']}")
            self.stdout.write(f"Dimension: {current_stats['dimension']}")
            
            if options['dry_run']:
                self.stdout.write("DRY RUN MODE - No actual migration will occur")
                self.stdout.write("The collection will be recreated with photo_id field when needed")
                return
            
            # Check if collection needs migration (has photo_id field)
            try:
                # Try to query photo_id field to see if it exists
                milvus_service.collection.load()
                test_query = milvus_service.collection.query(
                    expr="id >= 0",
                    limit=1,
                    output_fields=["photo_id"]
                )
                
                if test_query and 'photo_id' in test_query[0]:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Collection already has photo_id field. No migration needed."
                        )
                    )
                    return
                    
            except Exception as e:
                # Field doesn't exist, needs migration
                pass
            
            self.stdout.write(
                self.style.WARNING(
                    "Collection needs migration to include photo_id field. "
                    "This will recreate the collection and lose existing data."
                )
            )
            
            if not options['force']:
                self.stdout.write(
                    self.style.ERROR(
                        "Use --force to proceed with migration. "
                        "WARNING: This will delete all existing embeddings!"
                    )
                )
                return
            
            # Proceed with migration
            self.stdout.write("Starting collection migration...")
            
            # Drop existing collection
            from pymilvus import utility
            if utility.has_collection(milvus_service.collection_name):
                utility.drop_collection(milvus_service.collection_name)
                self.stdout.write("Dropped existing collection")
            
            # Create new collection with photo_id field
            milvus_service.create_collection_if_not_exists()
            
            # Verify new collection
            new_stats = milvus_service.get_collection_stats()
            
            if new_stats['exists']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Migration completed successfully! "
                        f"New collection: {new_stats['collection_name']}"
                    )
                )
                self.stdout.write(
                    "Note: All existing embeddings were lost during migration. "
                    "Use 'process_existing_photos' command to reprocess photos."
                )
            else:
                self.stdout.write(
                    self.style.ERROR("Migration failed - collection not created")
                )
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "Face AI service not available. Please ensure all dependencies are installed."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Migration command failed: {e}")
            )
            logger.error(f"Milvus collection migration failed: {e}")
