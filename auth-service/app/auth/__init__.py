"""Authentication module for FastAPI-Users integration."""

from .manager import get_user_manager
from .backend import auth_backend
from .dependencies import current_active_user, current_superuser
from .database import get_user_db

__all__ = [
    "get_user_manager",
    "auth_backend", 
    "current_active_user",
    "current_superuser",
    "get_user_db"
]