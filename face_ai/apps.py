from django.apps import AppConfig


class FaceAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'face_ai'
    verbose_name = 'Face AI Recognition'
    
    def ready(self):
        """Initialize app when Django starts"""
        try:
            # Import signals to register them
            import face_ai.signals
            print("✅ Face AI signals loaded successfully")
        except ImportError as e:
            print(f"⚠️ Face AI signals not loaded: {e}")
        except Exception as e:
            print(f"❌ Error loading Face AI signals: {e}")
