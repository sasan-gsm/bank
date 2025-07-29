from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.session import get_db
from app.models import Document, DocumentResponse, UploadResponse, DocumentUpdate
from app.services.storage import download_file_from_minio, remove_file_from_minio
from app.services.tasks import process_upload
from app.core.config import settings
from app.core.auth import get_current_active_user, require_admin
from typing import Optional, List, Dict, Any
import json
import io
from datetime import datetime

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    tags: Optional[str] = Query("", description="Comma-separated tags"),
    uploaded_by: Optional[str] = Query(None, description="Uploader identifier"),
    metadata: Optional[str] = Query("{}", description="JSON metadata"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Upload a new document"""

    # Read file content
    content = await file.read()

    # Validate file type
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(settings.allowed_mime_types)}",
        )

    # Validate file size
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_file_size} bytes",
        )

    # Parse metadata
    try:
        metadata_dict = json.loads(metadata) if metadata else {}
        if not isinstance(metadata_dict, dict):
            raise ValueError("Metadata must be a valid JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in metadata: {str(e)}",
        )

    # Process tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    if len(tag_list) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 10 tags allowed"
        )

    # Create document record
    doc = Document(
        filename=file.filename,
        content_type=file.content_type,
        size=len(content),
        tags=",".join(tag_list),
        uploaded_by=uploaded_by or current_user.get("username"),
        metadata=metadata_dict,
        status="pending",
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Queue background upload to MinIO
    process_upload.delay(
        doc.id,
        doc.filename,
        doc.content_type,
        ",".join(tag_list),
        uploaded_by or current_user.get("username"),
        content,
        metadata_dict,
    )

    return UploadResponse(id=doc.id, filename=doc.filename, status=doc.status)


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of documents to return"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    uploaded_by: Optional[str] = Query(None, description="Filter by uploader"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List documents with optional filtering"""

    query = select(Document)

    # Apply filters
    conditions = []

    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tag_list:
            conditions.append(Document.tags.contains(tag))

    if content_type:
        conditions.append(Document.content_type == content_type)

    if uploaded_by:
        conditions.append(Document.uploaded_by == uploaded_by)

    if conditions:
        query = query.where(and_(*conditions))

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document_metadata(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get document metadata by ID"""

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Download document file"""

    # Get document metadata
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if doc.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document not ready for download. Status: {doc.status}",
        )

    try:
        # Download from MinIO
        file_data = await download_file_from_minio(str(doc_id))

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=doc.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={doc.filename}",
                "Content-Length": str(len(file_data)),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}",
        )


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int,
    update_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Update document metadata"""

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check if user can update (owner or admin)
    if doc.uploaded_by != current_user.get("username") and not current_user.get(
        "is_admin", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this document",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        if field == "tags" and value is not None:
            setattr(doc, field, ",".join(value))
        elif field == "metadata" and value is not None:
            setattr(doc, field, value)
        elif value is not None:
            setattr(doc, field, value)

    doc.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(doc)

    return DocumentResponse.model_validate(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Delete document"""

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check if user can delete (owner or admin)
    if doc.uploaded_by != current_user.get("username") and not current_user.get(
        "is_admin", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document",
        )

    try:
        # Remove from MinIO if uploaded
        if doc.status == "uploaded":
            await remove_file_from_minio(str(doc_id))
    except Exception:
        # Log error but continue with database deletion
        pass

    # Remove from database
    await db.delete(doc)
    await db.commit()


@router.get("/stats/summary")
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_admin),
):
    """Get document statistics (admin only)"""

    from sqlalchemy import func

    # Total documents
    total_result = await db.execute(select(func.count(Document.id)))
    total_documents = total_result.scalar()

    # Documents by status
    status_result = await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )
    status_counts = dict(status_result.all())

    # Total storage used
    size_result = await db.execute(select(func.sum(Document.size)))
    total_size = size_result.scalar() or 0

    # Documents by content type
    type_result = await db.execute(
        select(Document.content_type, func.count(Document.id)).group_by(
            Document.content_type
        )
    )
    type_counts = dict(type_result.all())

    return {
        "total_documents": total_documents,
        "status_distribution": status_counts,
        "total_storage_bytes": total_size,
        "content_type_distribution": type_counts,
    }
