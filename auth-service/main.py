"""
FastAPI Authentication Microservice Main Entry Point

Enterprise-grade authentication service with comprehensive middleware stack,
database initialization, and proper error handling.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Corrected import path
from app.api.auth import router as auth_router
from app.core.cache import cache_manager
from app.core.config import settings
from app.db.session import db_manager
from scripts.init_db import main as init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("auth-service.log"),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting Auth Service...")

    try:
        # Initialize Redis cache
        await cache_manager.init_cache()
        logger.info("Redis cache initialized")

        # Check if database exists, create if not
        db_path = Path("auth.db")
        if not db_path.exists():
            logger.info("Database not found, creating and initializing...")
            await init_database()
        else:
            logger.info("Database found, ensuring tables exist...")
            await db_manager.create_tables()

        logger.info("Auth Service started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start Auth Service: {e}")
        raise
    finally:
        logger.info("Shutting down Auth Service...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application with enterprise middleware."""

    app = FastAPI(
        title="Banking Auth Service",
        description="Enterprise-grade authentication and authorization microservice",
        version=settings.service_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Security Middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"],
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # Compression Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Session Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=settings.access_token_expire_minutes * 60,
    )

    # Request ID and Logging Middleware
    @app.middleware("http")
    async def add_request_id_and_logging(request: Request, call_next):
        import uuid
        import time

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str(process_time)

        # Log response
        logger.info(
            f"Response {request_id}: {response.status_code} in {process_time:.4f}s"
        )

        return response

    # Exception Handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_exception",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "internal_server_error",
                    "message": "An internal server error occurred",
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    # Health Check Endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Service health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.service_name,
            "version": settings.service_version,
            "environment": settings.environment,
        }

    # Include routers with corrected path
    app.include_router(auth_router, prefix="/auth", tags=["authentication"])

    return app


# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=True,
    )
