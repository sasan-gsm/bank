import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


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
    """Enterprise-grade JWT token handler for document service."""
    
    def __init__(self):
        self.algorithm = getattr(settings, 'jwt_algorithm', 'RS256')
        self.public_key = getattr(settings, 'jwt_public_key', None)
        self.private_key = getattr(settings, 'secret_key', None)
        self.expected_audience = ["document-service"]
        
        # Validate configuration on initialization
        if not self.public_key and not self.private_key:
            logger.error("JWT keys not configured")
            raise ValueError("JWT public key or secret key is required for token validation")
            
        if self.algorithm not in ["RS256", "ES256", "HS256"]:
            logger.warning(f"Using algorithm {self.algorithm}. RS256 or ES256 recommended for production")
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with enhanced security."""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=getattr(settings, 'access_token_expire_minutes', 30))
        
        to_encode.update({
            "exp": expire,
            "iat": now,
            "aud": self.expected_audience
        })
        
        key = self.private_key or self.public_key
        encoded_jwt = jwt.encode(to_encode, key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> TokenData:
        """Decode and validate JWT token with comprehensive security checks."""
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Use public key for verification, fallback to secret key
            key = self.public_key or self.private_key
            
            # Decode token with comprehensive validation
            payload = jwt.decode(
                token,
                key,
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
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        try:
            token_data = self.decode_token(token)
            return {
                "user_id": token_data.user_id,
                "username": token_data.username,
                "email": token_data.email,
                "is_active": token_data.is_active,
                "is_superuser": token_data.is_superuser,
                "permissions": token_data.permissions
            }
        except HTTPException as e:
            raise AuthenticationError(e.detail)


# Initialize JWT handler
jwt_handler = JWTHandler()


async def verify_token_with_auth_service(token: str) -> TokenData:
    """Verify token with external auth service with fallback to local verification."""
    try:
        auth_service_url = getattr(settings, 'auth_service_url', None)
        if auth_service_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{auth_service_url}/verify-token",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    # Convert to TokenData for consistency
                    return TokenData(
                        user_id=user_data.get("user_id"),
                        username=user_data.get("username", ""),
                        email=user_data.get("email", ""),
                        is_active=user_data.get("is_active", True),
                        is_superuser=user_data.get("is_superuser", False),
                        permissions=user_data.get("permissions", [])
                    )
                else:
                    logger.warning(f"Auth service returned status {response.status_code}")
                    raise AuthenticationError("Token verification failed")
                    
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.warning(f"Auth service unavailable: {str(e)}. Falling back to local verification")
    except Exception as e:
        logger.error(f"Unexpected error with auth service: {str(e)}")
    
    # Fallback to local verification if auth service is unavailable
    return jwt_handler.decode_token(token)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user with enhanced validation."""
    try:
        # Try to verify with auth service first, fallback to local verification
        token_data = await verify_token_with_auth_service(credentials.credentials)
        logger.debug(f"Successfully authenticated user: {token_data.username}")
        return token_data
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
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


async def require_admin(current_user: TokenData = Depends(get_current_active_user)) -> TokenData:
    """Require admin privileges with enhanced validation."""
    if not current_user.is_superuser:
        logger.warning(f"Non-admin user attempted admin access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    logger.debug(f"Admin access granted to: {current_user.username}")
    return current_user


def require_permissions(required_permissions: list[str]):
    """Create a dependency that requires specific permissions."""
    
    async def permission_dependency(current_user: TokenData = Depends(get_current_active_user)) -> TokenData:
        return current_user
    
    async def permission_checker(current_user: TokenData = Depends(permission_dependency)):
        if current_user.is_superuser:
            logger.debug(f"Superuser {current_user.username} granted access to {required_permissions}")
            return current_user
            
        user_permissions = set(current_user.permissions)
        required_permissions_set = set(required_permissions)
        
        has_all_permissions = required_permissions_set.issubset(user_permissions)
        
        if not has_all_permissions:
            missing_permissions = required_permissions_set - user_permissions
            logger.warning(
                f"User {current_user.username} missing permissions: {missing_permissions}. "
                f"Required: {required_permissions}, Has: {current_user.permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permissions}",
            )
        
        logger.debug(f"User {current_user.username} granted access to {required_permissions}")
        return current_user

    return permission_checker