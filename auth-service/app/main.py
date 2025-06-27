"""
Main FastAPI application with middleware, routers, and startup/shutdown events.
Configures CORS, caching, and database initialization.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.cache import cache_manager
from app.db.session import db_manager
from app.api.routes import auth, users, password
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting Auth Service...")

    try:
        # Initialize database
        await db_manager.create_tables()
        logger.info("Database tables created/verified")

        # Initialize cache
        await cache_manager.init_cache()
        logger.info("Cache initialized")

        # Run database seeding if needed
        from scripts.init_db import seed_database

        await seed_database()
        logger.info("Database seeded with default data")

        logger.info("Auth Service startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to start Auth Service: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Auth Service...")

    try:
        # Close cache connections
        if cache_manager.redis_client:
            await cache_manager.redis_client.close()

        # Close database connections
        await db_manager.engine.dispose()

        logger.info("Auth Service shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="Banking Auth Service",
    description="Authentication and authorization microservice for banking transaction system",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
    if settings.debug
    else ["*.yourdomain.com"],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

app.include_router(users.router, prefix="/api/v1/users", tags=["User Management"])

app.include_router(
    password.router, prefix="/api/v1/password", tags=["Password Management"]
)


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Health check endpoint for service monitoring.

    Returns:
        Health status and service information
    """
    try:
        # Check database connectivity
        async with db_manager.async_session_factory() as session:
            await session.execute("SELECT 1")

        # Check cache connectivity
        if cache_manager.redis_client:
            await cache_manager.redis_client.ping()

        return {
            "status": "healthy",
            "service": "auth-service",
            "version": "1.0.0",
            "environment": settings.environment,
            "timestamp": "2025-06-26T01:54:00+03:30",
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "service": "auth-service", "error": str(e)},
        )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Banking Auth Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.

    Args:
        request: HTTP request object
        exc: Exception instance

    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )
