import os
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select
from app.models import Document
from app.db.session import get_db
from app.services.storage import upload_file_to_minio, test_minio_connection
from app.services.documents import DocumentService
from app.core.config import get_settings
from typing import Optional, Dict, Any, List
import asyncio
import hashlib
import json
from datetime import datetime

logger = get_task_logger(__name__)
settings = get_settings()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def init_db(self):
    """Initialize database tables"""
    import asyncio
    from app.db.session import init_db as _init_db

    async def _init():
        try:
            await _init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    try:
        asyncio.run(_init())
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_upload(
    self,
    doc_id: int,
    filename: str,
    content_type: str,
    tags: List[str],
    data: bytes,
    uploaded_by: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Process document upload to MinIO and update database"""
    
    async def _process_upload():
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            try:
                # Get document from database
                result = await session.execute(
                    select(Document).where(Document.id == doc_id)
                )
                doc = result.scalar_one_or_none()
                
                if not doc:
                    raise ValueError(f"Document with ID {doc_id} not found")
                
                logger.info(f"Processing upload for document {doc_id}: {filename}")
                
                # Calculate file hash
                file_hash = hashlib.sha256(data).hexdigest()
                
                # Upload to MinIO
                object_name = f"{doc_id}_{file_hash[:8]}_{filename}"
                
                # Prepare metadata for MinIO
                minio_metadata = {
                    "document-id": str(doc_id),
                    "filename": filename,
                    "uploaded-by": uploaded_by or "system",
                    "upload-timestamp": datetime.utcnow().isoformat()
                }
                
                if metadata:
                    minio_metadata.update({
                        f"custom-{k}": str(v) for k, v in metadata.items()
                    })
                
                await upload_file_to_minio(
                    obj_bytes=data,
                    object_name=object_name,
                    content_type=content_type,
                    metadata=minio_metadata
                )
                
                # Update document in database
                doc.status = "uploaded"
                doc.size = len(data)
                doc.file_hash = file_hash
                doc.object_name = object_name
                doc.updated_at = datetime.utcnow()
                
                if metadata:
                    doc.metadata = metadata
                
                await session.commit()
                
                logger.info(
                    f"Successfully processed upload for document {doc_id}. "
                    f"Object name: {object_name}, Size: {len(data)} bytes"
                )
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing upload for document {doc_id}: {e}")
                
                # Update document status to failed
                try:
                    result = await session.execute(
                        select(Document).where(Document.id == doc_id)
                    )
                    doc = result.scalar_one_or_none()
                    if doc:
                        doc.status = "failed"
                        doc.updated_at = datetime.utcnow()
                        await session.commit()
                except Exception as update_error:
                    logger.error(f"Failed to update document status: {update_error}")
                
                raise
    
    try:
        asyncio.run(_process_upload())
    except Exception as exc:
        logger.error(f"Upload processing failed for document {doc_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def cleanup_failed_uploads(self, max_age_hours: int = 24):
    """Clean up failed uploads older than specified hours"""
    
    async def _cleanup():
        from app.db.session import AsyncSessionLocal
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        async with AsyncSessionLocal() as session:
            try:
                # Find failed uploads older than cutoff time
                result = await session.execute(
                    select(Document).where(
                        Document.status == "failed",
                        Document.created_at < cutoff_time
                    )
                )
                failed_docs = result.scalars().all()
                
                cleaned_count = 0
                for doc in failed_docs:
                    try:
                        await session.delete(doc)
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting failed document {doc.id}: {e}")
                
                await session.commit()
                
                logger.info(
                    f"Cleaned up {cleaned_count} failed uploads older than {max_age_hours} hours"
                )
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error during cleanup: {e}")
                raise
    
    try:
        asyncio.run(_cleanup())
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def test_services_health(self):
    """Test health of external services (MinIO, Database)"""
    
    async def _test_health():
        health_status = {
            "minio": False,
            "database": False,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Test MinIO connection
        try:
            health_status["minio"] = await test_minio_connection()
            logger.info(f"MinIO health check: {'OK' if health_status['minio'] else 'FAILED'}")
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
        
        # Test Database connection
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                await session.execute(select(1))
                health_status["database"] = True
            logger.info("Database health check: OK")
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        return health_status
    
    try:
        return asyncio.run(_test_health())
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_document_thumbnail(
    self,
    doc_id: int,
    max_size: tuple = (200, 200)
):
    """Generate thumbnail for document (for image files)"""
    
    async def _generate_thumbnail():
        from app.db.session import AsyncSessionLocal
        from app.services.storage import download_file_from_minio, upload_file_to_minio
        from PIL import Image
        import io
        
        async with AsyncSessionLocal() as session:
            try:
                # Get document from database
                result = await session.execute(
                    select(Document).where(Document.id == doc_id)
                )
                doc = result.scalar_one_or_none()
                
                if not doc or doc.status != "uploaded":
                    raise ValueError(f"Document {doc_id} not found or not uploaded")
                
                # Check if it's an image file
                if not doc.content_type.startswith('image/'):
                    logger.info(f"Document {doc_id} is not an image, skipping thumbnail generation")
                    return
                
                logger.info(f"Generating thumbnail for document {doc_id}")
                
                # Download original file
                file_data = await download_file_from_minio(doc.object_name)
                
                # Generate thumbnail
                with Image.open(io.BytesIO(file_data)) as img:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Save thumbnail
                    thumbnail_io = io.BytesIO()
                    img.save(thumbnail_io, format='JPEG', quality=85)
                    thumbnail_data = thumbnail_io.getvalue()
                
                # Upload thumbnail to MinIO
                thumbnail_object_name = f"thumbnails/{doc.object_name}_thumb.jpg"
                await upload_file_to_minio(
                    obj_bytes=thumbnail_data,
                    object_name=thumbnail_object_name,
                    content_type="image/jpeg",
                    metadata={
                        "document-id": str(doc_id),
                        "thumbnail": "true",
                        "original-object": doc.object_name
                    }
                )
                
                # Update document metadata
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["thumbnail_object_name"] = thumbnail_object_name
                doc.updated_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"Successfully generated thumbnail for document {doc_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error generating thumbnail for document {doc_id}: {e}")
                raise
    
    try:
        asyncio.run(_generate_thumbnail())
    except Exception as exc:
        logger.error(f"Thumbnail generation failed for document {doc_id}: {exc}")
        raise self.retry(exc=exc)
