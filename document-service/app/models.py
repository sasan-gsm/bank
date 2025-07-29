# app/models/document.py

from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# Pydantic Models
class DocumentBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    tags: Optional[List[str]] = Field(default_factory=list)
    uploaded_by: Optional[str] = Field(None, max_length=100)
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("tags")
    def validate_tags(cls, v):
        if v is None:
            return []
        clean_tags = [tag.strip() for tag in v if tag.strip()]
        if len(clean_tags) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return clean_tags


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

    @field_validator("tags")
    def validate_tags(cls, v):
        if v is None:
            return v
        clean_tags = [tag.strip() for tag in v if tag.strip()]
        if len(clean_tags) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return clean_tags


class DocumentMeta(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int
    tags: List[str]
    uploaded_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    def parse_tags(cls, v):
        if isinstance(v, str):
            return [tag.strip() for tag in v.split(",") if tag.strip()]
        return v or []

    class Config:
        from_attributes = True


class DocumentResponse(DocumentMeta):
    download_url: Optional[str] = None

    @field_validator("download_url", mode="before")
    def set_download_url(cls, v, values):
        if "id" in values:
            return f"/documents/{values['id']}/download"
        return None


class UploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str = "File uploaded successfully"
