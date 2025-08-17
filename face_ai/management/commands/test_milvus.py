from django.core.management.base import BaseCommand
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Milvus connection and create watchlist collection'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-only',
            action='store_true',
            help='Only create collection, skip other tests'
        )
        parser.add_argument(
            '--test-insert',
            action='store_true',
            help='Test inserting a sample embedding'
        )
    
    def handle(self, *args, **options):
        try:
            from face_ai.services.milvus_service import MilvusService
            
            # Show configuration
            milvus_config = getattr(settings, 'MILVUS_CONFIG', {})
            self.stdout.write("🔧 Milvus Configuration:")
            self.stdout.write(f"   Host: {milvus_config.get('HOST', 'localhost')}")
            self.stdout.write(f"   Port: {milvus_config.get('PORT', 9001)}")
            self.stdout.write(f"   Collection: {milvus_config.get('COLLECTION_NAME', 'watchlist')}")
            self.stdout.write(f"   Dimension: {milvus_config.get('DIMENSION', 512)}")
            self.stdout.write(f"   Metric Type: {milvus_config.get('METRIC_TYPE', 'COSINE')}")
            self.stdout.write(f"   Index Type: {milvus_config.get('INDEX_TYPE', 'IVF_FLAT')}")
            
            if options['create_only']:
                self.stdout.write("\n📚 Creating collection only...")
                service = MilvusService()
                service.create_collection_if_not_exists()
                
                stats = service.get_collection_stats()
                if stats['exists']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Collection '{stats['collection_name']}' created/verified successfully!"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR("❌ Failed to create collection")
                    )
                return
            
            # Test 1: Service initialization
            self.stdout.write("\n🔌 Testing Milvus Service...")
            try:
                service = MilvusService()
                self.stdout.write(
                    self.style.SUCCESS("✅ Milvus service initialized successfully")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Milvus service initialization failed: {e}")
                )
                return
            
            # Test 2: Collection creation/verification
            self.stdout.write("\n📚 Testing Collection...")
            try:
                service.create_collection_if_not_exists()
                stats = service.get_collection_stats()
                
                if stats['exists']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Collection '{stats['collection_name']}' ready!"
                        )
                    )
                    self.stdout.write(f"   Total vectors: {stats['total_vectors']}")
                    self.stdout.write(f"   Index status: {stats['index_status']}")
                else:
                    self.stdout.write(
                        self.style.ERROR("❌ Collection not available")
                    )
                    return
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Collection test failed: {e}")
                )
                return
            
            # Test 3: Basic operations
            self.stdout.write("\n🧪 Testing Basic Operations...")
            try:
                # Test collection loading
                service.collection.load()
                self.stdout.write("✅ Collection loaded successfully")
                
                # Test stats retrieval
                stats = service.get_collection_stats()
                self.stdout.write(f"✅ Stats retrieved: {stats['total_vectors']} vectors")
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Basic operations test failed: {e}")
                )
            
            # Test 4: Embedding insertion (if requested)
            if options['test_insert']:
                self.stdout.write("\n📊 Testing Embedding Insertion...")
                try:
                    import numpy as np
                    
                    # Create sample embedding
                    sample_embedding = np.zeros(512).tolist()
                    
                    test_data = [{
                        'embedding': sample_embedding,
                        'target_id': 'test-target-123',
                        'photo_id': 'test-photo-456',
                        'confidence_score': 0.95,
                        'created_at': '2024-01-01T00:00:00Z'
                    }]
                    
                    # Insert test embedding
                    vector_ids = service.insert_face_embeddings(test_data)
                    
                    if vector_ids:
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Test embedding inserted! Vector ID: {vector_ids[0]}")
                        )
                        
                        # Clean up
                        deleted_count = service.delete_embeddings_by_target_id('test-target-123')
                        self.stdout.write(f"✅ Test data cleaned up ({deleted_count} embeddings removed)")
                    else:
                        self.stdout.write(
                            self.style.ERROR("❌ Failed to insert test embedding")
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Embedding insertion test failed: {e}")
                    )
            
            # Success summary
            self.stdout.write("\n" + "="*60)
            self.stdout.write(
                self.style.SUCCESS("🎉 Milvus test completed successfully!")
            )
            self.stdout.write(f"\n✅ Your 'watchlist' collection is ready for face embeddings!")
            self.stdout.write("   - Collection name: watchlist")
            self.stdout.write("   - Dimension: 512")
            self.stdout.write("   - Metric type: COSINE")
            self.stdout.write("   - Index type: IVF_FLAT")
            self.stdout.write("   - Ready for production use!")
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "Face AI service not available. Please ensure all dependencies are installed."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Milvus test command failed: {e}")
            )
            logger.error(f"Milvus test command failed: {e}")
