from typing import List, Optional, Dict, Any, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from ..models import Document, DocumentCreate, DocumentUpdate, DocumentResponse
from app.services.storage import (
    upload_file_to_minio,
    download_file_from_minio,
    remove_file_from_minio,
)
from app.core.config import settings
from fastapi import HTTPException, status
import json
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DocumentService:
    """Service class for document operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_file(
        self, content: bytes, content_type: str, filename: str
    ) -> None:
        """Validate file content and metadata"""

        # Check file size
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes",
            )

        # Check content type
        if content_type not in settings.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {content_type}. Allowed types: {', '.join(settings.allowed_mime_types)}",
            )

        # Check filename
        if not filename or len(filename) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename"
            )

    def calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(content).hexdigest()

    async def check_duplicate(self, file_hash: str) -> Optional[Document]:
        """Check if a file with the same hash already exists"""
        result = await self.db.execute(
            select(Document).where(Document.metadata["file_hash"].astext == file_hash)
        )
        return result.scalar_one_or_none()

    async def create_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        tags: List[str],
        uploaded_by: str,
        metadata: Dict[str, Any] = None,
    ) -> Document:
        """Create a new document record"""

        # Validate file
        await self.validate_file(content, content_type, filename)

        # Calculate file hash
        file_hash = self.calculate_file_hash(content)

        # Check for duplicates
        existing_doc = await self.check_duplicate(file_hash)
        if existing_doc:
            logger.warning(f"Duplicate file detected: {filename} (hash: {file_hash})")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File already exists with ID: {existing_doc.id}",
            )

        # Prepare metadata
        doc_metadata = metadata or {}
        doc_metadata["file_hash"] = file_hash
        doc_metadata["original_filename"] = filename

        # Validate tags
        if len(tags) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 tags allowed",
            )

        # Create document
        doc = Document(
            filename=filename,
            content_type=content_type,
            size=len(content),
            tags=",".join(tags),
            uploaded_by=uploaded_by,
            metadata=doc_metadata,
            status="pending",
        )

        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        logger.info(f"Document created: {doc.id} - {filename}")
        return doc

    async def get_document(self, doc_id: int) -> Optional[Document]:
        """Get document by ID"""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        tags: Optional[List[str]] = None,
        content_type: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Document]:
        """List documents with filtering"""

        query = select(Document)
        conditions = []

        # Apply filters
        if tags:
            for tag in tags:
                conditions.append(Document.tags.contains(tag))

        if content_type:
            conditions.append(Document.content_type == content_type)

        if uploaded_by:
            conditions.append(Document.uploaded_by == uploaded_by)

        if status:
            conditions.append(Document.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        # Apply pagination and ordering
        query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_document(
        self,
        doc_id: int,
        update_data: DocumentUpdate,
        user_id: str,
        is_admin: bool = False,
    ) -> Document:
        """Update document metadata"""

        doc = await self.get_document(doc_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Check permissions
        if not is_admin and doc.uploaded_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this document",
            )

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == "tags" and value is not None:
                if len(value) > 10:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Maximum 10 tags allowed",
                    )
                setattr(doc, field, ",".join(value))
            elif field == "metadata" and value is not None:
                # Merge with existing metadata
                existing_metadata = doc.metadata or {}
                existing_metadata.update(value)
                setattr(doc, field, existing_metadata)
            elif value is not None:
                setattr(doc, field, value)

        doc.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(doc)

        logger.info(f"Document updated: {doc_id}")
        return doc

    async def delete_document(
        self, doc_id: int, user_id: str, is_admin: bool = False
    ) -> None:
        """Delete document"""

        doc = await self.get_document(doc_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Check permissions
        if not is_admin and doc.uploaded_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this document",
            )

        try:
            # Remove from MinIO if uploaded
            if doc.status == "uploaded":
                await remove_file_from_minio(str(doc_id))
                logger.info(f"File removed from MinIO: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to remove file from MinIO: {doc_id} - {str(e)}")
            # Continue with database deletion even if MinIO deletion fails

        # Remove from database
        await self.db.delete(doc)
        await self.db.commit()

        logger.info(f"Document deleted: {doc_id}")

    async def get_document_stats(self) -> Dict[str, Any]:
        """Get document statistics"""

        # Total documents
        total_result = await self.db.execute(select(func.count(Document.id)))
        total_documents = total_result.scalar()

        # Documents by status
        status_result = await self.db.execute(
            select(Document.status, func.count(Document.id)).group_by(Document.status)
        )
        status_counts = dict(status_result.all())

        # Total storage used
        size_result = await self.db.execute(select(func.sum(Document.size)))
        total_size = size_result.scalar() or 0

        # Documents by content type
        type_result = await self.db.execute(
            select(Document.content_type, func.count(Document.id)).group_by(
                Document.content_type
            )
        )
        type_counts = dict(type_result.all())

        # Recent uploads (last 24 hours)
        from datetime import timedelta

        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_result = await self.db.execute(
            select(func.count(Document.id)).where(Document.created_at >= yesterday)
        )
        recent_uploads = recent_result.scalar()

        return {
            "total_documents": total_documents,
            "status_distribution": status_counts,
            "total_storage_bytes": total_size,
            "content_type_distribution": type_counts,
            "recent_uploads_24h": recent_uploads,
        }

    async def update_document_status(self, doc_id: int, status: str) -> None:
        """Update document status (used by background tasks)"""

        doc = await self.get_document(doc_id)
        if doc:
            doc.status = status
            doc.updated_at = datetime.utcnow()
            await self.db.commit()
            logger.info(f"Document status updated: {doc_id} -> {status}")

    async def search_documents(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[Document]:
        """Search documents by filename or metadata"""

        search_query = (
            select(Document)
            .where(Document.filename.contains(query))
            .offset(skip)
            .limit(limit)
            .order_by(Document.created_at.desc())
        )

        result = await self.db.execute(search_query)
        return result.scalars().all()
