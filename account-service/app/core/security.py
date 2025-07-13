from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from typing import Optional, List
from datetime import datetime
from .config import settings

security = HTTPBearer()

logger = logging.getLogger(__name__)


class Token(BaseModel):
    user_id: str
    usename: str
    email: Optional[str]
    is_active: bool
    is_superuser: bool
    permissions: list[str]
    exp: Optional[datetime]
    iat: Optional[datetime]
    aud: Optional[list[str]]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class JWTHandler:
    def __init__(self):
        self.algorithm = settings.jwt_algorithm
        self.public_key = settings.jwt_public_key
        self.expected_audience = ["account-service"]

        if not self.public_key:
            logger.error("JWT public key not configured")
            raise ValueError("JWT public key is required for token validation")

        if self.algorithm != "RS256":
            logger.warning(
                f"Algorithm {self.algorithm}. not recommended for production"
            )

    def decode(self, token: str) -> Token:
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = jwt.decode(
                token,
                key=self.public_key,
                algorithms=self.algorithm,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "require": ["exp", "iat", "user_id", "username"],
                },
            )
            return Token(
                user_id=payload.get("user_id"),
                usename=payload.get("username"),
                email=payload.get("email"),
                is_active=payload.get("is_active", True),
                is_superuser=payload.get("is_superuser", False),
                permissions=payload.get("permissions", []),
                exp=payload.get("exp"),
                iat=payload.get("ait"),
                aud=payload.get("aud", []),
            )

        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            raise e

    def validate_permissions(
        self, token_data: Token, required_permissions: List[str]
    ) -> bool:
        if not required_permissions:
            return True
        if token_data.is_superuser:
            return True

        user_permissions = set(token_data.permissions)
        required_permissions_set = set(required_permissions)
        return required_permissions_set.issubset(user_permissions)


# Initialize JWT handler with error handling
try:
    jwt_handler = JWTHandler()
except ValueError as e:
    logger.error(f"Failed to initialize JWT handler: {e}")
    raise


async def get_current_user(
    cridentials: HTTPAuthorizationCredentials = Depends(security),
) -> Token:
    if not cridentials or cridentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return jwt_handler.decode(cridentials.credentials)


async def get_current_active_user(
    current_user: Token = Depends(get_current_user),
) -> Token:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
