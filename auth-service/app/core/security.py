import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from passlib.context import CryptContext
from jwt import ExpiredSignatureError, InvalidTokenError

from .config import settings


class SecurityManager:
    """Security manager for password hashing and JWT operations."""

    def __init__(self):
        """Initialize Argon2 hashing context."""
        self.pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password using Argon2."""
        return self.pwd_context.hash(password)

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        subject: Optional[str] = None,
        audience: Optional[str] = "auth-service",
    ) -> str:
        """Create a JWT access token."""
        now = datetime.now(timezone.utc)
        expire = now + (
            expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
        )

        payload = {
            **data,
            "sub": subject or str(data.get("user_id")),
            "aud": audience,
            "iat": now,
            "exp": expire,
            "type": "access",
        }

        return jwt.encode(
            payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm
        )

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        subject: Optional[str] = None,
        audience: Optional[str] = "auth-service",
    ) -> str:
        """Create a JWT refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + (
            expires_delta or timedelta(days=settings.refresh_token_expire_days)
        )

        payload = {
            **data,
            "sub": subject or str(data.get("user_id")),
            "aud": audience,
            "iat": now,
            "exp": expire,
            "type": "refresh",
        }

        return jwt.encode(
            payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm
        )

    def verify_token(
        self,
        token: str,
        expected_type: Optional[str] = None,
        audience: Optional[str] = "auth-service",
    ) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_public_key,
                algorithms=[settings.jwt_algorithm],
                audience=audience,
            )

            if expected_type and payload.get("type") != expected_type:
                raise ValueError(f"Invalid token type: expected {expected_type}")

            return payload

        except ExpiredSignatureError:
            raise ValueError("Token has expired")

        except InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")


# Singleton instance
security = SecurityManager()
