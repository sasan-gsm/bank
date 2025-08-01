from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, InvalidSignatureError
from pydantic import BaseModel, Field
from .config import settings
import logging

logger = logging.getLogger(__name__)


security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data structure with validation."""

    user_id: int = Field(..., gt=0, description="User ID must be positive")
    username: str = Field(..., min_length=1, max_length=50, description="Username")
    email: str = Field(..., description="User email address")
    is_active: bool = Field(default=True, description="User active status")
    is_superuser: bool = Field(default=False, description="Superuser status")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    exp: Optional[datetime] = Field(default=None, description="Token expiration time")
    iat: Optional[datetime] = Field(default=None, description="Token issued at time")
    aud: Optional[list[str]] = Field(default=None, description="Token audience")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class JWTHandler:
    """Enterprise-grade JWT token handler for validation and decoding."""

    def __init__(self):
        self.algorithm = settings.jwt_algorithm
        self.public_key = settings.jwt_public_key
        self.expected_audience = ["notification-service"]
        
        # Validate configuration on initialization
        if not self.public_key:
            logger.error("JWT public key not configured")
            raise ValueError("JWT public key is required for token validation")
            
        if self.algorithm not in ["RS256", "ES256", "HS256"]:
            logger.warning(f"Using algorithm {self.algorithm}. RS256 or ES256 recommended for production")

    def decode_token(self, token: str) -> TokenData:
        """Decode and validate JWT token with comprehensive security checks."""
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Decode token with comprehensive validation
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.expected_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "require": ["exp", "iat", "user_id", "username"]
                }
            )

            # Extract and validate timestamps
            exp_timestamp = payload.get("exp")
            iat_timestamp = payload.get("iat")
            
            exp_datetime = None
            iat_datetime = None
            
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                
            if iat_timestamp:
                iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
                
                # Validate token is not from the future
                if iat_datetime > datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token issued in the future",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            # Validate required fields
            user_id = payload.get("user_id")
            username = payload.get("username")
            email = payload.get("email")
            
            if not user_id or not isinstance(user_id, int) or user_id <= 0:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user ID in token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            if not username or not isinstance(username, str):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username in token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return TokenData(
                user_id=user_id,
                username=username,
                email=email or "",
                is_active=payload.get("is_active", True),
                is_superuser=payload.get("is_superuser", False),
                permissions=payload.get("permissions", []),
                exp=exp_datetime,
                iat=iat_datetime,
                aud=payload.get("aud", [])
            )

        except ExpiredSignatureError:
            logger.warning(f"Expired token attempted for user extraction")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except InvalidSignatureError:
            logger.error("Invalid token signature detected")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ValueError as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def validate_permissions(
        self, token_data: TokenData, required_permissions: list[str]
    ) -> bool:
        """Validate if user has required permissions with detailed logging."""
        if not required_permissions:
            return True
            
        if token_data.is_superuser:
            logger.debug(f"Superuser {token_data.username} granted access to {required_permissions}")
            return True

        user_permissions = set(token_data.permissions)
        required_permissions_set = set(required_permissions)
        
        has_all_permissions = required_permissions_set.issubset(user_permissions)
        
        if not has_all_permissions:
            missing_permissions = required_permissions_set - user_permissions
            logger.warning(
                f"User {token_data.username} missing permissions: {missing_permissions}. "
                f"Required: {required_permissions}, Has: {token_data.permissions}"
            )
        else:
            logger.debug(f"User {token_data.username} granted access to {required_permissions}")
            
        return has_all_permissions


jwt_handler = JWTHandler()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current user from JWT token with enhanced validation."""
    try:
        token = credentials.credentials
        token_data = jwt_handler.decode_token(token)
        logger.debug(f"Successfully authenticated user: {token_data.username}")
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current active user with validation."""
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user account"
        )
    return current_user


def require_permissions(permissions: list[str]):
    """Dependency factory for permission-based access control."""
    
    async def permission_dependency(current_user: TokenData = Depends(get_current_active_user)) -> TokenData:
        return current_user
    
    async def permission_checker(current_user: TokenData = Depends(permission_dependency)):
        if not jwt_handler.validate_permissions(current_user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permissions}",
            )
        return current_user

    return permission_checker


async def get_admin_user(current_user: TokenData = Depends(get_current_active_user)) -> TokenData:
    """Get admin user (superuser only) with enhanced validation."""
    if not current_user.is_superuser:
        logger.warning(f"Non-admin user attempted admin access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    logger.debug(f"Admin access granted to: {current_user.username}")
    return current_user