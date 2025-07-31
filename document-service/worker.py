#!/usr/bin/env python3
"""
Celery Worker for Document Service

This module runs the Celery worker for processing background tasks
such as document uploads to MinIO and other asynchronous operations.

Usage:
    python worker.py
    # or
    celery -A worker.celery_app worker --loglevel=info
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from celery import Celery
from celery.signals import worker_init, worker_shutdown, task_prerun, task_postrun

from app.core.config import get_settings
from app.core.celery_app import celery_app
from app.db.session import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


class DocumentWorker:
    """Document service worker class"""
    
    def __init__(self):
        self.celery_app = celery_app
        self.is_running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
    
    async def initialize(self):
        """Initialize worker resources"""
        try:
            logger.info("Initializing Document Worker...")
            
            # Initialize database
            await init_db()
            logger.info("Database initialized")
            
            # Test MinIO connection
            from app.services.storage import test_minio_connection
            await test_minio_connection()
            logger.info("MinIO connection verified")
            
            # Test Redis connection
            from app.core.celery_app import test_redis_connection
            test_redis_connection()
            logger.info("Redis connection verified")
            
            self.is_running = True
            logger.info("Document Worker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup worker resources"""
        try:
            logger.info("Cleaning up worker resources...")
            
            # Close database connections
            await close_db()
            logger.info("Database connections closed")
            
            self.is_running = False
            logger.info("Worker cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def start(self):
        """Start the Celery worker"""
        try:
            # Initialize async resources
            asyncio.run(self.initialize())
            
            logger.info("Starting Celery worker...")
            
            # Start Celery worker
            self.celery_app.worker_main([
                'worker',
                '--loglevel=info',
                '--concurrency=4',
                '--pool=threads',  # Use threads for async tasks
                f'--hostname=document-worker@{settings.service_name}',
                '--without-gossip',
                '--without-mingle',
                '--without-heartbeat'
            ])
            
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            sys.exit(1)
        finally:
            # Cleanup
            asyncio.run(self.cleanup())
    
    def stop(self):
        """Stop the worker"""
        if self.is_running:
            logger.info("Stopping worker...")
            self.celery_app.control.shutdown()


# Celery signal handlers
@worker_init.connect
def worker_init_handler(sender=None, **kwargs):
    """Initialize worker process"""
    logger.info(f"Worker process {sender} initializing...")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Cleanup on worker shutdown"""
    logger.info(f"Worker process {sender} shutting down...")


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    logger.info(f"Task {task.name}[{task_id}] started")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion"""
    logger.info(f"Task {task.name}[{task_id}] completed with state: {state}")


def main():
    """Main entry point"""
    logger.info("Document Service Worker starting...")
    
    # Create and start worker
    worker = DocumentWorker()
    worker.start()


if __name__ == "__main__":
    main()