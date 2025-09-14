"""
Celery configuration for Django Face AI application.
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Create the celery app
app = Celery('backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Celery configuration
app.conf.update(
    # Task routing
    task_routes={
        'face_ai.*': {'queue': 'face_ai'},
        'video_processing.*': {'queue': 'video_processing'},
        'default': {'queue': 'default'},
    },
    
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task execution
    task_always_eager=False,
    task_eager_propagates=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result backend
    result_expires=3600,  # 1 hour
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Worker time limits
    worker_disable_rate_limits=False,
    worker_max_memory_per_child=200000,  # 200MB
    
    # Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        'cleanup-temp-files': {
            'task': 'backendapp.tasks.cleanup_temp_files',
            'schedule': 3600.0,  # Every hour
        },
        'process-pending-videos': {
            'task': 'video_processing.tasks.process_pending_videos',
            'schedule': 300.0,   # Every 5 minutes
        },
    },
)
