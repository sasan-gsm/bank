"""User manager implementation for FastAPI-Users."""

from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin

from app.core.config import settings
from app.domain.models import User
from app.auth.database import get_user_db, UserDatabase
import logging

logger = logging.getLogger(__name__)


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """User manager for FastAPI-Users."""
    
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key
    
    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after user registration."""
        logger.info(f"User {user.id} has registered.")
    
    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        """Called after user login."""
        logger.info(f"User {user.id} logged in.")
    
    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after verification request."""
        logger.info(f"Verification requested for user {user.id}. Token: {token}")
    
    async def on_after_verify(
        self, user: User, request: Optional[Request] = None
    ):
        """Called after user verification."""
        logger.info(f"User {user.id} has been verified")
    
    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after forgot password request."""
        logger.info(f"User {user.id} has forgot their password. Reset token: {token}")
    
    async def on_after_reset_password(self, user: User, request: Optional[Request] = None):
        """Called after password reset."""
        logger.info(f"User {user.id} has reset their password.")


async def get_user_manager(user_db: UserDatabase = Depends(get_user_db)):
    """Get user manager dependency."""
    yield UserManager(user_db)