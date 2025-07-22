from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time
import uvicorn

from app.core.config import get_settings
from app.core.security import JWTHandler
from app.db.session import DatabaseManager
from app.domain.events import EventPublisher
from app.api.routes import accounts
from app.api.deps import create_error_response

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Global instances
db_manager = None
event_publisher = None
jwt_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db_manager, event_publisher, jwt_handler

    logger.info("Starting Account Service...")

    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.init_db()
        logger.info("Database initialized successfully")

        # Initialize event publisher
        event_publisher = EventPublisher()
        await event_publisher.connect()
        logger.info("Event publisher connected successfully")

        # Initialize JWT handler
        jwt_handler = JWTHandler()
        logger.info("JWT handler initialized successfully")

        # Store instances in app state
        app.state.db_manager = db_manager
        app.state.event_publisher = event_publisher
        app.state.jwt_handler = jwt_handler

        logger.info("Account Service started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start Account Service: {str(e)}")
        raise

    finally:
        # Cleanup
        logger.info("Shutting down Account Service...")

        if event_publisher:
            await event_publisher.disconnect()
            logger.info("Event publisher disconnected")

        if db_manager:
            await db_manager.close()
            logger.info("Database connection closed")

        logger.info("Account Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Account Service",
    description="Bank Account Management Microservice",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# Add middleware

# # CORS middleware
# if settings.cors_origins:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=settings.cors_origins,
#         allow_credentials=True,
#         allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
#         allow_headers=["*"],
#     )

# Trusted host middleware
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"],
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


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()

    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"({process_time:.3f}s) for {request.method} {request.url.path}"
    )

    return response


# Exception handlers


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error for {request.url.path}: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            "Validation failed", "VALIDATION_ERROR", details=exc.errors()
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        f"Unhandled exception for {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response("Internal server error", "INTERNAL_ERROR"),
    )


# Include routers
app.include_router(accounts.router, prefix="/api/v1")


# Root endpoints


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "service": "account-service",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        if hasattr(app.state, "db_manager") and app.state.db_manager:
            async with app.state.db_manager.get_session() as session:
                await session.execute("SELECT 1")

        # Check Redis connection
        redis_status = (
            "connected"
            if (
                hasattr(app.state, "event_publisher")
                and app.state.event_publisher
                and app.state.event_publisher.redis
            )
            else "disconnected"
        )

        return {
            "status": "healthy",
            "service": "account-service",
            "version": "1.0.0",
            "environment": settings.environment,
            "database": "connected",
            "redis": redis_status,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "account-service",
                "error": str(e),
                "timestamp": time.time(),
            },
        )


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Basic metrics endpoint."""
    return {
        "service": "account-service",
        "uptime": time.time(),
        "environment": settings.environment,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.environment == "development",
        log_level="info",
        access_log=True,
    )
