#!/usr/bin/env python3
"""
ASGI Startup Script for Face AI Application.

This script starts the ASGI application with proper configuration for parallel processing.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Import Django and configure logging
import django
django.setup()

from face_ai.asgi_config import get_config, get_development_config, get_production_config
from face_ai.asgi import application

def setup_logging(config):
    """Setup logging configuration"""
    log_config = config['LOGGING']
    
    logging.basicConfig(
        level=getattr(logging, log_config['LEVEL']),
        format=log_config['FORMAT'],
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_config['FILE'])
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('face_ai').setLevel(logging.INFO)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

def get_environment_config():
    """Get configuration based on environment"""
    env = os.getenv('FACE_AI_ENV', 'development').lower()
    
    if env == 'production':
        return get_production_config()
    elif env == 'testing':
        return get_testing_config()
    else:
        return get_development_config()

def main():
    """Main entry point"""
    try:
        # Get configuration
        config = get_environment_config()
        
        # Setup logging
        setup_logging(config)
        
        logger = logging.getLogger(__name__)
        logger.info("Starting Face AI ASGI Application...")
        logger.info(f"Environment: {os.getenv('FACE_AI_ENV', 'development')}")
        logger.info(f"Configuration: {config['ASGI_APP']}")
        logger.info(f"Parallel Workers: {config['PARALLEL']['MAX_WORKERS']}")
        logger.info(f"Thread Pool Size: {config['PARALLEL']['THREAD_POOL_SIZE']}")
        
        # Import uvicorn
        import uvicorn
        
        # Start the ASGI server
        uvicorn.run(
            "face_ai.asgi:application",
            host=config['ASGI_APP']['HOST'],
            port=config['ASGI_APP']['PORT'],
            reload=config['ASGI_APP']['RELOAD'],
            log_level=config['LOGGING']['LEVEL'].lower(),
            access_log=True,
            workers=1,  # ASGI handles concurrency internally
            loop="asyncio",
            http="httptools",
            ws="websockets",
            lifespan="on",
            forwarded_allow_ips="*",
            proxy_headers=True,
            server_header=False,
            date_header=False,
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down Face AI ASGI Application...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start Face AI ASGI Application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
