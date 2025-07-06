from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.cache import cache_manager
from app.db.session import db_manager
from app.api.routes import transactions, accounts, balance

import logging

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Transaction Service...")
    try:
        await db_manager.create_tables()
        await cache_manager.init_cache()
        from scripts.init_db import seed_database

        await seed_database()
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    try:
        if cache_manager.redis_client:
            await cache_manager.redis_client.close()
        await db_manager.engine.dispose()
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title="Banking Transaction Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
    if settings.debug
    else ["*.yourdomain.com"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(transactions.router, prefix="/api/v1/transactions")
app.include_router(accounts.router, prefix="/api/v1/accounts")
app.include_router(balance.router, prefix="/api/v1/balance")


@app.get("/health")
async def health():
    try:
        async with db_manager.get_session() as session:
            await session.execute("SELECT 1")
        if cache_manager.redis_client:
            await cache_manager.redis_client.ping()
        return {
            "status": "healthy",
            "service": "transaction-service",
            "version": "1.0.0",
            "environment": settings.environment,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/")
async def root():
    return {
        "service": "Banking Transaction Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }


@app.exception_handler(Exception)
async def handle_unexpected(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        },
    )
