"""Authentication backend configuration for FastAPI-Users."""

from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,  # Use JWTStrategy instead of JWTAuthentication
)

from app.core.config import settings

# Bearer transport for token handling
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy with RSA keys."""
    return JWTStrategy(
        secret=settings.jwt_private_key,
        lifetime_seconds=settings.access_token_expire_minutes * 60,
        algorithm=settings.jwt_algorithm,
        public_key=settings.jwt_public_key,  # Add public key for RSA
    )


# Authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,  # Use function reference, not lambda
)
