from minio import Minio
from minio.error import S3Error, InvalidResponseError
from app.core.config import get_settings
from typing import Optional, List, Dict, Any
import io
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
settings = get_settings()


class MinIOService:
    """MinIO storage service"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MinIO client"""
        try:
            self.client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            logger.info(f"MinIO client initialized for endpoint: {settings.minio_endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise
    
    async def ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't"""
        try:
            loop = asyncio.get_event_loop()
            bucket_exists = await loop.run_in_executor(
                None, self.client.bucket_exists, settings.minio_bucket
            )
            
            if not bucket_exists:
                await loop.run_in_executor(
                    None, 
                    self.client.make_bucket, 
                    settings.minio_bucket,
                    settings.minio_region
                )
                logger.info(f"Created bucket: {settings.minio_bucket}")
            else:
                logger.debug(f"Bucket exists: {settings.minio_bucket}")
                
        except S3Error as e:
            logger.error(f"S3 error ensuring bucket exists: {e}")
            raise
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    async def upload_file(
        self, 
        obj_bytes: bytes, 
        object_name: str, 
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Upload file to MinIO"""
        try:
            await self.ensure_bucket_exists()
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.put_object,
                settings.minio_bucket,
                object_name,
                io.BytesIO(obj_bytes),
                len(obj_bytes),
                content_type,
                metadata or {}
            )
            
            logger.info(f"File uploaded successfully: {object_name}")
            
        except S3Error as e:
            logger.error(f"S3 error uploading file {object_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error uploading file {object_name}: {e}")
            raise
    
    async def download_file(self, object_name: str) -> bytes:
        """Download file from MinIO"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.client.get_object,
                settings.minio_bucket,
                object_name
            )
            
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"File downloaded successfully: {object_name}")
            return data
            
        except S3Error as e:
            logger.error(f"S3 error downloading file {object_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error downloading file {object_name}: {e}")
            raise
    
    async def remove_file(self, object_name: str) -> None:
        """Remove file from MinIO"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.remove_object,
                settings.minio_bucket,
                object_name
            )
            
            logger.info(f"File removed successfully: {object_name}")
            
        except S3Error as e:
            logger.error(f"S3 error removing file {object_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error removing file {object_name}: {e}")
            raise
    
    async def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.stat_object,
                settings.minio_bucket,
                object_name
            )
            return True
        except S3Error:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence {object_name}: {e}")
            return False
    
    async def get_file_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Get file information from MinIO"""
        try:
            loop = asyncio.get_event_loop()
            stat = await loop.run_in_executor(
                None,
                self.client.stat_object,
                settings.minio_bucket,
                object_name
            )
            
            return {
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata
            }
            
        except S3Error as e:
            logger.error(f"S3 error getting file info {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting file info {object_name}: {e}")
            return None
    
    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in bucket"""
        try:
            loop = asyncio.get_event_loop()
            objects = await loop.run_in_executor(
                None,
                lambda: list(self.client.list_objects(
                    settings.minio_bucket, 
                    prefix=prefix
                ))
            )
            
            return [
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified
                }
                for obj in objects
            ]
            
        except S3Error as e:
            logger.error(f"S3 error listing files: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    async def generate_presigned_url(
        self, 
        object_name: str, 
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate presigned URL for file access"""
        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                self.client.presigned_get_object,
                settings.minio_bucket,
                object_name,
                expires
            )
            
            logger.info(f"Generated presigned URL for: {object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"S3 error generating presigned URL {object_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating presigned URL {object_name}: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test MinIO connection"""
        try:
            await self.ensure_bucket_exists()
            
            # Try to list objects to test connection
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: list(self.client.list_objects(
                    settings.minio_bucket, 
                    prefix="test", 
                    max_keys=1
                ))
            )
            
            logger.info("MinIO connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"MinIO connection test failed: {e}")
            return False


# Global MinIO service instance
_minio_service = None


def get_minio_service() -> MinIOService:
    """Get MinIO service instance"""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinIOService()
    return _minio_service


# Convenience functions for backward compatibility
async def upload_file_to_minio(
    obj_bytes: bytes, 
    object_name: str, 
    content_type: str,
    metadata: Optional[Dict[str, str]] = None
) -> None:
    """Upload file to MinIO"""
    service = get_minio_service()
    await service.upload_file(obj_bytes, object_name, content_type, metadata)


async def download_file_from_minio(object_name: str) -> bytes:
    """Download file from MinIO"""
    service = get_minio_service()
    return await service.download_file(object_name)


async def remove_file_from_minio(object_name: str) -> None:
    """Remove file from MinIO"""
    service = get_minio_service()
    await service.remove_file(object_name)


async def test_minio_connection() -> bool:
    """Test MinIO connection"""
    service = get_minio_service()
    return await service.test_connection()
